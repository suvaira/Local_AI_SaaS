import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw
import PyPDF2

# --- UI DESIGN ---
def apply_custom_design():
    st.markdown("""
    <style>
    [data-testid="stMarkdownContainer"] p { color: inherit; }
    .main-header {
        background: linear-gradient(90deg, #1E3A8A, #3B82F6);
        color: white; padding: 2rem; border-radius: 20px;
        text-align: center; margin-bottom: 2rem;
    }
    .link-box {
        background: #f0fdf4; border: 1px solid #16a34a;
        padding: 15px; border-radius: 10px;
        color: #166534; font-weight: bold; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HELPERS ---
def read_file(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text[:5000] # Limit text to avoid DB errors
        else:
            return str(uploaded_file.read(), "utf-8")[:5000]
    except:
        return ""

def generate_hq_qr(url, shop_name):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=15, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E3A8A", back_color="white").convert('RGB')
    canvas = Image.new('RGB', (600, 700), 'white')
    canvas.paste(img.resize((500, 500)), (50, 50))
    draw = ImageDraw.Draw(canvas)
    draw.text((300, 600), shop_name, fill="#1E3A8A", anchor="mm")
    buf = BytesIO()
    canvas.save(buf, format="PNG", quality=100)
    return buf.getvalue()

# --- SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

apply_custom_design()
shop_slug = st.query_params.get("shop")

if shop_slug:
    # --- CUSTOMER CHAT ---
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
    if data.data:
        shop = data.data[0]
        st.markdown(f"<div class='main-header'><h1>🏪 {shop['shop_name']}</h1></div>", unsafe_allow_html=True)
        if "messages" not in st.session_state: st.session_state.messages = []
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            try:
                sys = f"Assistant for {shop['shop_name']}. Rules: {shop['rules']}. Info: {shop.get('sheet_url', '')}"
                msgs = [{"role": "system", "content": sys}] + st.session_state.messages
                res = ""
                with st.spinner("..."):
                    for msg in client.chat_completion(model="Qwen/Qwen2.5-7B-Instruct", messages=msgs, max_tokens=500, stream=True):
                        res += msg.choices[0].delta.content or ""
                with st.chat_message("assistant"): st.markdown(res)
                st.session_state.messages.append({"role": "assistant", "content": res})
            except: st.error("Slow connection. Try again.")
else:
    # --- ADMIN DASHBOARD ---
    st.markdown("<div class='main-header'><h1>SaaS AI Builder 🚀</h1></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🏗️ Build AI", "📊 Sheet Integration"])

    with t1:
        with st.form("builder"):
            name = st.text_input("Shop Name")
            slug = st.text_input("Unique ID (suhani-ele)")
            contact = st.text_input("Contact Info")
            manual_rules = st.text_area("Shop Rules & Inventory")
            file = st.file_uploader("Inventory file upload (PDF/TXT)", type=['pdf', 'txt'])
            
            if st.form_submit_button("Launch AI 🚀"):
                total_rules = manual_rules
                if file:
                    file_text = read_file(file)
                    total_rules += "\n" + file_text
                
                # Check if columns exist in DB
                supabase.table("shops").insert({
                    "shop_name": name, "shop_slug": slug.lower(), 
                    "rules": total_rules, "contact_info": contact
                }).execute()
                st.session_state.last_slug = slug.lower()
                st.session_state.last_name = name
                st.success("AI Created!")

        if "last_slug" in st.session_state:
            app_url = f"https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?shop={st.session_state.last_slug}"
            st.markdown(f"<div class='link-box'>Live Link: {app_url}</div>", unsafe_allow_html=True)
            
            # --- OFFICIAL COPY BUTTON ---
            st.copy_to_clipboard(app_url)
            st.info("Link automatically copied to clipboard! 📋")
            
            if st.button("🖼️ Create & Download HQ QR Card"):
                qr_data = generate_hq_qr(app_url, st.session_state.last_name)
                st.image(qr_data, width=300)
                st.download_button("📥 Download Print-Ready QR", qr_data, f"{st.session_state.last_slug}_qr.png", "image/png")

    with t2:
        st.subheader("Google Sheet Sync")
        st.write("Step 1: Sheet mein Extensions > Apps Script mein niche wala code paste karein aur 'Deploy as Web App' karke URL layein.")
        st.code("""
function doGet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheets()[0];
  var data = sheet.getDataRange().getValues();
  var result = [];
  for (var i = 1; i < data.length; i++) {
    result.push({"question": data[i][0], "answer": data[i][1]});
  }
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}
        """)
        target_slug = st.text_input("Shop ID daalein")
        sheet_url = st.text_input("Google Script Web App URL paste karein")
        if st.button("Activate Google Sheet Sync ⚡"):
            supabase.table("shops").update({"sheet_url": sheet_url}).eq("shop_slug", target_slug.lower()).execute()
            st.success("Google Sheet Connected!")

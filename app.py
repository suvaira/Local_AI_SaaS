import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import PyPDF2

# --- 1. UI DESIGN (Dark Mode Fix & Premium Look) ---
def apply_custom_design():
    st.markdown("""
    <style>
    /* Dark Mode Visibility Fix */
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] h1, 
    [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
        color: inherit !important;
    }
    
    .stApp { background-color: transparent; }

    /* Glassmorphism Header */
    .main-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white !important;
        padding: 2.5rem;
        border-radius: 25px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(30, 58, 138, 0.3);
    }
    .main-header h1 { color: white !important; }

    /* Chat Bubbles */
    .stChatMessage {
        border-radius: 20px !important;
        padding: 1.2rem !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Success Link Box */
    .link-box {
        background: #f0fdf4;
        border: 2px solid #16a34a;
        padding: 20px;
        border-radius: 15px;
        color: #166534;
        font-size: 1.1rem;
        font-weight: bold;
        text-align: center;
        margin: 15px 0;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        font-weight: bold;
        transition: 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HELPERS (File Reader & HQ QR) ---
def read_file(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text[:7000]
        else:
            return str(uploaded_file.read(), "utf-8")[:7000]
    except: return ""

def generate_hq_qr(url, shop_name):
    # High Quality QR
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white").convert('RGB')
    
    # Create Branded Card (HQ)
    canvas = Image.new('RGB', (800, 1000), '#1E3A8A')
    draw = ImageDraw.Draw(canvas)
    
    # White background for QR
    draw.rectangle([40, 150, 760, 960], fill="white")
    
    # Text branding
    draw.text((400, 60), "SMART AI ASSISTANT", fill="#3B82F6", anchor="mm")
    draw.text((400, 100), shop_name.upper(), fill="white", anchor="mm")
    
    # Paste QR
    qr_res = qr_img.resize((650, 650))
    canvas.paste(qr_res, (75, 200))
    
    draw.text((400, 900), "Scan to Chat with our AI", fill="#1E3A8A", anchor="mm")
    
    buf = BytesIO()
    canvas.save(buf, format="PNG", quality=100)
    return buf.getvalue()

# --- 3. CORE SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

apply_custom_design()
shop_slug = st.query_params.get("shop")

# --- 4. CUSTOMER CHAT INTERFACE ---
if shop_slug:
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
    if data.data:
        shop = data.data[0]
        st.markdown(f"<div class='main-header'><h1>🏪 {shop['shop_name']}</h1><p>Online 24/7 AI Support</p></div>", unsafe_allow_html=True)
        
        if "messages" not in st.session_state: st.session_state.messages = []
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Dukan ke baare mein puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)

            try:
                sys_msg = f"You are an assistant for {shop['shop_name']}. Rules: {shop['rules']}. Contact: {shop['contact_info']}. Reply in Hindi/English mixed."
                msgs = [{"role": "system", "content": sys_msg}] + st.session_state.messages
                
                response = ""
                with st.spinner("AI soch raha hai..."):
                    for msg in client.chat_completion(model="Qwen/Qwen2.5-7B-Instruct", messages=msgs, max_tokens=600, stream=True):
                        response += msg.choices[0].delta.content or ""
                
                with st.chat_message("assistant", avatar="🤖"): st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except: st.error("Slow connection. Try again.")
    else: st.error("Shop Not Found!")

# --- 5. ADMIN DASHBOARD ---
else:
    st.markdown("<div class='main-header'><h1>Shop AI SaaS Builder 🚀</h1><p>Modern Business Solutions</p></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🏗️ Build New AI", "📊 Google Sheet Sync"])

    with t1:
        with st.form("builder", clear_on_submit=False):
            st.subheader("Dukan ki Detail Bharein")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Shop Name", placeholder="E.g. Suhani Electronics")
                slug = st.text_input("Shop ID", placeholder="suhani-ele")
            with col2:
                contact = st.text_input("Contact Info", placeholder="Phone/Email")
            
            rules = st.text_area("Shop Rules & Inventory (Manual Type)")
            file = st.file_uploader("Ya phir Inventory File upload karein (PDF/TXT)", type=['pdf', 'txt'])
            
            launch = st.form_submit_button("Launch AI 🚀")
            
            if launch:
                if name and slug:
                    final_rules = rules
                    if file: final_rules += "\n" + read_file(file)
                    
                    supabase.table("shops").insert({
                        "shop_name": name, "shop_slug": slug.lower(), 
                        "rules": final_rules, "contact_info": contact
                    }).execute()
                    
                    st.session_state.last_slug = slug.lower()
                    st.session_state.last_name = name
                    st.success("Congratulations! AI is now live.")

        if "last_slug" in st.session_state:
            app_url = f"https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?shop={st.session_state.last_slug}"
            
            st.markdown(f"<div class='link-box'>Live Link: {app_url}</div>", unsafe_allow_html=True)
            
            # Copy to Clipboard
            st.copy_to_clipboard(app_url)
            st.toast("URL Copied to Clipboard! 📋")
            
            if st.button("🖼️ Generate Branded HQ QR Card"):
                with st.spinner("Creating High Quality QR..."):
                    qr_data = generate_hq_qr(app_url, st.session_state.last_name)
                    st.image(qr_data, width=350, caption="High-Quality Print Ready Card")
                    st.download_button("📥 Download HQ QR Card (PNG)", qr_data, f"{st.session_state.last_slug}_qr.png", "image/png")

    with t2:
        st.subheader("Google Sheet Integration")
        st.info("Step 1: Niche wala code copy karein aur apni Google Sheet ke 'Extensions > Apps Script' mein daalein.")
        
        full_script = """function doGet() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheets()[0];
    var data = sheet.getDataRange().getValues();
    var result = [];
    for (var i = 1; i < data.length; i++) {
      if (data[i][0] && data[i][1]) {
        result.push({ "question": data[i][0].toString(), "answer": data[i][1].toString() });
      }
    }
    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({"error": e.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}"""
        st.code(full_script, language="javascript")
        st.button("📋 Copy Script Code", on_click=lambda: st.write("Code Copied!"))
        st.copy_to_clipboard(full_script)
        
        st.write("---")
        st.write("Step 2: Script Deploy (Web App) karke URL yahan daalein:")
        target_id = st.text_input("Enter Shop ID to sync")
        s_url = st.text_input("Google Script Web App URL")
        
        if st.button("Activate & Sync Now ⚡"):
            if target_id and s_url:
                supabase.table("shops").update({"sheet_url": s_url}).eq("shop_slug", target_id.lower()).execute()
                st.success("Google Sheet Successfully Connected!")
            else: st.warning("ID aur URL dono zaroori hain.")

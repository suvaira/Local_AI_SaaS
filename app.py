import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# --- PREMIUM UI DESIGN (Advanced CSS) ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Glassmorphism Header */
    .main-header {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 30px;
    }

    /* Professional Chat Bubbles */
    .stChatMessage {
        background: white !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
    }

    /* GPay Style QR Card Preview */
    .qr-card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        border: 2px solid #1E3A8A;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }

    /* Custom Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #1E3A8A, #3B82F6);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTION: Generate Branded QR Card ---
def generate_qr_card(url, shop_name):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
    
    # Create a canvas for the card
    card = Image.new('RGB', (400, 550), color='#1E3A8A')
    draw = ImageDraw.Draw(card)
    
    # White rounded rectangle for QR
    draw.rectangle([20, 100, 380, 530], fill="white")
    
    # Add Shop Name Text
    # (Note: Standard PIL uses default font, for better fonts you'd load a .ttf)
    draw.text((200, 50), shop_name, fill="white", anchor="mm")
    draw.text((200, 80), "Scan to Chat with AI", fill="#c3cfe2", anchor="mm")
    
    # Paste QR onto card
    qr_img = qr_img.resize((300, 300))
    card.paste(qr_img, (50, 150))
    
    # Save to Buffer
    buf = BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()

# 1. Setup
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

local_css()

shop_slug = st.query_params.get("shop")

# --- PART A: CUSTOMER CHAT ---
if shop_slug:
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
    if data.data:
        shop = data.data[0]
        st.markdown(f"<div class='main-header'><h1>🏪 {shop['shop_name']}</h1><p>Online AI Assistant</p></div>", unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)

            try:
                sys_prompt = f"Assistant for {shop['shop_name']}. Rules: {shop['rules']}. Contact: {shop['contact_info']}. Reply in Hindi/English."
                messages = [{"role": "system", "content": sys_prompt}] + st.session_state.messages
                
                response = ""
                with st.spinner("AI is typing..."):
                    for msg in client.chat_completion(model="Qwen/Qwen2.5-7B-Instruct", messages=messages, max_tokens=500, stream=True):
                        response += msg.choices[0].delta.content or ""
                
                with st.chat_message("assistant", avatar="🤖"): st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except:
                st.error("AI is busy. Try later.")
    else:
        st.error("Shop not found.")

# --- PART B: ADMIN DASHBOARD ---
else:
    st.markdown("<div class='main-header'><h1>Shop AI SaaS Builder 🚀</h1><p>Modern Solutions for Local Businesses</p></div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🆕 Create New AI", "📱 My Branded QR"])
    
    with tab1:
        with st.form("setup"):
            name = st.text_input("Shop Name")
            slug = st.text_input("Unique ID (e.g. suhani-ele)")
            rules = st.text_area("Shop Rules & Inventory Details")
            contact = st.text_input("Contact Info")
            if st.form_submit_button("Launch AI"):
                supabase.table("shops").insert({"shop_name": name, "shop_slug": slug.lower(), "rules": rules, "contact_info": contact}).execute()
                st.success("AI is Live!")
    
    with tab2:
        search_slug = st.text_input("Enter your Shop ID to get QR")
        if search_slug:
            data = supabase.table("shops").select("*").eq("shop_slug", search_slug.lower()).execute()
            if data.data:
                shop = data.data[0]
                final_url = f"https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?shop={shop['shop_slug']}"
                
                # Show QR Card
                qr_img_data = generate_qr_card(final_url, shop['shop_name'])
                st.image(qr_img_data, width=300, caption="Your Branded AI QR Card")
                
                st.download_button(
                    label="📥 Download Branded QR Card",
                    data=qr_img_data,
                    file_name=f"{shop['shop_slug']}_qr.png",
                    mime="image/png"
                )
            else:
                st.warning("Shop ID not found.")

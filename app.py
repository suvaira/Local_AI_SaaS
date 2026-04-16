```python
import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Suvaira AI", page_icon="🤖", layout="centered")

# ---------------- CSS ----------------
def local_css():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to right, #eef2f3, #dfe9f3);
    }

    .main-header {
        text-align: center;
        padding: 25px;
        border-radius: 20px;
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        color: white;
        box-shadow: 0px 6px 15px rgba(0,0,0,0.15);
    }

    [data-testid="stChatMessageContent-user"] {
        background-color: #1E3A8A;
        color: white;
        border-radius: 15px;
        padding: 10px;
    }

    [data-testid="stChatMessageContent-assistant"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 10px;
    }

    .stChatInputContainer {
        background: white;
        border-radius: 20px;
        padding: 10px;
        box-shadow: 0px 3px 10px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ---------------- DB & AI ----------------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

# ---------------- QR CODE ----------------
def generate_qr(shop_name, url):
    qr = qrcode.make(url).resize((300,300))

    bg = Image.new("RGB", (420, 520), "#ffffff")
    draw = ImageDraw.Draw(bg)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    draw.text((40, 30), shop_name, fill="#1E3A8A", font=font)
    bg.paste(qr, (60,120))
    draw.text((60, 450), "Scan & Chat with AI 🤖", fill="gray")

    return bg

# ---------------- LANGUAGE DETECT ----------------
def detect_language(text):
    if any(c in text for c in "અઆઇઈઉઊએઐઓઔ"):
        return "Gujarati"
    elif any(c in text for c in "कखगघचछजझटठ"):
        return "Hindi"
    else:
        return "English"

# ---------------- ANALYTICS ----------------
def save_analytics(shop_slug, question):
    supabase.table("analytics").insert({
        "shop_slug": shop_slug,
        "question": question,
        "time": str(datetime.now())
    }).execute()

# ---------------- ROUTING ----------------
shop_slug = st.query_params.get("shop")

# ======================================================
# ================= CUSTOMER CHAT =======================
# ======================================================
if shop_slug:

    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()

    if data.data:
        shop = data.data[0]

        st.markdown(f"""
        <div class="main-header">
            <h1>🏪 {shop['shop_name']}</h1>
            <p>AI Assistant 🤖</p>
        </div>
        """, unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if prompt := st.chat_input("Kuch bhi puchiye..."):

            save_analytics(shop_slug, prompt)

            st.session_state.messages.append({"role":"user","content":prompt})

            lang = detect_language(prompt)

            # FAQ matching
            faq_answer = ""
            if shop.get("faq"):
                for line in shop["faq"].split("\n"):
                    if ":" in line:
                        q,a = line.split(":")
                        if q.lower() in prompt.lower():
                            faq_answer = a

            if faq_answer:
                response = faq_answer
            else:
                system = f"""
                You are assistant of {shop['shop_name']}.
                Rules: {shop['rules']}
                Answer in {lang}.
                """

                msgs = [{"role":"system","content":system}]
                for m in st.session_state.messages:
                    msgs.append(m)

                response = ""
                with st.spinner("AI soch raha hai..."):
                    for chunk in client.chat_completion(
                        model="Qwen/Qwen2.5-7B-Instruct",
                        messages=msgs,
                        max_tokens=400,
                        stream=True,
                    ):
                        response += chunk.choices[0].delta.content or ""

            with st.chat_message("assistant"):
                st.markdown(response)

                # ORDER BUTTON
                if shop.get("contact_info"):
                    st.link_button("📲 WhatsApp Order", f"https://wa.me/{shop['contact_info']}")

            st.session_state.messages.append({"role":"assistant","content":response})

    else:
        st.error("Shop nahi mila")

# ======================================================
# ================= ADMIN PANEL =========================
# ======================================================
else:

    st.markdown("""
    <div class="main-header">
        <h1>Suvaira AI Builder 🚀</h1>
        <p>Local dukaan ko digital banao</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Guide")
        st.write("1. Shop add karo")
        st.write("2. QR download karo")
        st.write("3. Print & use")

    # ---------------- CREATE SHOP ----------------
    st.subheader("New Shop Create")

    with st.form("form", clear_on_submit=True):

        name = st.text_input("Shop Name")
        slug = st.text_input("Unique ID")
        contact = st.text_input("WhatsApp Number")

        rules = st.text_area("Rules / Products / Timing")

        faq = st.text_area("FAQ (format: question:answer)")

        submit = st.form_submit_button("Create AI")

        if submit:
            supabase.table("shops").insert({
                "shop_name": name,
                "shop_slug": slug.lower(),
                "rules": rules,
                "contact_info": contact,
                "faq": faq
            }).execute()

            st.success("AI Ready 🚀")

            url = f"https://yourapp.streamlit.app/?shop={slug.lower()}"

            qr = generate_qr(name, url)

            st.image(qr)

            buf = io.BytesIO()
            qr.save(buf, format="PNG")

            st.download_button("Download QR", buf.getvalue(), f"{slug}.png")

    # ---------------- ANALYTICS ----------------
    st.subheader("Analytics")

    data = supabase.table("analytics").select("*").execute()

    if data.data:
        for d in data.data[-10:]:
            st.write(f"{d['shop_slug']} → {d['question']}")
```

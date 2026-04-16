import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient

# --- UI DESIGN (CSS) ---
def local_css():
    st.markdown("""
    <style>
    /* Background color */
    .stApp { background-color: #f5f7f9; }
    
    /* Chat bubble style */
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Header style */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #1E3A8A;
        text-align: center;
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }

    /* Input box style */
    .stChatInputContainer {
        padding-bottom: 20px;
    }

    /* Button style */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        height: 50px;
    }
    </style>
    """, unsafe_allow_html=True)

# 1. Database & AI Setup
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

local_css() # Design apply karna

# URL parameter check
shop_slug = st.query_params.get("shop")

# --- PART A: CUSTOMER CHAT (Beautiful Look) ---
if shop_slug:
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
    
    if data.data:
        shop = data.data[0]
        
        # Shop Header with Icon
        st.markdown(f"""
            <div class="main-header">
                <h1>🏪 {shop['shop_name']}</h1>
                <p>Aapki sewa mein hamara AI Assistant</p>
            </div>
        """, unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Chat display
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Dukan ke baare mein puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            try:
                system_instruction = f"You are a helpful assistant for {shop['shop_name']}. Rules: {shop['rules']}. Contact: {shop['contact_info']}. Answer in Hindi/English politely."
                
                messages = [{"role": "system", "content": system_instruction}]
                for m in st.session_state.messages:
                    messages.append({"role": m["role"], "content": m["content"]})

                response = ""
                # Progress bar for better experience
                with st.spinner("AI soch raha hai..."):
                    for message in client.chat_completion(
                        model="Qwen/Qwen2.5-7B-Instruct",
                        messages=messages,
                        max_tokens=500,
                        stream=True,
                    ):
                        response += message.choices[0].delta.content or ""

                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            except Exception as e:
                st.warning("⚠️ Thodi der baad try karein, AI break le raha hai.")
    else:
        st.error("Dukan nahi mili!")

# --- PART B: ADMIN DASHBOARD (Professional) ---
else:
    st.markdown("<div class='main-header'><h1>SaaS Shop AI Builder 🚀</h1><p>Local dukan ko digital banayein</p></div>", unsafe_allow_html=True)
    
    # Sidebar mein instructions
    with st.sidebar:
        st.header("Kaise Use Karein?")
        st.write("1. Dukan ki details bharein.")
        st.write("2. Rules mein timing aur products likhein.")
        st.write("3. Link ko QR Code banakar dukan par lagayein.")

    with st.container():
        st.subheader("Naya Shop AI banayein")
        with st.form("setup", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Dukan ka Naam", placeholder="Example: Sharma Sweets")
                slug = st.text_input("Unique ID", placeholder="sharma-sweets")
            with col2:
                contact = st.text_input("Phone/Contact", placeholder="9876543210")
            
            rules = st.text_area("Dukan ke Rules, Products aur Timing", placeholder="Hum 9 baje khulte hain. Free delivery 2km tak hai...")
            
            if st.form_submit_button("Generate Professional AI"):
                if name and slug:
                    supabase.table("shops").insert({"shop_name": name, "shop_slug": slug.lower(), "rules": rules, "contact_info": contact}).execute()
                    st.balloons() # Success celebration
                    st.success(f"Dukan '{name}' ka AI ban gaya hai!")
                    st.info(f"Customer Link: https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?shop={slug.lower()}")
                else:
                    st.error("Naam aur ID zaroori hai!")

import streamlit as st
from supabase import create_client
import google.generativeai as genai

# 1. Database aur AI Setup (Hame Secrets se connect karna hoga)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# URL check karne ke liye logic
query_params = st.query_params
shop_slug = query_params.get("shop")

# --- PART A: CUSTOMER CHAT INTERFACE ---
if shop_slug:
    # Database se shop ki detail nikalna
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug).execute()
    
    if data.data:
        shop = data.data[0]
        st.title(f"Welcome to {shop['shop_name']}")
        st.subheader("AI Assistant")

        # AI ko instruction dena (System Prompt)
        instruction = f"You are an AI assistant for {shop['shop_name']}. Rules: {shop['rules']}. Contact: {shop['contact_info']}. Answer briefly and politely in Hindi/English."
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            chat = model.start_chat(history=[])
            response = chat.send_message(prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
    else:
        st.error("Shop not found!")

# --- PART B: SHOPKEEPER SETUP DASHBOARD ---
else:
    st.title("Local Shop AI Maker 🏪")
    st.write("Apni dukan ke liye AI Assistant banayein 2 minute mein.")

    with st.form("setup_form"):
        s_name = st.text_input("Dukan ka Naam (Shop Name)")
        s_slug = st.text_input("Unique ID (Bina space ke, jaise: sharma-store)")
        s_rules = st.text_area("Dukan ke Rules aur Details (Timing, Returns, Offers)")
        s_contact = st.text_input("Contact Info (Phone/Address)")
        submit = st.form_submit_button("Create My AI")

        if submit:
            if s_name and s_slug and s_rules:
                # Database mein save karna
                entry = {"shop_name": s_name, "shop_slug": s_slug.lower(), "rules": s_rules, "contact_info": s_contact}
                supabase.table("shops").insert(entry).execute()
                
                st.success(f"Badhai ho! Aapka AI taiyar hai.")
                
                # Naya Automatic Link Logic
                base_url = "https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/"
                final_link = f"{base_url}?shop={s_slug.lower()}"
                
                st.info(f"Aapka Customer Link: {final_link}")
                st.write("Is link ko copy karein aur apne customer ko bhejein.")
            else:
                st.warning("Kripya saari details bharein.")

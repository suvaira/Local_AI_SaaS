import streamlit as st
from supabase import create_client
from huggingface_hub import InferenceClient

# 1. Database Setup
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Hugging Face AI Setup
# Hum 'Qwen/Qwen2.5-7B-Instruct' use kar rahe hain jo bahut smart model hai
client = InferenceClient(api_key=st.secrets["HF_TOKEN"])

# URL se shop ka naam uthana
if "shop" in st.query_params:
    shop_slug = st.query_params["shop"]
else:
    shop_slug = None

# --- PART A: CUSTOMER CHAT ---
if shop_slug:
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
    
    if data.data:
        shop = data.data[0]
        st.title(f"Welcome to {shop['shop_name']} 🤖")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Dukan ke baare mein kuch puchiye..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                # AI ko Instruction dena
                system_instruction = f"You are a helpful assistant for {shop['shop_name']}. Rules: {shop['rules']}. Contact: {shop['contact_info']}. Answer in Hindi/English mixed. Be polite and short."
                
                # AI se jawab mangna
                messages = [{"role": "system", "content": system_instruction}]
                for m in st.session_state.messages:
                    messages.append({"role": m["role"], "content": m["content"]})

                response = ""
                for message in client.chat_completion(
                    model="Qwen/Qwen2.5-7B-Instruct", # Ye model free aur fast hai
                    messages=messages,
                    max_tokens=500,
                    stream=True,
                ):
                    response += message.choices[0].delta.content or ""

                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            except Exception as e:
                st.error("AI thoda thak gaya hai, kripya 1 minute baad try karein.")
    else:
        st.error("Shop not found!")

# --- PART B: ADMIN PAGE ---
else:
    st.title("Local Shop AI Maker 🏪")
    st.write("Ek baar banayein, lifetime chalayein.")
    
    with st.form("setup"):
        name = st.text_input("Dukan ka Naam")
        slug = st.text_input("Shop Unique ID (e.g. suhani-ele)")
        rules = st.text_area("Dukan ke baare mein sab likh dein (Timing, Prices, Rules)")
        contact = st.text_input("Phone Number")
        if st.form_submit_button("Create My AI"):
            supabase.table("shops").insert({"shop_name": name, "shop_slug": slug.lower(), "rules": rules, "contact_info": contact}).execute()
            st.success("AI Tyar Hai!")
            st.info(f"Customer Link: https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?shop={slug.lower()}")

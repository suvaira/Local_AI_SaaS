 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/shop_ai_builder_streamlit.py b/shop_ai_builder_streamlit.py
new file mode 100644
index 0000000000000000000000000000000000000000..a01a04cd6e7d642790f7e7352f04281067d62b4c
--- /dev/null
+++ b/shop_ai_builder_streamlit.py
@@ -0,0 +1,356 @@
+import io
+from datetime import datetime
+
+import qrcode
+import streamlit as st
+from huggingface_hub import InferenceClient
+from PIL import Image, ImageDraw, ImageFont
+from supabase import create_client
+
+
+APP_BASE_URL = "https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app"
+
+
+def local_css() -> None:
+    """Polished CSS for customer chat and admin dashboard."""
+    st.markdown(
+        """
+        <style>
+            :root {
+                --brand-primary: #1e3a8a;
+                --brand-secondary: #2563eb;
+                --brand-accent: #0ea5e9;
+                --bg-soft: #f6f9fc;
+                --surface: #ffffff;
+                --text-main: #0f172a;
+            }
+
+            .stApp {
+                background: radial-gradient(circle at top right, #dbeafe 0%, #f8fafc 42%, #eef2ff 100%);
+                color: var(--text-main);
+            }
+
+            .main-header {
+                padding: 1.3rem 1.5rem;
+                border-radius: 20px;
+                background: linear-gradient(130deg, #1e3a8a 0%, #2563eb 54%, #38bdf8 100%);
+                color: #fff;
+                box-shadow: 0 18px 40px rgba(30, 58, 138, 0.22);
+                margin-bottom: 1.1rem;
+            }
+
+            .main-header h1 {
+                margin: 0;
+                font-weight: 800;
+                letter-spacing: 0.2px;
+            }
+
+            .main-header p {
+                margin: 0.2rem 0 0;
+                opacity: 0.94;
+            }
+
+            .glass-card {
+                background: rgba(255,255,255,0.85);
+                border: 1px solid rgba(148, 163, 184, 0.22);
+                border-radius: 18px;
+                padding: 1rem;
+                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
+                margin-bottom: .8rem;
+            }
+
+            .stChatMessage {
+                border-radius: 16px;
+                border: 1px solid #e2e8f0;
+                background: #fff;
+                box-shadow: 0 6px 22px rgba(15, 23, 42, 0.06);
+                padding: .55rem .75rem;
+                margin-bottom: .65rem;
+            }
+
+            .stChatInputContainer {
+                background: rgba(255,255,255,.93);
+                border: 1px solid #e2e8f0;
+                border-radius: 16px;
+                padding-bottom: 8px;
+            }
+
+            .stButton>button,
+            .stDownloadButton>button {
+                border-radius: 14px;
+                border: none;
+                font-weight: 700;
+                min-height: 46px;
+                background: linear-gradient(130deg, var(--brand-primary), var(--brand-secondary));
+                color: #fff;
+            }
+
+            .qr-card {
+                border-radius: 22px;
+                background: #fff;
+                border: 1px solid #dbeafe;
+                padding: 16px;
+                box-shadow: 0 12px 28px rgba(37, 99, 235, 0.12);
+                text-align: center;
+            }
+
+            .tiny-note {
+                font-size: .89rem;
+                color: #334155;
+            }
+        </style>
+        """,
+        unsafe_allow_html=True,
+    )
+
+
+def get_supabase_client():
+    url = st.secrets["SUPABASE_URL"]
+    key = st.secrets["SUPABASE_KEY"]
+    return create_client(url, key)
+
+
+def get_hf_client():
+    return InferenceClient(api_key=st.secrets["HF_TOKEN"])
+
+
+def build_shop_url(slug: str) -> str:
+    return f"{APP_BASE_URL}/?shop={slug.lower()}"
+
+
+def branded_qr_image(target_url: str, shop_name: str) -> Image.Image:
+    """Create a premium QR image with simple brand treatment and center label."""
+    qr = qrcode.QRCode(
+        version=1,
+        error_correction=qrcode.constants.ERROR_CORRECT_H,
+        box_size=14,
+        border=3,
+    )
+    qr.add_data(target_url)
+    qr.make(fit=True)
+
+    qr_img = qr.make_image(fill_color="#111827", back_color="white").convert("RGB")
+
+    canvas_size = qr_img.size[0] + 160
+    canvas = Image.new("RGB", (canvas_size, canvas_size + 120), "#f8fafc")
+    draw = ImageDraw.Draw(canvas)
+
+    # Card background
+    draw.rounded_rectangle(
+        (20, 20, canvas_size - 20, canvas_size - 20),
+        radius=35,
+        fill="#ffffff",
+        outline="#cbd5e1",
+        width=2,
+    )
+
+    # Paste QR in middle card
+    offset = ((canvas_size - qr_img.size[0]) // 2, 80)
+    canvas.paste(qr_img, offset)
+
+    # Badge (Google Pay inspired clean brand strip)
+    badge_w, badge_h = 300, 54
+    badge_x = (canvas_size - badge_w) // 2
+    badge_y = canvas_size - 40
+    draw.rounded_rectangle(
+        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
+        radius=24,
+        fill="#1e3a8a",
+    )
+
+    title = (shop_name or "Shop AI")[:28]
+    footer = "Scan & Chat with AI"
+
+    try:
+        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
+        font_footer = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
+        font_shop = ImageFont.truetype("DejaVuSans.ttf", 22)
+    except OSError:
+        font_title = font_footer = font_shop = ImageFont.load_default()
+
+    draw.text((44, 34), "AI SHOP QR", font=font_title, fill="#0f172a")
+    draw.text((48, canvas_size - 86), title, font=font_shop, fill="#334155")
+    draw.text((badge_x + 60, badge_y + 13), footer, font=font_footer, fill="#ffffff")
+
+    return canvas
+
+
+def qr_bytes(image: Image.Image) -> bytes:
+    buffer = io.BytesIO()
+    image.save(buffer, format="PNG")
+    return buffer.getvalue()
+
+
+def render_customer_chat(supabase, client, shop_slug: str) -> None:
+    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()
+    if not data.data:
+        st.error("Dukan nahi mili! कृपया QR ya link check karein.")
+        return
+
+    shop = data.data[0]
+    st.markdown(
+        f"""
+        <div class="main-header">
+            <h1>🏪 {shop['shop_name']}</h1>
+            <p>Fast, polite aur professional AI assistant — Hindi + English.</p>
+        </div>
+        """,
+        unsafe_allow_html=True,
+    )
+
+    st.markdown(
+        """
+        <div class="glass-card tiny-note">
+            Suggestion: Price, timing, delivery aur offers ke questions puchne ke liye niche chat use karein.
+        </div>
+        """,
+        unsafe_allow_html=True,
+    )
+
+    if "messages" not in st.session_state:
+        st.session_state.messages = [
+            {
+                "role": "assistant",
+                "content": "Namaste! 👋 Main aapki madad ke liye hoon. Aap products, timing, offers ya delivery ke bare mein puch sakte hain.",
+            }
+        ]
+
+    for message in st.session_state.messages:
+        avatar = "🤖" if message["role"] == "assistant" else "👤"
+        with st.chat_message(message["role"], avatar=avatar):
+            st.markdown(message["content"])
+
+    if prompt := st.chat_input("Dukan ke baare mein puchiye…"):
+        st.session_state.messages.append({"role": "user", "content": prompt})
+        with st.chat_message("user", avatar="👤"):
+            st.markdown(prompt)
+
+        try:
+            system_instruction = (
+                f"You are a premium support assistant for {shop['shop_name']}. "
+                f"Rules: {shop['rules']}. Contact: {shop['contact_info']}. "
+                "Keep responses short, friendly, practical, and bilingual (Hindi+English when useful)."
+            )
+
+            messages = [{"role": "system", "content": system_instruction}] + [
+                {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
+            ]
+
+            response = ""
+            with st.spinner("AI soch raha hai..."):
+                for chunk in client.chat_completion(
+                    model="Qwen/Qwen2.5-7B-Instruct",
+                    messages=messages,
+                    max_tokens=500,
+                    stream=True,
+                ):
+                    response += chunk.choices[0].delta.content or ""
+
+            with st.chat_message("assistant", avatar="🤖"):
+                st.markdown(response)
+
+            st.session_state.messages.append({"role": "assistant", "content": response})
+
+        except Exception:
+            st.warning("⚠️ Thodi der baad try karein, AI break le raha hai.")
+
+
+def render_admin(supabase) -> None:
+    st.markdown(
+        "<div class='main-header'><h1>SaaS Shop AI Builder 🚀</h1><p>Local dukaan ko digital, smart aur premium banayein.</p></div>",
+        unsafe_allow_html=True,
+    )
+
+    with st.sidebar:
+        st.header("Kaise Use Karein?")
+        st.write("1) Dukan details bharien.")
+        st.write("2) Rules mein products, delivery aur timing define karein.")
+        st.write("3) Link + branded QR download karke print karein.")
+
+    if "generated_url" not in st.session_state:
+        st.session_state.generated_url = ""
+    if "generated_qr" not in st.session_state:
+        st.session_state.generated_qr = b""
+    if "generated_slug" not in st.session_state:
+        st.session_state.generated_slug = ""
+
+    with st.container():
+        st.subheader("Naya Shop AI banayein")
+        with st.form("setup", clear_on_submit=True):
+            col1, col2 = st.columns(2)
+            with col1:
+                name = st.text_input("Dukan ka Naam", placeholder="Example: Sharma Sweets")
+                slug = st.text_input("Unique ID", placeholder="sharma-sweets")
+            with col2:
+                contact = st.text_input("Phone/Contact", placeholder="9876543210")
+
+            rules = st.text_area(
+                "Dukan ke Rules, Products aur Timing",
+                placeholder="Hum 9 baje khulte hain. Free delivery 2km tak hai...",
+            )
+
+            submitted = st.form_submit_button("Generate Professional AI + QR")
+            if submitted:
+                if name and slug:
+                    normalized_slug = slug.lower().strip()
+                    supabase.table("shops").upsert(
+                        {
+                            "shop_name": name.strip(),
+                            "shop_slug": normalized_slug,
+                            "rules": rules.strip(),
+                            "contact_info": contact.strip(),
+                            "updated_at": datetime.utcnow().isoformat(),
+                        },
+                        on_conflict="shop_slug",
+                    ).execute()
+
+                    created_url = build_shop_url(normalized_slug)
+                    qr_image = branded_qr_image(created_url, name.strip())
+
+                    st.session_state.generated_url = created_url
+                    st.session_state.generated_qr = qr_bytes(qr_image)
+                    st.session_state.generated_slug = normalized_slug
+
+                    st.balloons()
+                    st.success(f"Dukan '{name}' ka AI ready hai!")
+                else:
+                    st.error("Naam aur ID zaroori hai!")
+
+    if st.session_state.generated_url:
+        st.markdown("### Shop Live Assets")
+        cols = st.columns([1.2, 1])
+        with cols[0]:
+            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
+            st.code(st.session_state.generated_url, language="text")
+            st.link_button("🔗 Open Customer URL", st.session_state.generated_url)
+            st.download_button(
+                "⬇️ Download URL as TXT",
+                data=st.session_state.generated_url,
+                file_name=f"{st.session_state.generated_slug}-customer-link.txt",
+                mime="text/plain",
+            )
+            st.markdown("</div>", unsafe_allow_html=True)
+
+        with cols[1]:
+            st.markdown('<div class="qr-card">', unsafe_allow_html=True)
+            st.image(st.session_state.generated_qr, caption="Branded QR", use_container_width=True)
+            st.download_button(
+                "⬇️ Download Premium QR",
+                data=st.session_state.generated_qr,
+                file_name=f"{st.session_state.generated_slug}-premium-qr.png",
+                mime="image/png",
+            )
+            st.markdown("</div>", unsafe_allow_html=True)
+
+
+# App entrypoint
+st.set_page_config(page_title="SaaS Shop AI Builder", page_icon="🏪", layout="wide")
+local_css()
+supabase = get_supabase_client()
+hf_client = get_hf_client()
+
+shop_slug = st.query_params.get("shop")
+if shop_slug:
+    render_customer_chat(supabase, hf_client, shop_slug)
+else:
+    render_admin(supabase)
 
EOF
)

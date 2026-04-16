import io
from datetime import datetime
from urllib.parse import urlencode

import qrcode
import streamlit as st
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client


# ------------------------------
# Page + Theme Setup
# ------------------------------
st.set_page_config(
    page_title="SaaS Shop AI Builder",
    page_icon="🏪",
    layout="wide",
)


# ------------------------------
# UI Styling
# ------------------------------
def local_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f3f6fb;
            --surface: #ffffff;
            --text: #0f172a;
            --muted: #64748b;
            --primary: #1d4ed8;
            --secondary: #7c3aed;
            --success: #059669;
            --border: #e2e8f0;
            --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
            --radius: 18px;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(29,78,216,0.08), transparent 40%),
                radial-gradient(circle at top left, rgba(124,58,237,0.08), transparent 30%),
                var(--bg);
            color: var(--text);
        }

        .hero-card {
            background: linear-gradient(135deg, #111827 0%, #1e3a8a 45%, #7c3aed 100%);
            color: #fff;
            border-radius: 20px;
            padding: 28px;
            box-shadow: var(--shadow);
            margin-bottom: 16px;
        }

        .hero-card h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: .2px;
        }

        .hero-card p {
            margin: 8px 0 0;
            color: #e2e8f0;
            font-size: 1rem;
        }

        .section-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            box-shadow: var(--shadow);
            margin-bottom: 16px;
        }

        .meta-chip {
            display: inline-block;
            border: 1px solid rgba(255,255,255,0.35);
            padding: 6px 12px;
            border-radius: 999px;
            font-size: .85rem;
            margin-top: 12px;
            color: #e2e8f0;
        }

        .stChatMessage {
            border-radius: 16px;
            padding: 10px 12px;
            box-shadow: 0 4px 16px rgba(2, 6, 23, 0.07);
            border: 1px solid var(--border);
        }

        .stChatMessage[data-testid="stChatMessageContent"] {
            font-size: 1rem;
            line-height: 1.55;
        }

        .stChatInputContainer {
            background: rgba(255,255,255,0.72);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 8px;
            margin-top: 8px;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] button {
            width: 100%;
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            font-weight: 700;
            min-height: 46px;
        }

        [data-testid="stSidebar"] {
            background: #0f172a;
            color: #e2e8f0;
        }

        [data-testid="stSidebar"] * {
            color: #e2e8f0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------
# Utilities
# ------------------------------
def shop_url_from_slug(slug: str) -> str:
    params = urlencode({"shop": slug.lower().strip()})
    return f"https://localaisaas-4ma49cqnbwp8n9bir69ymz.streamlit.app/?{params}"


def _safe_font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_branded_qr(shop_name: str, slug: str, primary_color=(30, 58, 138)) -> bytes:
    """Generate a GPay-style branded QR card and return PNG bytes."""
    link = shop_url_from_slug(slug)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=3,
    )
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=primary_color, back_color="white").convert("RGB")
    qr_img = qr_img.resize((520, 520))

    card_w, card_h = 700, 980
    card = Image.new("RGB", (card_w, card_h), color=(245, 247, 252))
    draw = ImageDraw.Draw(card)

    # Header gradient-style blocks
    draw.rounded_rectangle((30, 30, card_w - 30, 220), radius=34, fill=(15, 23, 42))
    draw.rounded_rectangle((35, 35, card_w - 35, 215), radius=30, fill=(30, 58, 138))

    title_font = _safe_font(44)
    subtitle_font = _safe_font(26)
    small_font = _safe_font(22)
    shop_font = _safe_font(32)

    draw.text((60, 65), "SHOP AI", fill="white", font=title_font)
    draw.text((60, 125), "Smart Customer Assistant", fill=(226, 232, 240), font=subtitle_font)

    # QR container
    qr_box = (90, 250, card_w - 90, 770)
    draw.rounded_rectangle(qr_box, radius=30, fill="white", outline=(203, 213, 225), width=3)
    card.paste(qr_img, (90, 250))

    # Center logo style circle overlay
    badge_center = (card_w // 2, 510)
    badge_r = 56
    draw.ellipse(
        (badge_center[0] - badge_r, badge_center[1] - badge_r, badge_center[0] + badge_r, badge_center[1] + badge_r),
        fill=(30, 58, 138),
        outline="white",
        width=5,
    )
    draw.text((badge_center[0] - 22, badge_center[1] - 18), "AI", fill="white", font=_safe_font(36))

    # Footer
    short_name = shop_name.strip()[:28] + ("..." if len(shop_name.strip()) > 28 else "")
    draw.text((60, 800), f"{short_name}", fill=(15, 23, 42), font=shop_font)
    draw.text((60, 850), "Scan & Chat on WhatsApp-style Web Assistant", fill=(71, 85, 105), font=small_font)
    draw.text((60, 890), f"/{slug.lower()}", fill=(30, 58, 138), font=small_font)

    # Timestamp for printed usage
    stamp = datetime.utcnow().strftime("Generated: %Y-%m-%d %H:%M UTC")
    draw.text((60, 930), stamp, fill=(100, 116, 139), font=_safe_font(18))

    out = io.BytesIO()
    card.save(out, format="PNG")
    out.seek(0)
    return out.getvalue()


def init_clients():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    hf_token = st.secrets["HF_TOKEN"]
    return create_client(url, key), InferenceClient(api_key=hf_token)


# ------------------------------
# App Render
# ------------------------------
local_css()

supabase, hf_client = init_clients()
shop_slug = st.query_params.get("shop")

if shop_slug:
    data = supabase.table("shops").select("*").eq("shop_slug", shop_slug.lower()).execute()

    if data.data:
        shop = data.data[0]
        st.markdown(
            f"""
            <div class="hero-card">
                <h1>🏪 {shop['shop_name']}</h1>
                <p>Aapki sewa mein hamara AI Assistant — instant, polite aur professional support.</p>
                <span class="meta-chip">24x7 Smart Replies • Hindi + English</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_chat, col_meta = st.columns([2.2, 1], gap="large")

        with col_meta:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.subheader("Shop Details")
            st.write(f"**Contact:** {shop.get('contact_info') or 'Not set'}")
            st.write(f"**Slug:** `{shop.get('shop_slug', '')}`")
            st.write("**Rules:**")
            st.caption(shop.get("rules") or "No custom rules configured.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_chat:
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": (
                            f"Namaste! Main {shop['shop_name']} ka AI assistant hoon. "
                            "Aap products, delivery, price, timing ya offers ke baare mein pooch sakte hain."
                        ),
                    }
                ]

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                    st.markdown(msg["content"])

            prompt = st.chat_input("Type your question... (Hindi / English)")
            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)

                try:
                    system_instruction = (
                        f"You are the official assistant for {shop['shop_name']}. "
                        f"Business rules: {shop.get('rules')}. "
                        f"Contact info: {shop.get('contact_info')}. "
                        "Reply in clean Hindi/English, keep concise, and avoid hallucinating unavailable inventory."
                    )

                    model_messages = [{"role": "system", "content": system_instruction}] + [
                        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
                    ]

                    answer = ""
                    with st.spinner("AI assistant is typing..."):
                        for chunk in hf_client.chat_completion(
                            model="Qwen/Qwen2.5-7B-Instruct",
                            messages=model_messages,
                            max_tokens=500,
                            stream=True,
                        ):
                            answer += chunk.choices[0].delta.content or ""

                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

                except Exception:
                    st.warning("⚠️ Abhi response delay ho raha hai. Kripya kuch der baad try karein.")

    else:
        st.error("Dukan nahi mili. Kripya valid link use karein.")

else:
    st.markdown(
        """
        <div class='hero-card'>
            <h1>SaaS Shop AI Builder 🚀</h1>
            <p>Local dukan ko digital banayein with AI chat + branded QR onboarding.</p>
            <span class='meta-chip'>Create in 1 minute • Share instantly</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Setup Guide")
        st.write("1) Dukan details bharein.")
        st.write("2) Rules, timing aur offers set karein.")
        st.write("3) URL + QR print karke counter par lagayein.")
        st.divider()
        st.subheader("Pro Suggestions")
        st.caption("• Daily FAQ update karein")
        st.caption("• Delivery radius clearly define karein")
        st.caption("• Offer expiry date mention karein")

    c1, c2 = st.columns([1.6, 1], gap="large")

    with c1:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Naya Shop AI Banayein")

        with st.form("setup", clear_on_submit=False):
            f1, f2 = st.columns(2)
            with f1:
                name = st.text_input("Dukan ka Naam", placeholder="Example: Sharma Sweets")
                slug = st.text_input("Unique ID", placeholder="sharma-sweets")
            with f2:
                contact = st.text_input("Phone/WhatsApp", placeholder="9876543210")
                primary_brand = st.color_picker("QR Brand Color", "#1E3A8A")

            rules = st.text_area(
                "Dukan ke Rules, Products aur Timing",
                placeholder="Hum subah 9 baje khulte hain. 2km tak free delivery hai...",
                height=130,
            )

            submitted = st.form_submit_button("Generate Professional AI")

            if submitted:
                if not (name and slug):
                    st.error("Naam aur Unique ID dono zaroori hain.")
                else:
                    clean_slug = slug.lower().strip().replace(" ", "-")
                    supabase.table("shops").upsert(
                        {
                            "shop_name": name.strip(),
                            "shop_slug": clean_slug,
                            "rules": rules.strip(),
                            "contact_info": contact.strip(),
                        },
                        on_conflict="shop_slug",
                    ).execute()

                    st.success(f"✅ Dukan '{name}' ka AI ready hai!")
                    share_url = shop_url_from_slug(clean_slug)
                    st.info(f"Customer URL: {share_url}")

                    rgb = tuple(int(primary_brand[i : i + 2], 16) for i in (1, 3, 5))
                    qr_png = generate_branded_qr(name, clean_slug, primary_color=rgb)

                    st.download_button(
                        label="⬇️ Download Branded QR (PNG)",
                        data=qr_png,
                        file_name=f"{clean_slug}-qr.png",
                        mime="image/png",
                    )

                    st.image(qr_png, caption="Branded QR preview", use_container_width=False)

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Why this design works")
        st.write("✅ Mobile-friendly chat UI")
        st.write("✅ Brand-consistent visual identity")
        st.write("✅ Instant QR download for print/display")
        st.write("✅ Better trust with professional look")
        st.markdown("</div>", unsafe_allow_html=True)

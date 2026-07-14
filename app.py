import base64
import json
import mimetypes
import os
import socket
import uuid
from html import escape
from datetime import datetime
from typing import Optional
from urllib import error, request

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


load_dotenv()


st.set_page_config(
    page_title="Olist Copilot",
    page_icon="🤖",
    layout="wide",
)


PERSONAS = {
    "buyer": {
        "label": "Buyer",
        "icon": "🛒",
        "tagline": "Asisten belanja untuk Pembeli",
        "description": "Tanya rekomendasi produk, alternatif, dan alasan pemilihannya.",
        "role": "assistant",
        "accent": "#10b981",
        "suggestions": [
            "Rekomendasikan produk kategori rumah tangga dengan rating terbaik.",
            "Cari alternatif produk dengan review lebih tinggi.",
            "Bandingkan dua produk dan jelaskan alasannya.",
        ],
    },
    "seller": {
        "label": "Seller",
        "icon": "🏬",
        "tagline": "Asisten bisnis untuk Penjual",
        "description": "Pantau KPI, tren order, dan aksi prioritas berbasis insight.",
        "role": "mentor",
        "accent": "#8b5cf6",
        "suggestions": [
            "Tampilkan tren order 30 hari terakhir.",
            "Apa penyebab keterlambatan pengiriman minggu ini?",
            "Berikan 3 aksi prioritas untuk meningkatkan performa operasional.",
        ],
    },
}
DEFAULT_PERSONA = "buyer"


def persona_label(persona: str) -> str:
    info = PERSONAS.get(persona)
    if not info:
        return persona
    return f"{info['icon']} {info['label']}"


def get_config_value(key: str, default: str = "") -> str:
    env_value = os.getenv(key)
    if env_value not in (None, ""):
        return env_value

    try:
        secret_value = st.secrets.get(key, default)
    except Exception:
        secret_value = default

    if secret_value is None:
        return default
    return str(secret_value)


WEBHOOK_URL = get_config_value("OLIST_CHAT_WEBHOOK_URL")
WEBHOOK_TOKEN = get_config_value("OLIST_CHAT_WEBHOOK_TOKEN")
DEFAULT_NAME = get_config_value("OLIST_CHAT_DEFAULT_NAME", "John Doe")
DEFAULT_EMAIL = get_config_value("OLIST_CHAT_DEFAULT_EMAIL", "johndoemul@example.com")
APP_USERNAME = get_config_value("OLIST_CHAT_APP_USERNAME", "admin")
APP_PASSWORD = get_config_value("OLIST_CHAT_APP_PASSWORD", "admin123")


def render_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-top: #0b0f14;
            --bg-bottom: #11161d;
            --panel-bg: rgba(20, 27, 36, 0.94);
            --panel-elevated: rgba(27, 35, 46, 0.96);
            --panel-border: rgba(255, 255, 255, 0.1);
            --panel-shadow: rgba(0, 0, 0, 0.32);
            --text-main: #f3f4f6;
            --text-muted: #c0cad8;
            --text-soft: #94a3b8;
            --brand-from: #10b981;
            --brand-to: #8b5cf6;
            --buyer-accent: #10b981;
            --seller-accent: #8b5cf6;
        }

        html, body, [class*="css"] {
            font-family: "Plus Jakarta Sans", "Source Sans Pro", sans-serif;
        }

        body::before,
        body::after {
            content: "";
            position: fixed;
            border-radius: 50%;
            filter: blur(100px);
            z-index: 0;
            pointer-events: none;
        }

        body::before {
            width: 480px;
            height: 480px;
            background: rgba(16, 185, 129, 0.16);
            top: -180px;
            left: -140px;
        }

        body::after {
            width: 460px;
            height: 460px;
            background: rgba(139, 92, 246, 0.12);
            bottom: -160px;
            right: -120px;
        }

        .stApp {
            background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
        }

        .block-container {
            max-width: 960px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .app-header {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin-bottom: 0.4rem;
        }

        .app-header-badge {
            width: 52px;
            height: 52px;
            border-radius: 16px;
            background: linear-gradient(135deg, var(--brand-from), var(--brand-to));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            box-shadow: 0 10px 24px rgba(16, 185, 129, 0.3);
            flex-shrink: 0;
        }

        .app-header-title {
            font-size: 1.9rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.4;
            padding-top: 0.15em;
            background: linear-gradient(135deg, #f8fafc, #94a3b8);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .app-header-subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.1rem;
        }

        .persona-tagline-line {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin: 0 0 0.75rem 0;
        }

        .persona-tagline {
            font-weight: 700;
        }

        .persona-tagline.accent-buyer { color: var(--buyer-accent); }
        .persona-tagline.accent-seller { color: var(--seller-accent); }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f141b 0%, #141b24 100%);
            border-right: 1px solid var(--panel-border);
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.2rem;
        }

        .sidebar-brand-badge {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--brand-from), var(--brand-to));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.05rem;
            flex-shrink: 0;
        }

        .sidebar-brand-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text-main);
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            box-shadow: 0 10px 24px var(--panel-shadow);
        }

        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--text-main);
        }

        [data-testid="stSidebar"] button[kind="secondary"],
        [data-testid="stSidebar"] button[kind="primary"] {
            background: #1f2937;
            color: var(--text-main);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            color: var(--text-main) !important;
            border-radius: 12px;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] input,
        [data-testid="stSidebar"] [data-baseweb="select"] span {
            color: var(--text-main) !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            color: var(--text-main) !important;
        }

        .user-message-wrap {
            display: flex;
            justify-content: flex-end;
            margin: 0.75rem 0;
        }

        .user-message-card {
            max-width: 75%;
            background: #1e293b;
            color: var(--text-main);
            border-radius: 18px 18px 4px 18px;
            padding: 0.9rem 1rem;
            border: 1px solid var(--panel-border);
            box-shadow: 0 10px 24px var(--panel-shadow);
        }

        .user-message-persona {
            font-size: 0.72rem;
            color: var(--text-soft);
            margin-bottom: 0.35rem;
            letter-spacing: 0.02em;
        }

        .user-message-text {
            margin: 0;
            line-height: 1.5;
            color: var(--text-main);
        }


        [data-testid="stChatMessage"] {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 18px;
            padding: 0.4rem 0.55rem;
            box-shadow: 0 8px 24px var(--panel-shadow);
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div {
            color: var(--text-main);
        }

        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
            color: var(--text-main);
        }

        [data-testid="stChatMessage"] [data-testid="stCaptionContainer"] {
            color: var(--text-muted);
        }

        [data-testid="stAlertContainer"] {
            border-radius: 16px;
            border: 1px solid var(--panel-border);
            background: rgba(30, 41, 59, 0.94);
        }

        [data-testid="stChatInput"] {
            background: rgba(15, 23, 42, 0.98);
            border-radius: 18px;
            border: 1px solid var(--panel-border);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.24);
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }

        [data-testid="stChatInput"]:focus-within {
            border-color: var(--brand-from);
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15), 0 8px 24px rgba(15, 23, 42, 0.24);
        }

        [data-testid="stChatInput"] textarea {
            color: #f8fafc !important;
            caret-color: #f8fafc;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: var(--text-soft) !important;
        }

        [data-testid="stFileUploader"] {
            margin-top: 0;
            width: 3.25rem;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
            min-height: 3.25rem;
            padding: 0;
            border: none;
            background: transparent;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none;
        }

        [data-testid="stFileUploader"] button {
            width: 3.25rem !important;
            height: 3.25rem !important;
            min-width: 3.25rem !important;
            padding: 0 !important;
            border-radius: 999px !important;
            border: 1px solid var(--panel-border) !important;
            background: rgba(15, 23, 42, 0.98) !important;
            color: var(--text-main) !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.24);
        }

        [data-testid="stFileUploader"] button span {
            font-size: 0 !important;
        }

        [data-testid="stFileUploader"] button::before {
            content: "＋";
            display: block;
            font-size: 1.5rem;
            line-height: 1;
            font-weight: 600;
            color: var(--text-main);
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {
            display: none;
        }

        h1, h2, h3 {
            color: var(--text-main) !important;
        }

        .stApp > header,
        [data-testid="stHeader"],
        [data-testid="stAppToolbar"],
        [data-testid="stToolbar"],
        [data-testid="stAppDeployButton"],
        [data-testid="stDecoration"] {
            background: transparent;
            box-shadow: none;
        }

        #MainMenu,
        footer,
        [data-testid="stStatusWidget"] {
            visibility: hidden;
            height: 0;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stVerticalBlock"] {
            color: var(--text-main);
        }

        .stMarkdown p,
        .stCaption {
            color: var(--text-muted);
        }

        .stInfo,
        .stSuccess,
        .stWarning,
        .stError {
            color: var(--text-main);
        }

        .stRadio label,
        .stSelectbox label,
        .stChatInputContainer label {
            color: var(--text-main) !important;
        }

        [data-testid="stSegmentedControl"] label {
            font-size: 0.95rem;
            padding: 0.5rem 1.1rem !important;
        }

        .stButton button,
        [data-testid="stFormSubmitButton"] button {
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }

        .stButton button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            border-color: var(--brand-from);
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.22);
            transform: translateY(-1px);
        }

        .welcome-card {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            border-left: 4px solid transparent;
            border-radius: 20px;
            padding: 1.5rem 1.7rem;
            box-shadow: 0 16px 32px var(--panel-shadow);
            margin: 0.5rem 0 1.25rem 0;
        }

        .welcome-card.accent-buyer {
            border-left-color: var(--buyer-accent);
            box-shadow: 0 16px 32px var(--panel-shadow), 0 0 0 1px rgba(16, 185, 129, 0.14);
        }

        .welcome-card.accent-seller {
            border-left-color: var(--seller-accent);
            box-shadow: 0 16px 32px var(--panel-shadow), 0 0 0 1px rgba(139, 92, 246, 0.14);
        }

        .welcome-title-row {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.6rem;
        }

        .welcome-icon-badge {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.06);
        }

        .accent-buyer .welcome-icon-badge { background: rgba(16, 185, 129, 0.16); }
        .accent-seller .welcome-icon-badge { background: rgba(139, 92, 246, 0.16); }

        .welcome-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .welcome-text {
            color: var(--text-muted);
            margin: 0 0 0.75rem 0;
            line-height: 1.5;
        }

        .welcome-hint {
            color: var(--text-soft);
            font-size: 0.85rem;
            margin: 0;
            line-height: 1.5;
        }

        .st-key-login_card {
            max-width: 440px;
            margin: 2.5rem auto 0 auto;
            padding: 2.2rem 2rem 1.6rem 2rem !important;
            border-radius: 24px !important;
            background: var(--panel-elevated) !important;
            border: 1px solid var(--panel-border) !important;
            box-shadow: 0 24px 60px var(--panel-shadow) !important;
            text-align: center;
        }

        .login-badge {
            width: 64px;
            height: 64px;
            margin: 0 auto 1rem auto;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--brand-from), var(--brand-to));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            box-shadow: 0 12px 30px rgba(16, 185, 129, 0.35);
        }

        .login-title {
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, var(--brand-from), var(--brand-to));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 0.2rem;
        }

        .login-subtitle {
            color: var(--text-muted);
            font-size: 0.92rem;
            margin-bottom: 1.2rem;
        }

        .login-chips {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }

        .persona-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid transparent;
        }

        .persona-chip.accent-buyer {
            background: rgba(16, 185, 129, 0.12);
            color: #6ee7b7;
            border-color: rgba(16, 185, 129, 0.35);
        }

        .persona-chip.accent-seller {
            background: rgba(139, 92, 246, 0.12);
            color: #c4b5fd;
            border-color: rgba(139, 92, 246, 0.35);
        }

        .st-key-login_card [data-testid="stTextInputRootElement"] {
            background: rgba(15, 23, 42, 0.85) !important;
            border-radius: 12px !important;
        }

        .st-key-login_card [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, var(--brand-from), var(--brand-to));
            border: none;
            color: #0b0f14;
            font-weight: 700;
            margin-top: 0.4rem;
        }

        .st-key-login_card [data-testid="stFormSubmitButton"] button:hover {
            filter: brightness(1.08);
            box-shadow: 0 14px 28px rgba(16, 185, 129, 0.4);
        }

        .login-footer {
            color: var(--text-soft);
            font-size: 0.78rem;
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "name" not in st.session_state:
        st.session_state.name = DEFAULT_NAME
    if "email" not in st.session_state:
        st.session_state.email = DEFAULT_EMAIL


def render_login() -> None:
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        with st.container(key="login_card", border=True):
            st.markdown(
                """
                <div class="login-badge">🤖</div>
                <div class="login-title">Olist Copilot</div>
                <p class="login-subtitle">Asisten AI belanja &amp; bisnis Olist</p>
                <div class="login-chips">
                    <span class="persona-chip accent-buyer">🛒 Buyer</span>
                    <span class="persona-chip accent-seller">🏬 Seller</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                username = st.text_input("👤 Username")
                password = st.text_input("🔒 Password", type="password")
                submitted = st.form_submit_button("Masuk →", use_container_width=True)

            if submitted:
                if username == APP_USERNAME and password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Username atau password salah.")

            st.markdown(
                '<p class="login-footer">🔒 Akses terbatas — hubungi admin untuk kredensial.</p>',
                unsafe_allow_html=True,
            )


def build_multipart_body(fields: dict[str, str], file_field: Optional[tuple[str, str, bytes]] = None) -> tuple[bytes, str]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for key, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    if file_field is not None:
        field_name, filename, file_bytes = file_field
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8"),
                file_bytes,
                b"\r\n",
            ]
        )

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def render_attachment_widget(attachment: dict) -> None:
    name = attachment.get("name", "file")
    mime = attachment.get("mime") or "application/octet-stream"
    data_b64 = attachment.get("data", "")
    safe_name = escape(name)
    is_image = mime.startswith("image/")

    if is_image:
        trigger_html = f'<img class="preview" src="data:{mime};base64,{data_b64}" alt="{safe_name}" />'
        height = 176
    else:
        trigger_html = f'<span class="chip"><span class="icon">📄</span>{safe_name}</span>'
        height = 44

    components.html(
        f"""
        <style>
          html, body {{ margin: 0; padding: 0; background: transparent; font-family: "Source Sans Pro", sans-serif; }}
          .preview {{
            display: block; max-width: 160px; max-height: 160px; border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1); cursor: pointer; object-fit: cover;
          }}
          .chip {{
            display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.65rem;
            border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(15, 23, 42, 0.65); color: #c0cad8; font-size: 0.78rem;
            line-height: 1; cursor: pointer; width: fit-content;
          }}
          .chip:hover {{ border-color: #94a3b8; color: #f3f4f6; }}
          .icon {{ color: #94a3b8; font-size: 0.8rem; }}
        </style>
        <div onclick="openAttachment()">{trigger_html}</div>
        <script>
          function openAttachment() {{
            const byteChars = atob("{data_b64}");
            const byteNumbers = new Array(byteChars.length);
            for (let i = 0; i < byteChars.length; i++) {{
              byteNumbers[i] = byteChars.charCodeAt(i);
            }}
            const blob = new Blob([new Uint8Array(byteNumbers)], {{ type: "{mime}" }});
            window.open(URL.createObjectURL(blob), "_blank");
          }}
        </script>
        """,
        height=height,
    )


def render_user_bubble(question: str, persona: str, attachment: Optional[dict] = None) -> None:
    with st.chat_message("user", avatar="🙋"):
        st.caption(persona_label(persona))
        st.write(question)

        if attachment:
            render_attachment_widget(attachment)


def render_loading_bubble(persona: str) -> None:
    icon = PERSONAS.get(persona, {}).get("icon", "🤖")
    with st.chat_message("assistant", avatar=icon):
        st.caption(f"{persona_label(persona)} • memproses...")
        


def process_question(question: str, persona: str, uploaded_files: Optional[list[object]] = None) -> None:
    if not question.strip():
        st.error("Pertanyaan tidak boleh kosong.")
        return
    if not st.session_state.name.strip() or not st.session_state.email.strip():
        st.error("Nama dan email wajib diisi.")
        return
    if not WEBHOOK_URL or not WEBHOOK_TOKEN:
        st.error("Konfigurasi API belum lengkap. Isi OLIST_CHAT_WEBHOOK_URL dan OLIST_CHAT_WEBHOOK_TOKEN di .env atau Streamlit Secrets.")
        return

    attachment = build_attachment(uploaded_files)

    render_user_bubble(question, persona, attachment=attachment)
    render_loading_bubble(persona)

    try:
        with st.spinner("Memproses pertanyaan..."):
            response = call_backend(question=question, persona=persona, uploaded_files=uploaded_files)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Terjadi error tak terduga saat memproses permintaan. Silakan coba lagi.")
        return

    response["attachment"] = attachment
    st.session_state.chat_history.append(response)


def build_attachment(uploaded_files: Optional[list[object]] = None) -> Optional[dict]:
    if not uploaded_files:
        return None

    first_file = uploaded_files[0]
    name = getattr(first_file, "name", "")
    if not name:
        return None

    mime = getattr(first_file, "type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
    file_bytes = first_file.getvalue() if hasattr(first_file, "getvalue") else first_file.read()

    return {
        "name": name,
        "mime": mime,
        "data": base64.b64encode(file_bytes).decode("utf-8"),
    }


def parse_api_response(response_body: str) -> tuple[str, list[str], list[tuple[str, str, str]], str]:
    payload = json.loads(response_body)
    if not isinstance(payload, list) or not payload:
        raise ValueError("Format response API tidak sesuai.")

    first_item = payload[0]
    raw_output = first_item.get("output", "")
    parsed_output = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
    if not isinstance(parsed_output, dict):
        raise ValueError("Field output API tidak valid.")

    message = parsed_output.get("message", "Tidak ada jawaban dari API.")
    sources = parsed_output.get("sources", [])
    kpis = parsed_output.get("kpis", [])
    mode = parsed_output.get("mode", "Auto")
    return message, sources, kpis, mode


def call_backend(question: str, persona: str, uploaded_files: Optional[list[object]] = None) -> dict:
    """Call the chat webhook and normalize the response for the UI."""
    timestamp = datetime.now().strftime("%H:%M")

    fields = {
        "role": PERSONAS[persona]["role"],
        "name": st.session_state.name.strip(),
        "email": st.session_state.email.strip(),
        "message": question.strip(),
    }
    file_payload = None
    uploaded_file_name = None

    if uploaded_files:
        first_file = uploaded_files[0]
        uploaded_file_name = getattr(first_file, "name", None)
        file_bytes = first_file.getvalue() if hasattr(first_file, "getvalue") else first_file.read()
        if uploaded_file_name:
            file_payload = ("file", uploaded_file_name, file_bytes)

    body, content_type = build_multipart_body(fields, file_payload)
    req = request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "x-token-webhook": WEBHOOK_TOKEN,
            "Content-Type": content_type,
            "Accept": "*/*",
            "User-Agent": "curl/8.7.1",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            response_body = response.read().decode("utf-8")
        answer, sources, kpis, mode = parse_api_response(response_body)
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            "Request ke API melebihi batas waktu 60 detik. Silakan coba lagi dalam beberapa saat."
        ) from exc
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API mengembalikan error {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gagal terhubung ke API: {exc.reason}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Response API tidak bisa diproses: {exc}") from exc

    return {
        "timestamp": timestamp,
        "persona": persona,
        "answer": answer,
        "recommendations": [],
        "sources": sources,
        "kpis": kpis,
        "mode": mode,
        "question": question,
    }


def render_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-badge">🤖</div>
            <div class="sidebar-brand-title">Olist Copilot</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Satu AI, dua peran: bantu Anda belanja atau kelola toko.")

    with st.sidebar.expander("ℹ️ Tentang aplikasi", expanded=True):
        st.markdown(
            "- 🛒 **Buyer** — rekomendasi produk, perbandingan, dan alasan pemilihannya.\n"
            "- 🏬 **Seller** — insight KPI, tren order, dan aksi prioritas toko.\n"
            "- 📎 Bisa lampirkan **gambar** (JPG/PNG/WEBP) atau **PDF** saat bertanya, "
            "klik ikon **＋** di sebelah kotak chat."
        )

    st.sidebar.divider()
    if st.sidebar.button("🚪 Keluar", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


def render_persona_switcher() -> str:
    options = list(PERSONAS.keys())
    current = st.session_state.get("active_persona", DEFAULT_PERSONA)

    st.write("**Pilih peran Anda**")
    selected = st.segmented_control(
        "Pilih peran Anda",
        options=options,
        format_func=persona_label,
        default=current,
        key="persona_switch",
        label_visibility="collapsed",
    )
    persona = selected or current

    if st.session_state.get("active_persona") != persona:
        st.session_state.active_persona = persona
        st.session_state.chat_history = []

    info = PERSONAS[persona]
    st.markdown(
        f'<p class="persona-tagline-line">'
        f'<span class="persona-tagline accent-{persona}">{info["tagline"]}</span> — {info["description"]}'
        f"</p>",
        unsafe_allow_html=True,
    )

    return persona


def render_quick_prompts(persona: str) -> None:
    st.caption("💡 Coba tanyakan:")
    suggestions = PERSONAS[persona]["suggestions"]
    columns = st.columns(len(suggestions))

    for index, suggestion in enumerate(suggestions):
        with columns[index]:
            if st.button(suggestion, key=f"quick_prompt_{persona}_{index}", use_container_width=True):
                process_question(suggestion, persona)
                st.rerun()


def render_welcome_card(persona: str) -> None:
    info = PERSONAS[persona]
    st.markdown(
        f"""
        <div class="welcome-card accent-{persona}">
            <div class="welcome-title-row">
                <div class="welcome-icon-badge">{info['icon']}</div>
                <div class="welcome-title">Halo, saya {info['label']} Copilot</div>
            </div>
            <p class="welcome-text">{info['description']}</p>
            <p class="welcome-hint">
                📎 Anda juga bisa melampirkan <strong>gambar</strong> (JPG, PNG, WEBP) atau
                <strong>PDF</strong> saat bertanya — klik ikon <strong>＋</strong> di sebelah kotak chat.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat(persona: str) -> None:
    if not st.session_state.chat_history:
        render_welcome_card(persona)
        return

    for entry in st.session_state.chat_history:
        entry_persona = entry.get("persona", persona)
        attachment = entry.get("attachment")
        icon = PERSONAS.get(entry_persona, {}).get("icon", "🤖")

        render_user_bubble(entry["question"], entry_persona, attachment=attachment)

        with st.chat_message("assistant", avatar=icon):
            st.caption(f"{persona_label(entry_persona)} • {entry['timestamp']} • {entry['mode']}")
            st.write(entry["answer"])
            if entry["recommendations"]:
                st.write("Rekomendasi")
                for item in entry["recommendations"]:
                    st.markdown(f"- {item}")


def main() -> None:
    initialize_state()
    render_styles()

    if not st.session_state.authenticated:
        render_login()
        return

    render_sidebar()

    st.markdown(
        """
        <div class="app-header">
            <div class="app-header-badge">🤖</div>
            <div>
                <div class="app-header-title">Olist Copilot</div>
                <div class="app-header-subtitle">
                    Asisten AI yang membantu Anda sebagai <strong>Buyer</strong> (pembeli)
                    maupun <strong>Seller</strong> (penjual) di Olist.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    persona = render_persona_switcher()
    render_chat(persona)
    if not st.session_state.chat_history:
        render_quick_prompts(persona)

    st.caption("📎 Bisa lampirkan gambar (JPG/PNG/WEBP) atau PDF — klik ikon ＋ di sebelah kotak chat sebelum kirim.")
    prompt = st.chat_input(
        "Tulis pertanyaan Anda di sini...",
        accept_file=True,
        file_type=["jpg", "jpeg", "png", "webp", "pdf"],
        key="chat_input",
    )

    if prompt:
        prompt_text = prompt.text if hasattr(prompt, "text") else str(prompt)
        prompt_files = list(prompt.files) if hasattr(prompt, "files") and prompt.files else []
        process_question(prompt_text, persona, uploaded_files=prompt_files)
        st.rerun()


if __name__ == "__main__":
    main()
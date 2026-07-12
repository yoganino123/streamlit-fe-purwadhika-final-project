import json
import mimetypes
import os
import socket
import uuid
from datetime import datetime
from typing import Optional
from urllib import error, request

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


st.set_page_config(
    page_title="Olist Copilot",
    page_icon="💬",
    layout="wide",
)


PERSONAS = {
    "Users Copilot Chat": {
        "description": "Tanya rekomendasi produk, alternatif, dan alasan pemilihannya.",
        "suggestions": [
            "Rekomendasikan produk kategori rumah tangga dengan rating terbaik.",
            "Cari alternatif produk dengan review lebih tinggi.",
            "Bandingkan dua produk dan jelaskan alasannya.",
        ],
    },
    "Mentor Dashboard": {
        "description": "Pantau KPI, tren order, dan aksi prioritas berbasis insight.",
        "suggestions": [
            "Tampilkan tren order 30 hari terakhir.",
            "Apa penyebab keterlambatan pengiriman minggu ini?",
            "Berikan 3 aksi prioritas untuk meningkatkan performa operasional.",
        ],
    },
}

PERSONA_TO_ROLE = {
    "Users Copilot Chat": "assistant",
    "Mentor Dashboard": "mentor",
}


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


def render_styles() -> None:
    st.markdown(
        """
        <style>
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
        }

        .stApp {
            background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
        }

        .block-container {
            max-width: 900px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f141b 0%, #141b24 100%);
            border-right: 1px solid var(--panel-border);
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

        .stApp > header {
            background: transparent;
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "name" not in st.session_state:
        st.session_state.name = DEFAULT_NAME
    if "email" not in st.session_state:
        st.session_state.email = DEFAULT_EMAIL


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

    try:
        with st.spinner("Memproses pertanyaan..."):
            response = call_backend(question=question, persona=persona, uploaded_files=uploaded_files)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Terjadi error tak terduga saat memproses permintaan. Silakan coba lagi.")
        return

    st.session_state.chat_history.append(response)


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
        "role": PERSONA_TO_ROLE[persona],
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
        "file_name": uploaded_file_name,
    }


def render_sidebar() -> str:
    # st.sidebar.title("Workspace")
    persona = st.sidebar.radio("Persona", options=list(PERSONAS.keys()))
    # st.sidebar.text_input("Name", key="name")
    # st.sidebar.text_input("Email", key="email")
    st.sidebar.caption(PERSONAS[persona]["description"])

    return persona


def render_quick_prompts(persona: str) -> None:
    st.caption("Prompt cepat")
    suggestions = PERSONAS[persona]["suggestions"]
    columns = st.columns(len(suggestions))

    for index, suggestion in enumerate(suggestions):
        with columns[index]:
            if st.button(suggestion, key=f"quick_prompt_{persona}_{index}", use_container_width=True):
                process_question(suggestion, persona)
                st.rerun()


def render_chat(persona: str) -> None:
    if not st.session_state.chat_history:
        # st.info("Mulai percakapan dari kolom chat di bawah.")
        return

    for entry in st.session_state.chat_history:
        entry_persona = entry.get("persona", persona)

        st.markdown(
            f"""
            <div class="user-message-wrap">
                <div class="user-message-card">
                    <div class="user-message-persona">{entry_persona}</div>
                    <p class="user-message-text">{entry['question']}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.chat_message("assistant"):
            st.caption(f"{entry_persona} • {entry['timestamp']} • {entry['mode']}")
            st.write(entry["answer"])
            if entry["recommendations"]:
                st.write("Rekomendasi")
                for item in entry["recommendations"]:
                    st.markdown(f"- {item}")


def main() -> None:
    initialize_state()
    render_styles()
    persona = render_sidebar()
    st.title("Olist Copilot")
    st.caption(PERSONAS[persona]["description"])

    render_chat(persona)
    render_quick_prompts(persona)

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
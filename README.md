# Streamlit Frontend

## Setup (macOS/Linux)

1. Buat virtual environment:

   python3 -m venv .venv

2. Aktifkan virtual environment:

   source .venv/bin/activate

3. Install dependencies:

   python -m pip install -r requirements.txt

4. Jalankan app:

   streamlit run app.py

## Catatan

- Jika perintah `pip` tidak dikenali, gunakan `python -m pip` atau `python3 -m pip`.
- Di beberapa mesin, `pip` tidak tersedia tetapi `pip3` tersedia.

## Deploy ke Streamlit Community Cloud

1. Push project ini ke GitHub.
2. Buka https://share.streamlit.io.
3. Pilih repository, branch, dan file utama `app.py`.
4. Pastikan `requirements.txt` ikut ter-commit.
5. Set Python runtime ke `python-3.11` melalui [runtime.txt](runtime.txt) atau pengaturan app.
6. Copy isi [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) ke Secrets Streamlit Cloud:

   ```toml
   OLIST_CHAT_WEBHOOK_URL = "https://..."
   OLIST_CHAT_WEBHOOK_TOKEN = "..."
   OLIST_CHAT_DEFAULT_NAME = "John Doe"
   OLIST_CHAT_DEFAULT_EMAIL = "johndoemul@example.com"
   ```

Catatan: di Streamlit Cloud, credential lebih aman disimpan di Secrets daripada di `.env`. File [`.streamlit/secrets.toml`](.streamlit/secrets.toml) tetap jangan di-commit.

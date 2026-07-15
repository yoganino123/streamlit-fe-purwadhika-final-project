w

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

## Setup (Windows)

1. Buat virtual environment:

   py -m venv .venv
2. Aktifkan virtual environment:

   .venv\Scripts\activate
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
   OLIST_CHAT_APP_USERNAME = "admin"
   OLIST_CHAT_APP_PASSWORD = "admin123"

   DB_HOST = "..."
   DB_PORT = "3306"
   DB_USER = "..."
   DB_PASSWORD = "..."
   DB_NAME = "..."
   DB_SSL_CA = """-----BEGIN CERTIFICATE-----
   ...
   -----END CERTIFICATE-----"""
   ```

Catatan: di Streamlit Cloud, credential lebih aman disimpan di Secrets daripada di `.env`. File [`.streamlit/secrets.toml`](.streamlit/secrets.toml) tetap jangan di-commit.

## Login & Manajemen User (MySQL)

Login memakai tabel `users` di database MySQL (dibuat otomatis saat app pertama kali jalan, lewat `init_database()` di [app.py](app.py)). Kolom: `username`, `password_hash` (bcrypt), `name`, `email`, `role` (`user`/`admin`).

- **Env var wajib**: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`. Kalau DB pakai SSL (mis. Aiven), isi juga `DB_SSL_CA` dengan isi certificate CA (format PEM, boleh multi-baris).
- **Akun admin awal**: kalau tabel `users` masih kosong, satu akun admin otomatis dibuat dari `OLIST_CHAT_APP_USERNAME` / `OLIST_CHAT_APP_PASSWORD` (default `admin` / `admin123`) — pakai ini untuk login pertama kali, lalu ganti passwordnya lewat halaman **🛠️ Kelola User**.
- **Halaman admin**: user dengan role `admin` akan melihat tombol "🛠️ Kelola User" di sidebar untuk create/edit/delete user lain. Admin tidak bisa menghapus akunnya sendiri atau menghapus admin terakhir yang tersisa.
- **Payload ke n8n**: field `name` dan `email` yang dikirim ke webhook otomatis mengikuti akun yang sedang login (bukan lagi nilai statis).

"""UP3 submission form and status list for the internet-facing viewer."""
import re
from uuid import uuid4
import smtplib
from email.message import EmailMessage

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError

SCHEMA_RE = re.compile(r"^[a-z]+_[0-9]{4}$")
TABLE_RE = re.compile(r"^(?:20\d{4}|20\d{6})_ADD_[A-Za-z0-9_]+$", re.I)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def assigned_schemas(role, schema):
    # UID admin sees reports for all UP3, but a submission always needs
    # a specific assigned UP3. No wildcard/schema substring matching.
    return [s for s in (x.strip() for x in schema.split(",")) if SCHEMA_RE.fullmatch(s)]


def submit_request(engine, username, account, schema, table, expected_rows, notes):
    allowed = assigned_schemas(account.get("role", ""), account.get("schema", ""))
    email = str(account.get("email", "")).strip().lower()
    table = table.strip()
    if schema not in allowed or not TABLE_RE.fullmatch(table):
        raise ValueError("Schema atau nama tabel pengajuan tidak sesuai.")
    if not EMAIL_RE.fullmatch(email):
        raise ValueError("Alamat email akun belum dikonfigurasi.")
    if expected_rows is not None and expected_rows < 0:
        raise ValueError("Jumlah record tidak valid.")
    request_id = str(uuid4())
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO public.maghes_verification_requests
              (id, schema_name, table_name, requested_by, requester_email, expected_rows, notes)
            VALUES (:id, :schema, :table, :username, :email, :rows, :notes)
            ON CONFLICT DO NOTHING RETURNING id
        """), {"id": request_id, "schema": schema, "table": table,
                "username": username, "email": email, "rows": expected_rows,
                "notes": notes.strip()[:500]}).scalar_one_or_none()
    if row is None:
        raise ValueError("Tabel ini masih mempunyai pengajuan aktif. Lihat statusnya di bawah.")
    return request_id


def list_requests(engine, username, account):
    allowed = assigned_schemas(account.get("role", ""), account.get("schema", ""))
    if not allowed:
        return pd.DataFrame()
    stmt = text("""
        SELECT id, schema_name, table_name, expected_rows, status,
               requested_at, updated_at, published_id, request_notified_at, result_notified_at
          FROM public.maghes_verification_requests
         WHERE requested_by = :username AND schema_name IN :schemas
         ORDER BY requested_at DESC LIMIT 30
    """).bindparams(bindparam("schemas", expanding=True))
    return pd.read_sql(stmt, engine, params={"username": username, "schemas": allowed})


def _mail_config():
    try:
        return (st.secrets["GMAIL_SENDER"], st.secrets["GMAIL_APP_PASSWORD"],
                st.secrets["REVIEWER_EMAIL"])
    except (KeyError, FileNotFoundError):
        return None


def notify_reviewer(engine, request_id, schema, table, username, rows, notes):
    config = _mail_config()
    if not config:
        return False
    sender, app_password, reviewer = config
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = reviewer
    msg["Subject"] = f"[MAGHES] Pengajuan verifikasi {schema}.{table}"
    msg.set_content(
        f"Pengajuan: {request_id}\nUP3: {schema}\nTabel: {table}\n"
        f"Pengaju: {username}\nPerkiraan record: {rows if rows is not None else 'belum diisi'}\n"
        f"Catatan: {notes[:500]}\n\nBuka antrean MAGHES internal untuk memeriksa data."
    )
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender, app_password)
            server.send_message(msg)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE public.maghes_verification_requests
                   SET request_notified_at = now()
                 WHERE id = :id AND requested_by = :username AND request_notified_at IS NULL
            """), {"id": request_id, "username": username})
        return True
    except (OSError, smtplib.SMTPException):
        return False


def render_submission_portal(engine, username, role, schema, account):
    st.markdown("### 📨 Ajukan Verifikasi")
    st.caption("Selesaikan upload di QGIS dahulu, lalu catat tabelnya di sini. Tim UID akan memeriksa data di intranet.")
    allowed = assigned_schemas(role, schema)
    if not allowed:
        st.info("Akun ini belum memiliki penugasan UP3 untuk membuat pengajuan.")
        return
    if not EMAIL_RE.fullmatch(str(account.get("email", "")).strip()):
        st.warning("Email akun UP3 belum diatur. Hubungi pengelola MAGHES sebelum mengajukan.")
        return
    with st.form("maghes_request_form", clear_on_submit=True):
        selected = st.selectbox("UP3", allowed)
        table = st.text_input("Nama tabel yang selesai diunggah melalui QGIS",
                              placeholder="202610_ADD_APP")
        count_text = st.text_input("Perkiraan jumlah record (opsional)", placeholder="Contoh: 72000")
        notes = st.text_area("Catatan untuk verifikator (opsional)", max_chars=500)
        submitted = st.form_submit_button("📨 Ajukan Verifikasi", type="primary")
    if submitted:
        try:
            rows = int(count_text) if count_text.strip() else None
            request_id = submit_request(engine, username, account, selected, table, rows, notes)
            mailed = notify_reviewer(engine, request_id, selected, table.strip(), username, rows, notes)
            st.success("Pengajuan tersimpan dan masuk antrean UID." +
                       (" Email pemberitahuan terkirim." if mailed else
                        " Email belum terkirim; pengajuan tetap terlihat di antrean UID."))
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Pengajuan belum tersimpan. Periksa koneksi atau hubungi pengelola.")
    try:
        history = list_requests(engine, username, account)
        if not history.empty:
            st.markdown("#### Status pengajuan saya")
            st.dataframe(history[["schema_name", "table_name", "expected_rows",
                                  "status", "requested_at", "updated_at"]],
                         use_container_width=True, hide_index=True)
            if _mail_config():
                pending = history[history["request_notified_at"].isna() &
                                  (history["status"] == "DIAJUKAN")]
                if not pending.empty and st.button("Kirim ulang email pengajuan yang tertunda"):
                    sent = 0
                    for _, item in pending.iterrows():
                        if notify_reviewer(engine, str(item["id"]), item["schema_name"],
                                           item["table_name"], username,
                                           item["expected_rows"], ""):
                            sent += 1
                    st.info(f"Email terkirim: {sent} dari {len(pending)} pengajuan.")
    except Exception:
        st.info("Riwayat pengajuan belum tersedia; minta pengelola menjalankan migrasi tabel pengajuan.")

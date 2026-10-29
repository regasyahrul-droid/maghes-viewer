"""UP3 submission form and status list for the internet-facing viewer."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
import smtplib
from email.message import EmailMessage

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text

SCHEMA_RE = re.compile(r"^[a-z]+_[0-9]{4}$")
TABLE_RE = re.compile(r"^(?:20\d{4}|20\d{6})_ADD_[A-Za-z0-9_]+$", re.I)
PERIOD_RE = re.compile(r"^20\d{2}(?:0[1-9]|1[0-2])$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MONTH_NAMES = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)


def month_label(period):
    value = str(period)
    if not PERIOD_RE.fullmatch(value):
        return value
    return f"{MONTH_NAMES[int(value[4:6]) - 1]} {value[:4]}"


MONTH_RE = re.compile(r"^(20\d{2})(0[1-9]|1[0-2])(?:\d{2})?_")


def table_month(table_name):
    """Kelompokkan tabel YYYYMM dan YYYYMMDD pada bulan data yang sama."""
    match = MONTH_RE.match(str(table_name).upper())
    return f"{match.group(1)}{match.group(2)}" if match else None


ASSET_TYPES = (
    "APP",
    "ARRESTER",
    "BUSBAR_GHGD",
    "CO",
    "EV_CHARGER",
    "GARDU_DISTRIBUSI",
    "ISOLATOR",
    "JOINTING",
    "JTM",
    "JTR",
    "LVCABLE",
    "MVCABLE",
    "MVCELL_GDGH",
    "PERALATAN_TIANG_LAIN",
    "PHB_SR",
    "PHBTR",
    "PLTS_ATAP",
    "STASIUN_PENGISIAN_LISTRIK",
    "STLTM",
    "STLTR",
    "SWITCHING",
    "TIANG",
    "TRAFO",
)


def enabled_submission_schemas():
    try:
        values = st.secrets["SUBMISSION_SCHEMAS"]
    except Exception:
        values = ["semarang_5217"]
    return {str(value).strip() for value in values if SCHEMA_RE.fullmatch(str(value).strip())}


def assigned_schemas(role, schema):
    # Pilot submissions are limited independently of report viewing rights.
    enabled = enabled_submission_schemas()
    return [s for s in (x.strip() for x in schema.split(","))
            if SCHEMA_RE.fullmatch(s) and s in enabled]


def build_table_name(period, asset_type):
    period = str(period).strip()
    asset_type = str(asset_type).strip().upper()
    if not PERIOD_RE.fullmatch(period):
        raise ValueError("Bulan data harus memakai format YYYYMM, misalnya 202610.")
    if asset_type not in ASSET_TYPES:
        raise ValueError("Jenis tabel tidak tersedia pada daftar pengajuan.")
    return f"{period}_ADD_{asset_type}"


def submit_requests(engine, username, account, schema, tables, notes):
    allowed = assigned_schemas(account.get("role", ""), account.get("schema", ""))
    email = str(account.get("email", "")).strip().lower()
    tables = list(dict.fromkeys(str(table).strip().upper() for table in tables))
    if schema not in allowed or not tables:
        raise ValueError("Pilih UP3 dan minimal satu jenis tabel.")
    if not all(TABLE_RE.fullmatch(table) for table in tables):
        raise ValueError("Nama tabel pengajuan tidak sesuai.")
    if not EMAIL_RE.fullmatch(email):
        raise ValueError("Alamat email akun belum dikonfigurasi.")

    requests = []
    with engine.begin() as conn:
        for table in tables:
            request_id = str(uuid4())
            row = conn.execute(text("""
                INSERT INTO public.maghes_verification_requests
                  (id, schema_name, table_name, requested_by, requester_email, notes)
                VALUES (:id, :schema, :table, :username, :email, :notes)
                ON CONFLICT DO NOTHING RETURNING id
            """), {"id": request_id, "schema": schema, "table": table,
                    "username": username, "email": email,
                    "notes": notes.strip()[:500]}).scalar_one_or_none()
            if row is None:
                raise ValueError(
                    f"{table} masih mempunyai pengajuan aktif. "
                    "Tidak ada pilihan baru yang disimpan."
                )
            requests.append((request_id, table))
    return requests


def submit_request(engine, username, account, schema, table, expected_rows, notes):
    """Kompatibilitas pemanggil lama; pengajuan baru tidak meminta jumlah record."""
    return submit_requests(engine, username, account, schema, [table], notes)[0][0]


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
    rows_line = f"Perkiraan record: {rows}\n" if rows is not None else ""
    msg.set_content(
        f"Pengajuan: {request_id}\nUP3: {schema}\nTabel: {table}\n"
        f"Pengaju: {username}\n{rows_line}"
        f"Catatan: {notes[:500] or '-'}\n\n"
        "Buka antrean MAGHES internal untuk memeriksa data."
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
    st.caption(
        "Selesaikan upload di QGIS dahulu. Pilih bulan dan jenis data yang sudah "
        "selesai diunggah; tim UID akan memeriksanya melalui intranet."
    )
    allowed = assigned_schemas(role, schema)
    if not allowed:
        st.info("Akun ini belum memiliki penugasan UP3 untuk membuat pengajuan.")
        return
    if not EMAIL_RE.fullmatch(str(account.get("email", "")).strip()):
        st.warning("Email akun UP3 belum diatur. Hubungi pengelola MAGHES sebelum mengajukan.")
        return

    with st.form("maghes_request_form", clear_on_submit=True):
        selected_schema = st.selectbox("1. UP3", allowed)
        st.markdown("**2. Bulan Validasi**")
        today = datetime.now(ZoneInfo("Asia/Jakarta"))
        month_column, year_column = st.columns(2)
        with month_column:
            validation_month = st.selectbox(
                "Bulan", list(range(1, 13)), index=today.month - 1,
                format_func=lambda month: MONTH_NAMES[month - 1],
                key="submission_validation_month",
            )
        with year_column:
            validation_year = st.selectbox(
                "Tahun", list(range(today.year + 1, 1999, -1)), index=1,
                key="submission_validation_year",
            )
        period = f"{validation_year:04d}{validation_month:02d}"
        st.markdown("**3. Tabel yang selesai diunggah melalui QGIS**")
        st.caption("Centang satu atau beberapa jenis aset.")
        columns = st.columns(3)
        selected_assets = []
        for index, asset_type in enumerate(ASSET_TYPES):
            with columns[index % 3]:
                if st.checkbox(asset_type, key=f"request_asset_{asset_type}"):
                    selected_assets.append(asset_type)
        notes = st.text_area(
            "4. Catatan untuk Verifikator",
            placeholder=(
                "Contoh: Masih ada kekurangan; data tambahan akan diunggah menyusul."
            ),
            max_chars=500,
        )
        submitted = st.form_submit_button("📨 Ajukan Verifikasi", type="primary")

    if submitted:
        try:
            tables = [build_table_name(period, asset) for asset in selected_assets]
            requests = submit_requests(
                engine, username, account, selected_schema, tables, notes
            )
            sent = 0
            for request_id, table in requests:
                if notify_reviewer(
                    engine, request_id, selected_schema, table,
                    username, None, notes
                ):
                    sent += 1
            message = f"{len(requests)} pengajuan tersimpan dan masuk antrean UID."
            if sent == len(requests):
                message += " Semua email pemberitahuan terkirim."
            elif sent:
                message += f" Email terkirim: {sent} dari {len(requests)}."
            else:
                message += " Email belum terkirim; pengajuan tetap terlihat di antrean UID."
            st.success(message)
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Pengajuan belum tersimpan. Periksa koneksi atau hubungi pengelola.")

    try:
        history = list_requests(engine, username, account)
        if not history.empty:
            st.markdown("#### Status pengajuan saya")
            st.dataframe(
                history[["schema_name", "table_name", "status",
                         "requested_at", "updated_at"]],
                use_container_width=True,
                hide_index=True,
            )
            if _mail_config():
                pending = history[
                    history["request_notified_at"].isna()
                    & (history["status"] == "DIAJUKAN")
                ]
                if not pending.empty and st.button("Kirim ulang email pengajuan yang tertunda"):
                    sent = 0
                    for _, item in pending.iterrows():
                        if notify_reviewer(
                            engine, str(item["id"]), item["schema_name"],
                            item["table_name"], username, None, ""
                        ):
                            sent += 1
                    st.info(f"Email terkirim: {sent} dari {len(pending)} pengajuan.")
    except Exception:
        st.info(
            "Riwayat pengajuan belum tersedia; "
            "minta pengelola menjalankan migrasi tabel pengajuan."
        )

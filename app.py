"""
MAGHES Viewer — Public QA/QC Dashboard
=======================================
Kloningan tampilan MAGHES Internal, namun sumber datanya dari Supabase (internet publik).
Admin UP3 bisa login dengan akun mereka tanpa VPN.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import base64, os, math

# ==========================================
# PATHS & ASSETS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "image", "LOGO_MAGIS.png")
LOGO_PLN_PATH = os.path.join(BASE_DIR, "image", "LOGO_PLN.png")
BG_PATH = os.path.join(BASE_DIR, "image", "BACKGROUND_MAGIS_FIX.png")
BG_VALIDATOR_PATH = os.path.join(BASE_DIR, "image", "BACKGROUND_VALIDATOR.png")

def load_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

LOGO_B64 = load_b64(LOGO_PATH)
LOGO_PLN_B64 = load_b64(LOGO_PLN_PATH)
BG_B64 = load_b64(BG_PATH)
BG_VALIDATOR_B64 = load_b64(BG_VALIDATOR_PATH)

# ==========================================
# USER DATABASE (sama persis dengan MAGHES internal)
# ==========================================
USERS_DB = {
    "rega.syahrul": {"pass": "aheadfinelattedoubleshoot", "role": "admin", "schema": "master_jateng"},
    "user_semarang": {"pass": "smg_dist2026", "role": "viewer", "schema": "semarang_5217"},
    "user_purwokerto": {"pass": "pwt_dist2026", "role": "viewer", "schema": "purwokerto_5215"},
    "user_cilacap": {"pass": "clp_dist2026", "role": "viewer", "schema": "cilacap_5221"},
    "user_sukoharjo": {"pass": "skh_dist2026", "role": "viewer", "schema": "sukoharjo_5223"},
}

# ==========================================
# PAGE CONFIG
# ==========================================
from PIL import Image
try:
    favicon = Image.open(LOGO_PATH)
except:
    favicon = "⚡"

st.set_page_config(
    page_title="MAGHES Viewer — PLN UID Jateng",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False, "username": "", "role": "", "schema": "",
    })

# ==========================================
# SUPABASE ENGINE
# ==========================================
DEFAULT_DB_URL = "postgresql://postgres.jhwdbhhkmonxvuzoiheo:gisjateng2026@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

@st.cache_resource
def get_public_engine():
    try:
        db_url = st.secrets.get("DATABASE_URL", DEFAULT_DB_URL)
    except Exception:
        db_url = DEFAULT_DB_URL
        
    if not db_url or "PASSWORD" in db_url:
        db_url = DEFAULT_DB_URL
        
    # BARIS YANG DIUBAH (tambah +psycopg2)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
    return create_engine(db_url)


# ==========================================
# CSS THEME (Identik dengan MAGHES Internal)
# ==========================================
def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root {{
    --pln-blue: #0057A8; --pln-blue-light: #0073D1; --pln-blue-glow: rgba(0, 87, 168, 0.3);
    --pln-green: #7CC242; --pln-green-light: #96D35F; --pln-green-glow: rgba(124, 194, 66, 0.3);
    --bg-base: #041C2C; --bg-surface: #0A2A3C; --bg-card: #0E3349;
    --border-subtle: rgba(0, 87, 168, 0.15); --border-glow: rgba(0, 87, 168, 0.35);
    --text-primary: #EDF5FC; --text-secondary: #A3C4DC; --text-muted: #6B93AD;
    --success: #7CC242; --danger: #E74C3C; --warning: #F5A623;
}}
* {{ font-family: 'Inter', sans-serif; }}
.stApp {{
    background-image: none !important;
    background-color: var(--bg-base) !important;
    color: var(--text-primary);
}}
[data-testid="stAppViewContainer"] {{ background-color: var(--bg-base) !important; }}
[data-testid="stHeader"] {{
    background: rgba(4, 28, 44, 0.85) !important;
    backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid var(--border-glow);
}}
[data-testid="stHeader"]::before {{
    content: "PENGELOLAAN ASET DISTRIBUSI JAWA TENGAH";
    display: flex; align-items: center; color: var(--text-primary);
    font-size: 1.35rem; font-weight: 800; white-space: nowrap; padding-left: 65px; height: 100%; width: 100%;
    background-image: url("data:image/png;base64,{LOGO_PLN_B64}");
    background-size: 35px; background-repeat: no-repeat; background-position: 15px center; letter-spacing: 0.5px;
}}
[data-testid="stHeader"] button {{ color: var(--text-secondary) !important; z-index: 9999 !important; position: relative !important; }}
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(4, 28, 44, 0.90) 0%, rgba(10, 42, 60, 0.90) 100%) !important;
    backdrop-filter: blur(15px) !important; -webkit-backdrop-filter: blur(15px) !important;
    border-right: 1px solid var(--border-glow);
}}
footer {{ visibility: hidden; }}
[data-testid="manage-app-button"],
.stAppDeployButton,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {{
    display: none !important;
}}
[data-testid="stSidebarContent"] {{ display: flex; flex-direction: column; }}
[data-testid="stSidebarUserContent"] {{ order: 1; padding-top: 2rem; }}
[data-testid="stSidebarNav"] {{ order: 2; }}

.sidebar-user-card {{
    background: linear-gradient(135deg, rgba(0,87,168,0.15), rgba(124,194,66,0.1));
    border: 1px solid var(--border-glow); border-radius: 14px; padding: 1rem; text-align: center; margin-bottom: 1rem;
}}
.sidebar-username {{ font-weight: 700; font-size: 0.95rem; color: var(--text-primary); }}
.sidebar-role {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 0.2rem; color: var(--pln-green); }}
.sidebar-divider {{ height: 1px; background: linear-gradient(90deg, transparent, var(--border-glow), transparent); margin: 1rem 0; }}

.stat-box {{
    flex: 1; min-width: 180px; background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 14px; padding: 1.2rem; text-align: center;
}}
.stat-box .s-num {{ font-size: 2.2rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }}
.stat-box .s-num.blue {{ color: var(--pln-blue-light); }} .stat-box .s-num.green {{ color: var(--pln-green); }}
.stat-box .s-num.red {{ color: var(--danger); }}
.stat-box .s-txt {{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-top: 0.2rem; }}

.score-item {{
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 12px; padding: 1rem 0.8rem; text-align: center;
    border-left: 3px solid var(--pln-green); transition: all 0.3s ease;
}}
.score-item:hover {{ transform: translateY(-2px); border-color: var(--border-glow); }}
.score-item.has-error {{ border-left-color: var(--danger); }}
.s-value.pass {{ color: var(--pln-green); font-weight: bold; font-size: 1.5rem; }}
.s-value.fail {{ color: var(--danger); font-weight: bold; font-size: 1.5rem; }}

.stTabs [data-baseweb="tab-list"] {{
    gap: 4px; background: var(--bg-surface); border-radius: 14px; padding: 5px; border: 1px solid var(--border-subtle);
}}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px; font-weight: 600; font-size: 0.82rem; }}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, var(--pln-blue), #00573F) !important; color: white !important;
}}

[data-testid="stAlert"] {{
    background: rgba(4, 28, 44, 0.85) !important; backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border-glow) !important; color: var(--text-primary) !important;
}}
.header-bar {{
    background: linear-gradient(135deg, rgba(4, 28, 44, 0.85), rgba(10, 42, 60, 0.95));
    backdrop-filter: blur(12px); border: 1px solid var(--border-glow); border-radius: 16px;
    padding: 1.2rem 1.5rem; margin-bottom: 1.5rem;
}}
.header-bar h1 {{ font-size: 1.4rem; font-weight: 800; margin: 0; color: var(--text-primary); }}
.header-bar p {{ font-size: 0.75rem; margin: 0.2rem 0 0; color: var(--text-muted); }}
.header-logo {{ height: 45px; margin-right: 1rem; vertical-align: middle; }}

.app-footer {{
    text-align: center; padding: 1rem; color: var(--text-muted); font-size: 0.72rem;
    border: 1px solid var(--border-subtle); margin-top: 3rem;
    background: rgba(4, 28, 44, 0.85); backdrop-filter: blur(10px); border-radius: 12px;
}}
.app-footer span {{ color: var(--pln-blue-light); font-weight: 600; }}
.footer-logo {{ height: 28px; vertical-align: middle; margin-right: 8px; opacity: 0.7; }}
</style>
""", unsafe_allow_html=True)


def render_footer(page="home"):
    footer_logo = f'<img class="footer-logo" src="data:image/png;base64,{LOGO_PLN_B64}">' if LOGO_PLN_B64 else ''
    is_logged_in = st.session_state.get("logged_in", False)
    
    if not is_logged_in or page == "login":
        text_content = '<span>PLN UID Jawa Tengah</span> &middot; <span>MAGHES Enterprise Platform</span> &middot; &copy; 2026'
    else:
        text_content = '<span>Modul MAGHES Validator</span> &mdash; Developed by <span>Rega Syahrul</span> | &middot; &copy; 2026'
        
    st.markdown(f"""
<div class="app-footer">
    {footer_logo} {text_content}
</div>
""", unsafe_allow_html=True)


def render_card(title, score):
    if score is None: score = 0
    color = "var(--success)" if score >= 95 else "var(--warning)" if score >= 75 else "var(--danger)"
    display_score = "99.9" if 99.9 < score < 100 else f"{score:.1f}"
    return f"""
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px;
        padding: 1.2rem; text-align: center; border-top: 3px solid {color};">
        <p style="margin:0; font-size:0.85rem; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">{title}</p>
        <h1 style="color:{color}; font-size:2.5rem; margin:10px 0; font-family:'JetBrains Mono',monospace; font-weight:800;">{display_score}%</h1>
    </div>
    """


# ══════════════════════════════════════
# HALAMAN LOGIN (Belum Login)
# ══════════════════════════════════════
if not st.session_state["logged_in"]:
    if BG_B64:
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{BG_B64}");
            background-size: cover; background-position: center top;
            background-repeat: no-repeat; background-attachment: fixed;
            height: 100vh !important; overflow: hidden !important;
        }}
        .block-container {{ max-width: 100% !important; padding: 0 !important; margin: 0 !important; }}
        [data-testid="stHeader"] {{ background: transparent !important; display: none !important; }}
        footer {{visibility: hidden;}}
        [data-testid="manage-app-button"],
        .stAppDeployButton,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            display: none !important;
        }}
        [data-testid="stSidebar"] {{ display: none !important; }}

        .magis-hud-container {{
            position: absolute;
            top: 5vh;
            left: 0;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 50;
        }}
        .magis-logo {{ 
            height: 50px; 
            margin-right: 15px; 
            position: relative;
            top: -80px;
            left: 90px;
        }}
        .magis-text-box {{ text-align: left; }}
        .magis-title {{
            font-size: 2.5rem; 
            font-weight: 900;
            color: #7CC242; 
            text-shadow: 0 0 15px rgba(124, 194, 66, 0.8);
            margin: 0; padding: 0; line-height: 1.1;
            position: relative;
            top: -70px; left: 110px;
        }}
        .magis-subtitle {{
            font-size: 0.85rem;
            color: #A3C4DC;
            letter-spacing: 1px;
            font-weight: 250;
            margin: 0; margin-top: 2px;
            position: relative;
            top: -90px; left: -25px;
        }}

        [data-testid="stForm"] {{
            background: rgba(4, 28, 44, 0.4) !important;
            backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(124, 194, 66, 0.3) !important;
            border-radius: 28px !important; padding: 1.8rem !important;
            box-shadow: 0 0 40px rgba(0, 87, 168, 0.6) !important;
        }}
        @keyframes petirBlink {{
            0%, 100% {{ box-shadow: 0 0 5px rgba(255, 140, 0, 0.3); border-color: rgba(255, 140, 0, 0.5); color: #FFFFFF; }}
            10%, 12%, 14% {{ box-shadow: 0 0 20px rgba(255, 165, 0, 1), 0 0 40px rgba(255, 69, 0, 0.8) inset; border-color: #FF8C00; color: #FFD700; text-shadow: 0 0 10px #FF8C00; }}
            11%, 13% {{ box-shadow: none; border-color: rgba(255, 140, 0, 0.3); }}
            50% {{ box-shadow: 0 0 15px rgba(255, 140, 0, 0.6); border-color: rgba(255, 165, 0, 0.8); }}
        }}
        [data-testid="stForm"] button {{
            animation: petirBlink 3s infinite; transition: all 0.2s ease-in-out; font-weight: 700;
        }}
        [data-testid="stForm"] button:hover {{ transform: scale(1.05); box-shadow: 0 0 30px rgba(255, 165, 0, 0.9) !important; }}

        .app-footer {{
            position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); width: 100%;
            border: none; margin: 0; padding: 0; z-index: 999; text-align: center; color: #A3C4DC; font-size: 0.75rem;
        }}
        .app-footer span {{ color: #7CC242; font-weight: 600; }}
        .footer-logo {{ height: 28px; vertical-align: middle; margin-right: 8px; opacity: 0.7; }}
        </style>
        """, unsafe_allow_html=True)

    logo_html = f'<img class="magis-logo" src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""
    <div class="magis-hud-container">
        {logo_html}
        <div class="magis-text-box">
            <h1 class="magis-title">MAGHES</h1>
            <p class="magis-subtitle">Management Asset & Geospatial Holistic Electrical System</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 32vh;'></div>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1.5, 1, 1.5])
    with col_c:
        with st.form("login_form"):
            input_user = st.text_input("Username Database").strip()
            input_pass = st.text_input("Password", type="password")
            submit = st.form_submit_button("⚡ Hubungkan ke Server ⚡", use_container_width=True)
            if submit:
                if input_user in USERS_DB and input_pass == USERS_DB[input_user]["pass"]:
                    engine = get_public_engine()
                    if engine:
                        st.session_state.update({
                            "logged_in": True, "username": input_user,
                            "role": USERS_DB[input_user]["role"],
                            "schema": USERS_DB[input_user]["schema"],
                        })
                        st.rerun()
                    else:
                        st.error("Database Publik belum dikonfigurasi.")
                else:
                    st.error("Username atau Password ditolak!")

    render_footer("login")

# ══════════════════════════════════════
# DASHBOARD UTAMA (Sudah Login)
# ══════════════════════════════════════
else:
    inject_css()

    db_user = st.session_state["username"]
    current_role = st.session_state["role"]
    user_schema = st.session_state["schema"]
    engine = get_public_engine()

    # ── Sidebar ──
    with st.sidebar:
        logo_sidebar = f'<img style="width: 80%; display: block; margin: 0 auto 20px auto;" src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
        st.markdown(f"""
        <div class="sidebar-user-card">
            {logo_sidebar}
            <div class="sidebar-username">{db_user.upper()}</div>
            <div class="sidebar-role">{'TIM EXPERTISE GIS' if current_role == 'admin' else current_role.upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Putuskan Koneksi", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        if current_role == "admin":
            st.info("Mode Admin: Anda dapat melihat seluruh data UP3.")
        else:
            schemas_list = [s.strip() for s in user_schema.split(',')]
            if len(schemas_list) > 1:
                st.info(f"🔒 Terkunci di {len(schemas_list)} UP3:\n\n" + "\n".join([f"- **{s}**" for s in schemas_list]))
            else:
                st.info(f"🔒 Terkunci di Schema: **{user_schema}**")

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # Load list of published verifications
        try:
            if current_role == "admin":
                df_verif = pd.read_sql("SELECT DISTINCT ON (schema_name, tabel_sumber) * FROM public.tbl_published_verifications ORDER BY schema_name, tabel_sumber, published_at DESC", engine)
            else:
                schemas_list = [s.strip() for s in user_schema.split(',')]
                if len(schemas_list) > 1:
                    conditions = " OR ".join([f"schema_name LIKE :schema_{i}" for i in range(len(schemas_list))])
                    params = {f"schema_{i}": f"%{s}%" for i, s in enumerate(schemas_list)}
                    q = text(f"SELECT DISTINCT ON (schema_name, tabel_sumber) * FROM public.tbl_published_verifications WHERE {conditions} ORDER BY schema_name, tabel_sumber, published_at DESC")
                    df_verif = pd.read_sql(q, engine, params=params)
                else:
                    df_verif = pd.read_sql(text("SELECT DISTINCT ON (schema_name, tabel_sumber) * FROM public.tbl_published_verifications WHERE schema_name LIKE :schema ORDER BY schema_name, tabel_sumber, published_at DESC"), engine, params={"schema": f"%{user_schema}%"})
            # Sort again by published_at DESC for display
            df_verif = df_verif.sort_values(by="published_at", ascending=False).reset_index(drop=True)
        except Exception:
            df_verif = pd.DataFrame()

        if df_verif.empty:
            st.warning("Belum ada data verifikasi yang di-publish.")
            selected_verif_id = None
        else:
            st.markdown("##### 📋 Pilih Hasil Verifikasi")
            options = df_verif['id'].tolist()
            format_map = {row['id']: f"{row['schema_name']}.{row['tabel_sumber']} ({row['layer_type']})" for _, row in df_verif.iterrows()}
            selected_verif_id = st.selectbox(
                "Tabel Target:",
                options,
                format_func=lambda x: format_map.get(x, str(x)),
                label_visibility="collapsed"
            )

        # Globe animation (same as main MAGHES)
        st.markdown("""
        <style>
        .wireframe-globe { width: 130px; height: 130px; position: relative; margin: 40px auto 30px; transform-style: preserve-3d; animation: spinWireframe 8s linear infinite; }
        .wireframe-globe .circle { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 1.5px solid #7CC242; border-radius: 50%; box-shadow: 0 0 8px rgba(124, 194, 66, 0.4), inset 0 0 8px rgba(124, 194, 66, 0.4); }
        .wireframe-globe .circle:nth-child(1) { transform: rotateY(0deg); } .wireframe-globe .circle:nth-child(2) { transform: rotateY(36deg); }
        .wireframe-globe .circle:nth-child(3) { transform: rotateY(72deg); } .wireframe-globe .circle:nth-child(4) { transform: rotateY(108deg); }
        .wireframe-globe .circle:nth-child(5) { transform: rotateY(144deg); }
        .wireframe-globe .circle-h1 { transform: rotateX(90deg); } .wireframe-globe .circle-h2 { transform: rotateX(90deg) translateZ(30px) scale(0.85); }
        .wireframe-globe .circle-h3 { transform: rotateX(90deg) translateZ(-30px) scale(0.85); }
        @keyframes spinWireframe { 0% { transform: rotateY(0deg) rotateX(15deg) rotateZ(5deg); } 100% { transform: rotateY(360deg) rotateX(15deg) rotateZ(5deg); } }
        </style>
        <div class="wireframe-globe">
          <div class="circle"></div><div class="circle"></div><div class="circle"></div><div class="circle"></div><div class="circle"></div>
          <div class="circle circle-h1"></div><div class="circle circle-h2"></div><div class="circle circle-h3"></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Header Bar ──
    header_logo = f'<img class="header-logo" src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""
    <div class="header-bar">
        <div style="display: flex; align-items: center;">
            {header_logo}
            <div>
                <h1>MAGHES: Dashboard Hasil Verifikasi</h1>
                <p>Mode: Public Viewer (Internet) | User: <b style="color:#7CC242;">{db_user.upper()}</b> | Schema: {user_schema}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not engine:
        st.error("Database publik belum dikonfigurasi.")
        st.stop()

    if selected_verif_id is None:
        st.info("📌 Pilih hasil verifikasi dari sidebar untuk melihat detailnya.")
        render_footer()
        st.stop()

    # ── Get Record ──
    record = df_verif[df_verif['id'] == selected_verif_id].iloc[0]

    st.success("✅ Verifikasi berhasil dijalankan! Hasil telah disimpan ke database log.")
    st.markdown(f"**Target:** `{record['schema_name']}.{record['tabel_sumber']}` | **Tipe:** **{record['layer_type'].upper()}**")
    
    st.info(f"📊 **Rekapitulasi Layer:** Total Record diverifikasi: **{record['total_record']}** | Terakhir Publish: **{record['published_at']}**")

    # ── Tabs ──
    tab_rekap, tab_struktur, tab_atribut, tab_spasial, tab_error = st.tabs([
        "📈 Rekapitulasi Aset", 
        "📐 Struktur Kolom", 
        "📊 Kualitas Atribut", 
        "🌐 Spasial & Duplikat", 
        "📋 Error Log Terpadu"
    ])

    with tab_rekap:
        if pd.isna(record.get('hasil_rekapitulasi')) or not record['hasil_rekapitulasi']:
            st.info("🔒 **Fitur Terkunci / Data Kosong:** Detail rekapitulasi aset belum disinkronisasi ke web publik. Silakan lakukan verifikasi ulang di aplikasi utama.")
        else:
            try:
                import json
                rekap_data = json.loads(record['hasil_rekapitulasi'])
                
                keys = list(rekap_data.keys())
                if len(keys) == 1:
                    k = keys[0]
                    st.markdown(f"#### 📊 Berdasarkan {k}")
                    df_k = pd.DataFrame(rekap_data[k])
                    if not df_k.empty:
                        first_num_col = next((c for c in df_k.columns if c != df_k.columns[0]), None)
                        if first_num_col:
                            st.bar_chart(df_k.set_index(df_k.columns[0])[first_num_col])
                        st.dataframe(df_k, use_container_width=True, hide_index=True)
                elif len(keys) >= 2:
                    col1, col2 = st.columns(2)
                    for idx, k in enumerate(keys[:2]):
                        target_col = col1 if idx == 0 else col2
                        with target_col:
                            st.markdown(f"#### 📊 Berdasarkan {k}")
                            df_k = pd.DataFrame(rekap_data[k])
                            if not df_k.empty:
                                first_num_col = next((c for c in df_k.columns if c != df_k.columns[0]), None)
                                if first_num_col:
                                    st.bar_chart(df_k.set_index(df_k.columns[0])[first_num_col])
                                st.dataframe(df_k, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Gagal memuat rekapitulasi: {e}")
    
    with tab_struktur:
        st.markdown("### 📐 Perbandingan Struktur")
        if pd.isna(record.get('hasil_struktur')) or not record['hasil_struktur']:
            st.warning("Data struktur kolom tidak tersedia. Harap lakukan verifikasi ulang di aplikasi utama agar data sinkron ke Supabase.")
        else:
            try:
                import json
                struk_data = json.loads(record['hasil_struktur'])
                df_cols = pd.DataFrame(struk_data)
                
                issues = df_cols[df_cols["status"] != "OK"] if "status" in df_cols.columns else pd.DataFrame()
                ok_count = len(df_cols) - len(issues)
                
                st.markdown(f"""
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <div class="stat-box"><div class="s-num blue">{len(df_cols)}</div><div class="s-txt">Total Kolom</div></div>
                    <div class="stat-box"><div class="s-num green">{ok_count}</div><div class="s-txt">✅ Match</div></div>
                    <div class="stat-box"><div class="s-num red">{len(issues)}</div><div class="s-txt">❌ Bermasalah</div></div>
                </div>""", unsafe_allow_html=True)
                
                if not issues.empty:
                    st.error(f"Ditemukan **{len(issues)}** kolom bermasalah:")
                    st.dataframe(issues, use_container_width=True, hide_index=True)
                
                with st.expander("🔍 Lihat Seluruh Kolom"):
                    st.dataframe(df_cols, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Gagal memuat data struktur: {str(e)}")

    # ── Scorecards ──
    with tab_atribut:
        st.markdown(render_card("Validitas Atribut", record['score_attr']), unsafe_allow_html=True)
        st.markdown("---")
        try:
            df_attr = pd.read_sql(text("SELECT * FROM public.tbl_qa_error_log_public WHERE verification_id = :vid AND jenis_error = 'ATRIBUT'"), engine, params={"vid": selected_verif_id})
        except:
            df_attr = pd.DataFrame()

        if df_attr.empty:
            st.success("🎉 Tidak ada error atribut. Data 100% valid!")
        else:
            st.warning(f"Ditemukan **{len(df_attr)}** error atribut.")
            summary = df_attr['rule_dilanggar'].value_counts()
            for rule, count in summary.items():
                with st.expander(f"❌ {rule} — {count} error"):
                    st.dataframe(df_attr[df_attr['rule_dilanggar'] == rule][['objectid', 'rule_dilanggar', 'detail_error']], use_container_width=True, hide_index=True)

    with tab_spasial:
        st.markdown(render_card("Validitas Spasial", record['score_spas']), unsafe_allow_html=True)
        st.markdown("---")
        try:
            df_spas = pd.read_sql(text("SELECT * FROM public.tbl_qa_error_log_public WHERE verification_id = :vid AND jenis_error != 'ATRIBUT'"), engine, params={"vid": selected_verif_id})
        except:
            df_spas = pd.DataFrame()

        if df_spas.empty:
            st.success("🎉 Tidak ada error spasial. Data 100% valid!")
        else:
            st.warning(f"Ditemukan **{len(df_spas)}** error spasial.")
            summary = df_spas['rule_dilanggar'].value_counts()
            for rule, count in summary.items():
                with st.expander(f"❌ {rule} — {count} error"):
                    st.dataframe(df_spas[df_spas['rule_dilanggar'] == rule][['objectid', 'rule_dilanggar', 'detail_error']], use_container_width=True, hide_index=True)

    with tab_error:
        st.markdown(render_card("Kesehatan Data Keseluruhan", record['score_overall']), unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 📋 Unified Error Log")
        try:
            df_all = pd.read_sql(text("SELECT * FROM public.tbl_qa_error_log_public WHERE verification_id = :vid"), engine, params={"vid": selected_verif_id})
        except:
            df_all = pd.DataFrame()

        if df_all.empty:
            st.success("🎉 Tidak ada error QA/QC yang terekam. Data bersih!")
        else:
            st.warning(f"Ditemukan **{len(df_all)}** total log error.")
            st.dataframe(df_all[['objectid', 'jenis_error', 'rule_dilanggar', 'detail_error']], use_container_width=True, hide_index=True)

            # Download CSV
            csv_data = df_all.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV (Excel)",
                data=csv_data,
                file_name=f"error_log_{record['tabel_sumber']}.csv",
                mime="text/csv",
                use_container_width=True
            )

    render_footer("validator")

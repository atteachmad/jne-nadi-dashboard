import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. KONFIGURASI HALAMAN DASAR
# ==========================================
st.set_page_config(page_title="NADI - JNE Agent Monitoring", page_icon="📦", layout="wide")

# ==========================================
# 2. SISTEM LOGIN SEDERHANA
# ==========================================
def check_password():
    """Mengembalikan True jika password benar."""
    def password_entered():
        if (st.session_state["username"] == st.secrets["credentials"]["username"] and 
            st.session_state["password"] == st.secrets["credentials"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari memory
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Form Login
        st.markdown("<h1 style='text-align: center;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>JNE Agent Rating & Sentiment Analysis</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered, use_container_width=True)
        return False
    
    elif not st.session_state["password_correct"]:
        # Jika salah password
        st.markdown("<h1 style='text-align: center;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered, use_container_width=True)
            st.error("😕 Username atau password salah")
        return False
    
    else:
        # Jika Benar
        return True

# ==========================================
# 3. TAMPILAN DASHBOARD (Hanya muncul jika login)
# ==========================================
if check_password():
    st.title("📊 NADI: JNE Agent Sentiment & Rating Dashboard")
    st.markdown("Selamat datang, Analyst. Berikut adalah performa agen terkini dari Google Sheets.")
    
    try:
        # Menarik data dari Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m") # Cek data baru setiap 1 menit
        
        # Membersihkan baris yang kosong (jika ada baris kosong di Google Sheets)
        df = df.dropna(how="all")

        # Membuat Layout Modern (Angka Rangkuman)
        col1, col2, col3 = st.columns(3)
        col1.metric(label="Total Agen Dipantau", value=len(df))
        col2.metric(label="Rata-rata Rating", value=round(df["Rating"].mean(), 2))
        col3.metric(label="Total Paket (Sampel)", value=int(df["Total Paket"].sum()))

        st.divider()

        # Visualisasi Grafik
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Rating per Agen")
            fig_bar = px.bar(df, x="Nama Agen", y="Rating", color="Sentimen", text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart2:
            st.subheader("Distribusi Sentimen")
            fig_pie = px.pie(df, names="Sentimen", values="Total Paket", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("Detail Data Terkini")
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        # Menampilkan pesan error jika terjadi masalah koneksi atau salah nama kolom
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan URL dan nama kolom benar. Detail error: {e}")

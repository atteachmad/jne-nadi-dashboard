import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import re
from collections import Counter

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
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>JNE Agent Rating & Sentiment Analysis</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered, use_container_width=True)
        return False
    
    elif not st.session_state["password_correct"]:
        st.markdown("<h1 style='text-align: center;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered, use_container_width=True)
            st.error("😕 Username atau password salah")
        return False
    
    else:
        return True

# ==========================================
# 3. FUNGSI BANTUAN (LOGIC & ANALISIS TEKS)
# ==========================================
def tentukan_sentimen(rating):
    """Mengubah angka rating ulasan menjadi kategori sentimen."""
    try:
        r = float(rating)
        if r >= 4: return "Positif"
        elif r >= 3: return "Netral"
        else: return "Negatif"
    except:
        return "Tidak Diketahui"

# Daftar kata yang diabaikan agar tidak masuk ke grafik (Stopwords)
KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", 
                "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", 
                "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", 
                "aja", "banget", "sih", "kok", "sama", "buat"}

def ekstrak_kata_penting(teks):
    """Membersihkan tanda baca dan mengambil kata-kata penting."""
    if pd.isna(teks): return []
    # Ubah ke huruf kecil
    teks = str(teks).lower()
    # Hapus semua tanda baca dan angka (sisakan huruf saja)
    teks = re.sub(r'[^a-z\s]', '', teks)
    # Pecah jadi perkata dan buang kata yang ada di daftar KATA_ABAIKAN
    kata_kata = teks.split()
    return [k for k in kata_kata if k not in KATA_ABAIKAN and len(k) > 2]

# ==========================================
# 4. TAMPILAN DASHBOARD UTAMA
# ==========================================
if check_password():
    st.title("📊 NADI: JNE Agent Sentiment & Rating Dashboard")
    st.markdown("Pemantauan Performa Agen, Pemetaan Wilayah, dan Analisis Sentimen Pelanggan.")
    
    try:
        # Menarik data dari Google Sheets (Otomatis update tiap 1 menit jika ada perubahan)
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="1m")
        df = df.dropna(how="all")

        # Memastikan format angka terbaca dengan benar
        df["Rating_Rata_Rata"] = pd.to_numeric(df["Rating_Rata_Rata"], errors="coerce")
        df["Rating_Ulasan_Orang"] = pd.to_numeric(df["Rating_Ulasan_Orang"], errors="coerce")
        
        # Eksekusi Logika
        df["Sentimen"] = df["Rating_Ulasan_Orang"].apply(tentukan_sentimen)

        # ----------------------------------------
        # A. METRIK UTAMA
        # ----------------------------------------
        col1, col2, col3 = st.columns(3)
        total_agen = df["Nama_Agen"].nunique()
        rata_rating = df["Rating_Ulasan_Orang"].mean()
        
        col1.metric(label="Total Agen Terdaftar", value=total_agen)
        col2.metric(label="Rata-rata Rating Ulasan", value=f"{rata_rating:.2f}" if pd.notna(rata_rating) else "0.00")
        col3.metric(label="Total Ulasan Masuk", value=len(df))

        st.divider()

        # ----------------------------------------
        # B. PETA SEBARAN AGEN (INTERAKTIF)
        # ----------------------------------------
        st.subheader("🗺️ Peta Pemantauan Lokasi Agen")
        st.markdown("Titik warna menunjukkan Rating Rata-rata Agen. Dekatkan kursor ke titik untuk melihat nama agen.")
        
        # Filter data yang hanya memiliki Latitude dan Longitude valid
        df_map = df.copy()
        df_map["Latitude"] = pd.to_numeric(df_map["Latitude"], errors="coerce")
        df_map["Longitude"] = pd.to_numeric(df_map["Longitude"], errors="coerce")
        df_map_bersih = df_map.dropna(subset=["Latitude", "Longitude", "Nama_Agen"])
        
        if not df_map_bersih.empty:
            fig_map = px.scatter_mapbox(
                df_map_bersih, 
                lat="Latitude", 
                lon="Longitude", 
                hover_name="Nama_Agen", 
                hover_data={"Alamat": True, "Rating_Rata_Rata": True, "Latitude": False, "Longitude": False},
                color="Rating_Rata_Rata",
                color_continuous_scale=px.colors.diverging.RdYlGn, # Merah (jelek) ke Hijau (bagus)
                size_max=15, 
                zoom=11, 
                mapbox_style="open-street-map"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Menunggu data Latitude dan Longitude yang valid dari Google Sheets untuk menampilkan peta.")

        st.divider()

        # ----------------------------------------
        # C. ANALISIS SENTIMEN & KATA NEGATIF
        # ----------------------------------------
        col_chart1, col_chart2 = st.columns([1, 1.5])
        
        with col_chart1:
            st.subheader("Proporsi Sentimen")
            fig_pie = px.pie(df, names="Sentimen", hole=0.4, 
                             color="Sentimen", 
                             color_discrete_map={"Positif": "#2ca02c", "Netral": "#ff7f0e", "Negatif": "#d62728"})
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_chart2:
            st.subheader("⚠️ Top Keluhan (Kata Paling Sering Muncul)")
            st.markdown("Dianalisis secara otomatis dari **Teks_Ulasan** bersentimen **Negatif**.")
            
            # Ambil hanya ulasan negatif
            df_negatif = df[df["Sentimen"] == "Negatif"]
            semua_kata_negatif = []
            
            # Kumpulkan semua kata dari ulasan negatif
            for ulasan in df_negatif["Teks_Ulasan"]:
                semua_kata_negatif.extend(ekstrak_kata_penting(ulasan))
            
            # Hitung frekuensi kata
            if semua_kata_negatif:
                top_10_kata = Counter(semua_kata_negatif).most_common(10)
                df_kata = pd.DataFrame(top_10_kata, columns=["Kata Keluhan", "Jumlah Disebut"])
                
                # Buat grafik bar horizontal
                fig_bar_kata = px.bar(df_kata, x="Jumlah Disebut", y="Kata Keluhan", 
                                      orientation='h', color_discrete_sequence=["#d62728"])
                fig_bar_kata.update_layout(yaxis={'categoryorder':'total ascending'}) # Urutkan dari terbanyak di atas
                st.plotly_chart(fig_bar_kata, use_container_width=True)
            else:
                st.success("Luar biasa! Belum ada ulasan negatif yang masuk untuk dianalisis.")

        st.divider()

        # ----------------------------------------
        # D. TABEL DATA MENTAH
        # ----------------------------------------
        st.subheader("📋 Detail Data Mentah Ulasan")
        st.dataframe(df[["Nama_Agen", "Alamat", "Rating_Ulasan_Orang", "Sentimen", "Teks_Ulasan"]], use_container_width=True)
        
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan format kolom sama persis. Detail error: {e}")

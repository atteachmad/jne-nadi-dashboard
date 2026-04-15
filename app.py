import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import re
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

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
# 3. KONFIGURASI HALAMAN DASAR (16:9 1366x768)
# ==========================================
st.set_page_config(page_title="NADI - JNE Agent Monitoring", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 4. CUSTOM CSS UNTUK TAMPILAN "POWER BI"
# ==========================================
st.markdown("""
<style>
    /* Latar belakang abu-abu terang ala Power BI */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* Efek Card putih dengan shadow untuk setiap visual */
    .css-1r6slb0, .css-12oz5g7 {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    
    /* Header Container */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: white;
        padding: 10px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Metrik besar */
    .big-metric {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        color: #333;
    }
    .metric-label {
        font-size: 18px;
        text-align: center;
        font-weight: bold;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 5. SISTEM LOGIN SEDERHANA
# ==========================================
def check_password():
    # Gunakan logika login Anda di sini (saya asumsikan selalu True untuk testing tampilan)
    # Jika menggunakan st.secrets, pastikan file konfigurasi sudah benar.
    return True 

# ==========================================
# 6. FUNGSI BANTUAN (LOGIC & ANALISIS TEKS)
# ==========================================
KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", 
                "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", 
                "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", 
                "aja", "banget", "sih", "kok", "sama", "buat"}

def ekstrak_kata_penting(teks):
    if pd.isna(teks): return []
    teks = str(teks).lower()
    teks = re.sub(r'[^a-z\s]', '', teks)
    return [k for k in teks.split() if k not in KATA_ABAIKAN and len(k) > 2]

# ==========================================
# 7. DASHBOARD UTAMA (LAYOUT POWER BI)
# ==========================================
if check_password():
    
    # -- HEADER --
    col_logo, col_title, col_filter, col_btn = st.columns([1, 4, 2, 1])
    with col_logo:
        st.image("https://upload.wikimedia.org/wikipedia/commons/9/92/Logo_JNE.png", width=100) # Ganti dengan path logo lokal jika ada
    with col_title:
        st.markdown("<h3 style='margin:0; padding-top:10px;'>JNE Bandung : Analisa Kualitas Layanan & Sentimen</h3>", unsafe_allow_html=True)
    with col_filter:
        global_filter = st.selectbox("Wilayah/Semua", ["Semua", "Bandung Kota", "Kabupaten Bandung", "Cimahi"], label_visibility="collapsed")
    with col_btn:
        st.button("CEK MAPS", use_container_width=True)

    # -- AMBIL DATA --
    try:
        # Dummy Connection Check (Ganti dengan koneksi GSheets Anda)
        # conn = st.connection("gsheets", type=GSheetsConnection)
        # df_raw = conn.read(ttl="1m").dropna(how="all")
        
        # Simulasi Data agar script berjalan saat diuji
        df = pd.DataFrame({
            "Nama_Agen": ["AGEN MARANATHA", "JNE Cabang Rancaekek", "AGEN TERUSAN PASIR KOJA", "Agen JNE Express Cinambo"],
            "Kategori": ["AGEN", "Cash Counter", "Warehouse", "AGEN"],
            "Rating": [0, 1.7, 2.0, 2.2],
            "Total_Ulasan": [0, 117, 23, 13],
            "Latitude": [-6.886, -6.958, -6.931, -6.924],
            "Longitude": [107.576, 107.756, 107.585, 107.689],
            "Teks_Ulasan": ["ramah cepat", "lama lelet parah", "kurang memuaskan", "biasa saja"],
            "link_maps": ["https://maps.google.com/?q=-6.886,107.576", "https://maps.google.com/?q=-6.958,107.756", "https://maps.google.com/?q=-6.931,107.585", "https://maps.google.com/?q=-6.924,107.689"]
        })
        
        # State Management untuk Cross-Filtering
        if "selected_kategori" not in st.session_state:
            st.session_state.selected_kategori = "Semua"
            
        # -- LAYOUT 3 KOLOM --
        col1, col2, col3 = st.columns([1.2, 1.5, 1.3])
        
        # ================= KOLOM KIRI =================
        with col1:
            st.markdown("<div class='metric-label'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
            kategori_options = ["Semua", "AGEN", "Cash Counter", "Warehouse"]
            # Gunakan radio button horizontal sebagai pengganti slicer Power BI
            selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed")
            st.session_state.selected_kategori = selected_kat
            
            # Filter Data based on selection
            if st.session_state.selected_kategori != "Semua":
                df_filtered = df[df["Kategori"] == st.session_state.selected_kategori]
            else:
                df_filtered = df
                
            rata_rating = df_filtered["Rating"].mean()
            
            # Bintang & Rating
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 50px; color:#FFD700;'>⭐</span>
                    <span class='big-metric'>{rata_rating:.1f}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Tabel
            st.dataframe(df_filtered[["Nama_Agen", "Rating", "Total_Ulasan"]], use_container_width=True, height=450)

        # ================= KOLOM TENGAH =================
        with col2:
            st.markdown("<div class='metric-label'>TOTAL ULASAN</div>", unsafe_allow_html=True)
            total_ulasan = df_filtered["Total_Ulasan"].sum()
            
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 40px;'>🗣️</span>
                    <span class='big-metric'>{total_ulasan:,}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='metric-label'>PETA LOKASI</div>", unsafe_allow_html=True)
            
            # Peta menggunakan Folium agar Marker bisa diklik dan mengarah ke link_maps
            m = folium.Map(location=[-6.917464, 107.619123], zoom_start=11) # Pusat di Bandung
            
            for idx, row in df_filtered.iterrows():
                if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
                    # Membuat HTML Popup dengan Link yang otomatis membuka tab baru
                    popup_html = f"""
                    <b>{row['Nama_Agen']}</b><br>
                    Rating: {row['Rating']}<br>
                    <a href="{row['link_maps']}" target="_blank" style="color:blue; text-decoration:underline;">Buka di Google Maps ↗</a>
                    """
                    folium.CircleMarker(
                        location=[row["Latitude"], row["Longitude"]],
                        radius=6,
                        color="#0072CE", # Biru JNE
                        fill=True,
                        fill_color="#0072CE",
                        fill_opacity=0.7,
                        popup=folium.Popup(popup_html, max_width=250),
                        tooltip=row["Nama_Agen"]
                    ).add_to(m)
            
            # Tampilkan peta di Streamlit
            st_folium(m, width=500, height=450, returned_objects=[])

        # ================= KOLOM KANAN =================
        with col3:
            st.markdown("<div class='metric-label'>RATA RATA RATING</div>", unsafe_allow_html=True)
            
            # Bar Chart Horizontal
            df_bar = df.groupby("Kategori")["Rating"].mean().reset_index()
            fig_bar = px.bar(df_bar, x="Rating", y="Kategori", orientation='h', text="Rating")
            fig_bar.update_traces(marker_color='#2ca02c', texttemplate='%{text:.1f}', textposition='outside')
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title=None, yaxis_title=None,
                height=150
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Word Cloud Sentimen
            st.markdown("<div class='metric-label'>SENTIMEN ULASAN PELANGGAN</div>", unsafe_allow_html=True)
            
            semua_kata = []
            for ulasan in df_filtered["Teks_Ulasan"]:
                semua_kata.extend(ekstrak_kata_penting(ulasan))
                
            if semua_kata:
                teks_gabungan = " ".join(semua_kata)
                wordcloud = WordCloud(width=800, height=450, background_color="white", colormap="tab20").generate(teks_gabungan)
                
                fig_wc, ax = plt.subplots(figsize=(8, 4.5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                fig_wc.patch.set_facecolor('white')
                st.pyplot(fig_wc)
            else:
                st.info("Tidak ada ulasan untuk ditampilkan.")

    except Exception as e:
        st.error(f"Terjadi kesalahan teknis: {e}")

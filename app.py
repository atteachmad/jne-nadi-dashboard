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
import os

# ==========================================
# 1. KONFIGURASI HALAMAN DASAR
# ==========================================
st.set_page_config(page_title="NADI - JNE Agent Monitoring", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. CUSTOM CSS UNTUK TAMPILAN
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .css-1r6slb0, .css-12oz5g7 {
        background-color: white; border-radius: 10px;
        padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .big-metric { font-size: 48px; font-weight: bold; text-align: center; color: #333; }
    .metric-label { font-size: 18px; text-align: center; font-weight: bold; color: #555; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. SISTEM LOGIN SEDERHANA
# ==========================================
def check_password():
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
# 4. FUNGSI BANTUAN (ANALISIS TEKS)
# ==========================================
KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", 
                "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", 
                "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", 
                "aja", "banget", "sih", "kok", "sama", "buat", "sangat", "lagi", "karena", "tapi"}

def ekstrak_kata_penting(teks):
    if pd.isna(teks): return []
    teks = str(teks).lower()
    teks = re.sub(r'[^a-z\s]', '', teks)
    return [k for k in teks.split() if k not in KATA_ABAIKAN and len(k) > 2]

# ==========================================
# 5. TAMPILAN DASHBOARD UTAMA
# ==========================================
if check_password():
    
    # -- HEADER --
    col_logo, col_title, col_filter, col_btn = st.columns([1, 4, 2, 1])
    with col_logo:
        if os.path.exists("logo_jne.png"):
            st.image("logo_jne.png", width=120)
        else:
            st.markdown("<h2 style='color:#0033a0; margin:0;'><b>JNE</b></h2>", unsafe_allow_html=True)

    with col_title:
        st.markdown("<h3 style='margin:0; padding-top:10px;'>JNE Bandung : Analisa Kualitas Layanan & Sentimen</h3>", unsafe_allow_html=True)
    with col_filter:
        global_filter = st.selectbox("Wilayah", ["Semua", "Bandung Kota", "Kabupaten Bandung", "Cimahi"], label_visibility="collapsed")
    with col_btn:
        st.button("CEK MAPS", use_container_width=True)

    st.divider()

    try:
        # -- KONEKSI DATA --
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="10m")
        df = df.dropna(how="all")

        # -- IDENTIFIKASI KOLOM OTOMATIS --
        kolom_rating = "Rating_Rata_Rata" if "Rating_Rata_Rata" in df.columns else "Rating"
        kolom_total_ulasan = "Total_Ulasan_Agen" if "Total_Ulasan_Agen" in df.columns else ("Total_Ulasan" if "Total_Ulasan" in df.columns else "Rating_Ulasan_Orang")
        kolom_kategori = "Kategori Warehouse" if "Kategori Warehouse" in df.columns else "Kategori"
        kolom_link = "link_maps" if "link_maps" in df.columns else "Link_Maps"

        # Memperbaiki Format Angka (Koma ke Titik) sebelum dikonversi
        df[kolom_rating] = df[kolom_rating].astype(str).str.replace(',', '.').str.strip()
        df[kolom_rating] = pd.to_numeric(df[kolom_rating], errors="coerce").fillna(0)
        
        if kolom_total_ulasan in df.columns:
            df[kolom_total_ulasan] = df[kolom_total_ulasan].astype(str).str.replace(',', '.').str.strip()
            df[kolom_total_ulasan] = pd.to_numeric(df[kolom_total_ulasan], errors="coerce").fillna(0)

        # Memperbaiki Format Koordinat Peta
        df["Latitude"] = df["Latitude"].astype(str).str.replace(',', '.').str.strip()
        df["Longitude"] = df["Longitude"].astype(str).str.replace(',', '.').str.strip()
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

        if kolom_kategori not in df.columns:
            df[kolom_kategori] = "AGEN" # Fallback

        # State Management Slicer
        if "selected_kategori" not in st.session_state:
            st.session_state.selected_kategori = "Semua"
            
        # -- LAYOUT 3 KOLOM --
        col1, col2, col3 = st.columns([1.2, 1.5, 1.3])
        
        # ================= KOLOM KIRI =================
        with col1:
            st.markdown("<div class='metric-label'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
            kategori_options = ["Semua"] + list(df[kolom_kategori].dropna().unique())
            selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed")
            st.session_state.selected_kategori = selected_kat
            
            # Filter Data sesuai klik Slicer
            if st.session_state.selected_kategori != "Semua":
                df_filtered = df[df[kolom_kategori] == st.session_state.selected_kategori]
            else:
                df_filtered = df
                
            # -- LOGIKA TABEL SESUAI SPREADSHEET (MENGHINDARI DUPLIKASI) --
            if kolom_total_ulasan in df.columns:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({
                    kolom_rating: "max", 
                    kolom_total_ulasan: "max"
                }).reset_index()
            else:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({kolom_rating: "max"}).reset_index()
            
            # Mengurutkan Tabel & Format Koma
            df_tabel = df_tabel.sort_values(by=kolom_rating, ascending=True)
            df_tabel_display = df_tabel.copy()
            df_tabel_display[kolom_rating] = df_tabel_display[kolom_rating].apply(lambda x: f"{x:.1f}".replace(".", ","))
            if kolom_total_ulasan in df_tabel_display.columns:
                df_tabel_display[kolom_total_ulasan] = df_tabel_display[kolom_total_ulasan].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            
            # -- LOGIKA DAX: KPI RATING --
            # Format: "⭐ "  & SUBSTITUTE(FORMAT([Avg_Rating_Per_Agen], "0.0"), ".", ",")
            rata_rating = df_tabel[kolom_rating].mean()
            rating_text = f"{rata_rating:.1f}".replace(".", ",")
            
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 50px; color:#FFD700;'>⭐</span>
                    <span class='big-metric'>{rating_text}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Tampilkan Tabel
            st.dataframe(df_tabel_display, hide_index=True, use_container_width=True, height=400)

        # ================= KOLOM TENGAH =================
        with col2:
            st.markdown("<div class='metric-label'>TOTAL ULASAN</div>", unsafe_allow_html=True)
            
            # -- LOGIKA DAX: TOTAL ULASAN --
            # SUMX(VALUES('BI FM'[Nama_Agen]), CALCULATE(MAX('BI FM'[Total_Ulasan_Agen])))
            if kolom_total_ulasan in df.columns:
                total_ulasan = df_tabel[kolom_total_ulasan].sum()
            else:
                total_ulasan = len(df_filtered)
            
            # Format "#,##0" versi Indonesia (titik sebagai pemisah ribuan)
            ulasan_text = f"{total_ulasan:,.0f}".replace(",", ".")
            
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 40px;'>🗣️</span>
                    <span class='big-metric'>{ulasan_text}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='metric-label'>PETA LOKASI</div>", unsafe_allow_html=True)
            
            # -- PETA MAPS INTERAKTIF --
            m = folium.Map(location=[-6.917464, 107.619123], zoom_start=11)
            
            df_map_unik = df_filtered.drop_duplicates(subset=["Nama_Agen"]).copy()
            
            for idx, row in df_map_unik.iterrows():
                if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
                    # Mengambil URL Maps dari Database
                    url_maps = row.get(kolom_link, f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}")
                    
                    popup_html = f"""
                    <div style="font-family: Arial; min-width: 150px;">
                        <b>{row['Nama_Agen']}</b><br>
                        Rating: {str(row.get(kolom_rating, 0)).replace('.', ',')}<br>
                        <a href="{url_maps}" target="_blank" style="display:inline-block; margin-top:8px; padding:6px 12px; background-color:#0033a0; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">
                            Buka di Google Maps ↗
                        </a>
                    </div>
                    """
                    folium.CircleMarker(
                        location=[row["Latitude"], row["Longitude"]],
                        radius=7,
                        color="#0033a0", # Biru Gelap JNE
                        fill=True, fill_color="#ed1c24", # Merah JNE
                        fill_opacity=0.9,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=row["Nama_Agen"]
                    ).add_to(m)
            
            st_folium(m, width=500, height=400, returned_objects=[])

        # ================= KOLOM KANAN =================
        with col3:
            st.markdown("<div class='metric-label'>RATA RATA RATING</div>", unsafe_allow_html=True)
            
            # Hitung rata-rata tiap kategori berdasarkan data unik agen saja
            df_bar = df_map_unik.groupby(kolom_kategori)[kolom_rating].mean().reset_index()
            df_bar = df_bar.sort_values(by=kolom_rating, ascending=True)
            
            fig_bar = px.bar(df_bar, x=kolom_rating, y=kolom_kategori, orientation='h', text=kolom_rating)
            fig_bar.update_traces(marker_color='#2ca02c', texttemplate='%{text:.1f}', textposition='outside')
            
            # Menyesuaikan koma di grafik (Opsional, bawaan Plotly biasa titik)
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=30, t=10, b=0), xaxis_title=None, yaxis_title=None, height=180
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # -- WORD CLOUD --
            st.markdown("<div class='metric-label'>SENTIMEN ULASAN PELANGGAN</div>", unsafe_allow_html=True)
            
            if "Teks_Ulasan" in df_filtered.columns:
                semua_kata = []
                for ulasan in df_filtered["Teks_Ulasan"]:
                    semua_kata.extend(ekstrak_kata_penting(ulasan))
                    
                if semua_kata:
                    teks_gabungan = " ".join(semua_kata)
                    wordcloud = WordCloud(width=800, height=400, background_color="white", colormap="tab20").generate(teks_gabungan)
                    
                    fig_wc, ax = plt.subplots(figsize=(8, 4))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis("off")
                    fig_wc.patch.set_facecolor('white')
                    st.pyplot(fig_wc)
                else:
                    st.info("Tidak ada ulasan berbentuk teks yang bisa dianalisis.")

    except Exception as e:
        st.error(f"Gagal memuat data. Periksa penamaan kolom di Spreadsheet. Detail Error: {e}")

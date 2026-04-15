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
# 1. KONFIGURASI HALAMAN DASAR (16:9 1366x768)
# ==========================================
st.set_page_config(page_title="NADI - JNE Agent Monitoring", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. CUSTOM CSS UNTUK TAMPILAN "POWER BI"
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
# 3. FUNGSI BANTUAN
# ==========================================
KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", 
                "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", 
                "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", 
                "aja", "banget", "sih", "kok", "sama", "buat", "sangat"}

def ekstrak_kata_penting(teks):
    if pd.isna(teks): return []
    teks = str(teks).lower()
    teks = re.sub(r'[^a-z\s]', '', teks)
    return [k for k in teks.split() if k not in KATA_ABAIKAN and len(k) > 2]

# ==========================================
# 4. DASHBOARD UTAMA
# ==========================================

# -- HEADER --
col_logo, col_title, col_filter, col_btn = st.columns([1, 4, 2, 1])
with col_logo:
    # Memanggil logo lokal jika ada, jika tidak pakai teks alternatif
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
    # -- KONEKSI DATA GOOGLE SHEETS ASLI --
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="10m") # Update setiap 10 menit
    df = df.dropna(how="all")

    # Pastikan tipe data angka terbaca benar (sesuaikan nama kolom ini dengan yang ada di Google Sheets Anda)
    # Jika nama kolom di GSheets berbeda, ganti tulisan di dalam tanda kutip ("...") di bawah ini.
    kolom_rating = "Rating" 
    kolom_total_ulasan = "Total_Ulasan"
    
    # Jika di GSheets nama kolomnya beda (contoh: Rating_Rata_Rata), sesuaikan kodenya di sini:
    if "Rating_Rata_Rata" in df.columns: kolom_rating = "Rating_Rata_Rata"
    if "Rating_Ulasan_Orang" in df.columns: kolom_total_ulasan = "Rating_Ulasan_Orang"

    df[kolom_rating] = pd.to_numeric(df[kolom_rating], errors="coerce").fillna(0)
    df[kolom_total_ulasan] = pd.to_numeric(df[kolom_total_ulasan], errors="coerce").fillna(0)
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    
    # State Management untuk Slicer Kategori
    if "selected_kategori" not in st.session_state:
        st.session_state.selected_kategori = "Semua"
        
    # -- LAYOUT 3 KOLOM --
    col1, col2, col3 = st.columns([1.2, 1.5, 1.3])
    
    # ================= KOLOM KIRI =================
    with col1:
        st.markdown("<div class='metric-label'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
        
        # Cek apakah kolom Kategori ada di data
        if "Kategori" in df.columns:
            kategori_options = ["Semua"] + list(df["Kategori"].dropna().unique())
        else:
            kategori_options = ["Semua", "AGEN", "Cash Counter", "Warehouse"]
            df["Kategori"] = "AGEN" # Fallback jika kolom Kategori tidak ada
            
        selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed")
        st.session_state.selected_kategori = selected_kat
        
        # Filter Data
        if st.session_state.selected_kategori != "Semua":
            df_filtered = df[df["Kategori"] == st.session_state.selected_kategori]
        else:
            df_filtered = df
            
        rata_rating = df_filtered[kolom_rating].mean()
        
        st.markdown(f"""
            <div class='css-1r6slb0' style='text-align:center;'>
                <span style='font-size: 50px; color:#FFD700;'>⭐</span>
                <span class='big-metric'>{rata_rating:.1f}</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabel tanpa nomor urut (hide_index=True)
        st.dataframe(
            df_filtered[["Nama_Agen", kolom_rating, kolom_total_ulasan]], 
            hide_index=True, 
            use_container_width=True, 
            height=400
        )

    # ================= KOLOM TENGAH =================
    with col2:
        st.markdown("<div class='metric-label'>TOTAL ULASAN</div>", unsafe_allow_html=True)
        total_ulasan = df_filtered[kolom_total_ulasan].sum()
        
        st.markdown(f"""
            <div class='css-1r6slb0' style='text-align:center;'>
                <span style='font-size: 40px;'>🗣️</span>
                <span class='big-metric'>{total_ulasan:,.0f}</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='metric-label'>PETA LOKASI</div>", unsafe_allow_html=True)
        
        # Peta Folium
        m = folium.Map(location=[-6.917464, 107.619123], zoom_start=11)
        
        for idx, row in df_filtered.iterrows():
            if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
                link_maps = row.get("link_maps", f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}")
                popup_html = f"""
                <b>{row['Nama_Agen']}</b><br>
                Rating: {row[kolom_rating]}<br>
                <a href="{link_maps}" target="_blank" style="color:blue; text-decoration:underline;">Buka di Google Maps ↗</a>
                """
                folium.CircleMarker(
                    location=[row["Latitude"], row["Longitude"]],
                    radius=6,
                    color="#0072CE", 
                    fill=True, fill_color="#0072CE", fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=row["Nama_Agen"]
                ).add_to(m)
        
        st_folium(m, width=500, height=400, returned_objects=[])

    # ================= KOLOM KANAN =================
    with col3:
        st.markdown("<div class='metric-label'>RATA RATA RATING</div>", unsafe_allow_html=True)
        
        df_bar = df.groupby("Kategori")[kolom_rating].mean().reset_index()
        fig_bar = px.bar(df_bar, x=kolom_rating, y="Kategori", orientation='h', text=kolom_rating)
        fig_bar.update_traces(marker_color='#2ca02c', texttemplate='%{text:.1f}', textposition='outside')
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None, yaxis_title=None, height=180
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
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
                st.info("Tidak ada kata untuk dianalisis.")
        else:
            st.warning("Kolom 'Teks_Ulasan' tidak ditemukan di Google Sheets.")

except Exception as e:
    st.error(f"Gagal memuat data dari Google Sheets. Detail: {e}")

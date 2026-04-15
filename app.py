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
# 4. FUNGSI BANTUAN (ANALISIS TEKS)
# ==========================================
KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", 
                "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", 
                "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", 
                "aja", "banget", "sih", "kok", "sama", "buat", "sangat", "lagi", "karena"}

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
        kolom_total_ulasan = "Total_Ulasan" if "Total_Ulasan" in df.columns else ("Rating_Ulasan_Orang" if "Rating_Ulasan_Orang" in df.columns else None)
        
        # Mencari kolom Kategori (Bisa bernama "Kategori" atau "Kategori Warehouse" di Spreadsheet)
        kolom_kategori = "Kategori"
        if "Kategori" not in df.columns and "Kategori Warehouse" in df.columns:
            kolom_kategori = "Kategori Warehouse"

        # Pembersihan Tipe Data Angka
        df[kolom_rating] = pd.to_numeric(df[kolom_rating], errors="coerce").fillna(0)
        if kolom_total_ulasan:
            df[kolom_total_ulasan] = pd.to_numeric(df[kolom_total_ulasan], errors="coerce").fillna(0)

        # State Management Slicer
        if "selected_kategori" not in st.session_state:
            st.session_state.selected_kategori = "Semua"
            
        # -- LAYOUT 3 KOLOM --
        col1, col2, col3 = st.columns([1.2, 1.5, 1.3])
        
        # ================= KOLOM KIRI =================
        with col1:
            st.markdown("<div class='metric-label'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
            
            # Buat Slicer berdasarkan isi asli spreadsheet
            if kolom_kategori in df.columns:
                kategori_options = ["Semua"] + list(df[kolom_kategori].dropna().unique())
            else:
                kategori_options = ["Semua", "AGEN", "Warehouse", "Cash Counter"]
                df[kolom_kategori] = "AGEN" # Fallback jika kolom benar-benar tidak ditemukan
                
            selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed")
            st.session_state.selected_kategori = selected_kat
            
            # Filter Data sesuai klik Slicer
            if st.session_state.selected_kategori != "Semua":
                df_filtered = df[df[kolom_kategori] == st.session_state.selected_kategori]
            else:
                df_filtered = df
                
            # -- PENGELOMPOKAN DATA TABEL (MENCEGAH DUPLIKAT & SORTING TERENDAH) --
            if kolom_total_ulasan:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({
                    kolom_rating: "mean",
                    kolom_total_ulasan: "max" # Mengambil angka ulasan tertinggi per agen
                }).reset_index()
            else:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({kolom_rating: "mean"}).reset_index()
            
            # Mengurutkan dari Rating Paling Rendah ke Tinggi
            df_tabel = df_tabel.sort_values(by=kolom_rating, ascending=True)
            
            rata_rating = df_filtered[kolom_rating].mean()
            
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 50px; color:#FFD700;'>⭐</span>
                    <span class='big-metric'>{rata_rating:.1f}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Tampilkan Tabel (hide_index=True membuang angka urut awal)
            if kolom_total_ulasan:
                st.dataframe(df_tabel[["Nama_Agen", kolom_rating, kolom_total_ulasan]], hide_index=True, use_container_width=True, height=400)
            else:
                st.dataframe(df_tabel[["Nama_Agen", kolom_rating]], hide_index=True, use_container_width=True, height=400)

        # ================= KOLOM TENGAH =================
        with col2:
            st.markdown("<div class='metric-label'>TOTAL ULASAN</div>", unsafe_allow_html=True)
            
            # Hitung total ulasan unik
            if kolom_total_ulasan:
                total_ulasan = df_tabel[kolom_total_ulasan].sum()
            else:
                total_ulasan = len(df_filtered) # Jika tidak ada kolom total, hitung baris data mentah
            
            st.markdown(f"""
                <div class='css-1r6slb0' style='text-align:center;'>
                    <span style='font-size: 40px;'>🗣️</span>
                    <span class='big-metric'>{total_ulasan:,.0f}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='metric-label'>PETA LOKASI</div>", unsafe_allow_html=True)
            
            # Peta Folium (Gunakan data unik agar tidak menumpuk titik di kordinat yang sama)
            m = folium.Map(location=[-6.917464, 107.619123], zoom_start=11)
            
            # Ambil satu baris saja untuk tiap agen beserta kordinatnya
            df_map_unik = df_filtered.drop_duplicates(subset=["Nama_Agen"]).copy()
            df_map_unik["Latitude"] = pd.to_numeric(df_map_unik.get("Latitude"), errors="coerce")
            df_map_unik["Longitude"] = pd.to_numeric(df_map_unik.get("Longitude"), errors="coerce")
            
            for idx, row in df_map_unik.iterrows():
                if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
                    link_maps = row.get("link_maps", f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}")
                    popup_html = f"""
                    <b>{row['Nama_Agen']}</b><br>
                    Rating: {row.get(kolom_rating, 0):.1f}<br>
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
            
            # -- PERBAIKAN GRAFIK BAR (AGEN, WAREHOUSE, CASH COUNTER) --
            # Mengelompokkan semua data di sheet berdasarkan kategori untuk mendapatkan rata-ratanya
            df_bar = df.groupby(kolom_kategori)[kolom_rating].mean().reset_index()
            
            # Urutkan berdasarkan rating tertinggi ke terendah untuk tampilan visual yang bagus
            df_bar = df_bar.sort_values(by=kolom_rating, ascending=True)
            
            fig_bar = px.bar(df_bar, x=kolom_rating, y=kolom_kategori, orientation='h', text=kolom_rating)
            fig_bar.update_traces(marker_color='#2ca02c', texttemplate='%{text:.1f}', textposition='outside')
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
            else:
                st.warning("Kolom 'Teks_Ulasan' tidak ditemukan.")

    except Exception as e:
        st.error(f"Gagal memuat data. Periksa penamaan kolom di Spreadsheet. Detail Error: {e}")

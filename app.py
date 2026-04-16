import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import re
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
        # Cek apakah username ada dan password cocok
        if (st.session_state["username"] in st.secrets["credentials"] and
            st.session_state["password"] == st.secrets["credentials"][st.session_state["username"]]["password"]):
            
            # JIKA BENAR:
            st.session_state["role"] = st.secrets["credentials"][st.session_state["username"]]["role"]
            st.session_state["password_correct"] = True
            
        else:
            # JIKA SALAH:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #0033a0;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #555;'>JNE Agent Rating & Sentiment Analysis</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered, use_container_width=True)
        return False
    
    elif not st.session_state["password_correct"]:
        st.markdown("<h1 style='text-align: center; color: #0033a0;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
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
# 3. FUNGSI BANTUAN & CSS CUSTOM
# ==========================================
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #f4f7f6;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Efek Card Modern */
    .metric-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        text-align: center;
        border-top: 4px solid #0033a0;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    
    .big-metric {
        font-size: 42px;
        font-weight: 800;
        color: #333;
        margin: 10px 0;
    }
    
    .metric-label {
        font-size: 14px;
        font-weight: 700;
        color: #888;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    
    /* Tombol Kustom */
    .stButton>button {
        background-color: #0033a0 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #ed1c24 !important;
    }
</style>
""", unsafe_allow_html=True)

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
# 4. TAMPILAN DASHBOARD UTAMA
# ==========================================
if check_password():
    
    # Inisialisasi State Interaksi
    if "selected_kategori" not in st.session_state:
        st.session_state.selected_kategori = "Semua"
    if "selected_agent" not in st.session_state:
        st.session_state.selected_agent = None

    # -- HEADER --
    col_logo, col_title, col_filter, col_btn = st.columns([1, 4, 2, 1])
    with col_logo:
        if os.path.exists("logo_jne.png"):
            st.image("logo_jne.png", width=120)
        else:
            st.markdown("<h2 style='color:#0033a0; margin:0; font-weight:900;'>JNE</h2>", unsafe_allow_html=True)

    with col_title:
        st.markdown("<h3 style='margin:0; padding-top:5px; color:#333;'>Dashboard Analisis Kualitas & Sentimen</h3>", unsafe_allow_html=True)
    with col_filter:
        global_filter = st.selectbox("Wilayah", ["Semua", "Bandung Kota", "Kabupaten Bandung", "Cimahi"], label_visibility="collapsed")
    with col_btn:
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.session_state.selected_agent = None # Reset pilihan agen saat di-refresh

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

        # Memperbaiki Format Angka & Koordinat
        df[kolom_rating] = pd.to_numeric(df[kolom_rating].astype(str).str.replace(',', '.').str.strip(), errors="coerce").fillna(0)
        if kolom_total_ulasan in df.columns:
            df[kolom_total_ulasan] = pd.to_numeric(df[kolom_total_ulasan].astype(str).str.replace(',', '.').str.strip(), errors="coerce").fillna(0)

        df["Latitude"] = pd.to_numeric(df["Latitude"].astype(str).str.replace(',', '.').str.strip(), errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"].astype(str).str.replace(',', '.').str.strip(), errors="coerce")

        if kolom_kategori not in df.columns:
            df[kolom_kategori] = "AGEN" # Fallback
            
        # -- LAYOUT 3 KOLOM --
        col1, col2, col3 = st.columns([1.2, 1.6, 1.2])
        
        # FILTER DASAR (Kategori)
        df_filtered_cat = df[df[kolom_kategori] == st.session_state.selected_kategori] if st.session_state.selected_kategori != "Semua" else df
        
        # FILTER FOKUS (Berdasarkan Klik Tabel / Peta)
        if st.session_state.selected_agent:
            df_focus = df_filtered_cat[df_filtered_cat["Nama_Agen"] == st.session_state.selected_agent]
        else:
            df_focus = df_filtered_cat

        # ================= KOLOM KIRI =================
        with col1:
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
            kategori_options = ["Semua"] + list(df[kolom_kategori].dropna().unique())
            selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed", index=kategori_options.index(st.session_state.selected_kategori))
            
            # Jika ganti kategori, reset agen yg dipilih
            if selected_kat != st.session_state.selected_kategori:
                st.session_state.selected_kategori = selected_kat
                st.session_state.selected_agent = None
                st.rerun()

            # Data untuk Tabel (Selalu tampilkan semua dalam kategori agar bisa dipilih)
            if kolom_total_ulasan in df.columns:
                df_tabel = df_filtered_cat.groupby("Nama_Agen").agg({kolom_rating: "max", kolom_total_ulasan: "max"}).reset_index()
            else:
                df_tabel = df_filtered_cat.groupby("Nama_Agen").agg({kolom_rating: "max"}).reset_index()
            
            df_tabel = df_tabel.sort_values(by=kolom_rating, ascending=False)
            df_tabel_display = df_tabel.copy()
            df_tabel_display[kolom_rating] = df_tabel_display[kolom_rating].apply(lambda x: f"{x:.1f}".replace(".", ","))
            if kolom_total_ulasan in df_tabel_display.columns:
                df_tabel_display[kolom_total_ulasan] = df_tabel_display[kolom_total_ulasan].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            
            # Highlight metrik
            rata_rating = df_focus[kolom_rating].mean() if not df_focus.empty else 0
            rating_text = f"{rata_rating:.1f}".replace(".", ",")
            
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Rata-rata Rating {"(Spesifik Agen)" if st.session_state.selected_agent else ""}</div>
                    <div class='big-metric'><span style='color:#FFD700;'>⭐</span> {rating_text}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Tombol Reset Pilihan
            if st.session_state.selected_agent:
                if st.button("❌ Hapus Pilihan Agen & Tampilkan Semua", use_container_width=True):
                    st.session_state.selected_agent = None
                    st.rerun()

            st.markdown("<small><i>Klik baris pada tabel untuk filter detail agen.</i></small>", unsafe_allow_html=True)
            
            # TABEL INTERAKTIF (Membutuhkan Streamlit >= 1.35)
            selection_event = st.dataframe(
                df_tabel_display, 
                hide_index=True, 
                use_container_width=True, 
                height=400,
                on_select="rerun", # Ini kunci interaktivitas tabel
                selection_mode="single-row"
            )
            
            # Tangkap klik tabel
            if selection_event.selection.rows:
                selected_idx = selection_event.selection.rows[0]
                clicked_agent = df_tabel_display.iloc[selected_idx]["Nama_Agen"]
                if clicked_agent != st.session_state.selected_agent:
                    st.session_state.selected_agent = clicked_agent
                    st.rerun()

        # ================= KOLOM TENGAH =================
        with col2:
            if kolom_total_ulasan in df.columns:
                total_ulasan = df_focus.drop_duplicates(subset=["Nama_Agen"])[kolom_total_ulasan].sum()
            else:
                total_ulasan = len(df_focus)
            
            ulasan_text = f"{total_ulasan:,.0f}".replace(",", ".")
            
            st.markdown(f"""
                <div class='metric-card' style='border-top: 4px solid #ed1c24;'>
                    <div class='metric-label'>Total Ulasan Pelanggan {"(Spesifik Agen)" if st.session_state.selected_agent else ""}</div>
                    <div class='big-metric'>🗣️ {ulasan_text}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>PETA LOKASI AGEN</div>", unsafe_allow_html=True)
            
            # -- LOGIKA AUTO ZOOM PETA --
            if st.session_state.selected_agent and not df_focus.empty:
                # Fokus ke satu agen
                center_lat = df_focus["Latitude"].mean()
                center_lon = df_focus["Longitude"].mean()
                zoom_level = 16 # Zoom dekat
            else:
                # Default Bandung area
                center_lat = -6.917464
                center_lon = 107.619123
                zoom_level = 12
                
            m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level, tiles="CartoDB positron")
            df_map_unik = df_focus.drop_duplicates(subset=["Nama_Agen"]).copy()
            
            for idx, row in df_map_unik.iterrows():
                if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
                    
                    if kolom_link in df.columns and pd.notna(row[kolom_link]) and str(row[kolom_link]).strip():
                        url_maps = str(row[kolom_link])
                    else:
                        url_maps = f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}"
                    
                    # HTML Card Interaktif
                    popup_html = f"""
                    <div style="font-family: 'Segoe UI', sans-serif; min-width: 220px; padding: 5px; text-align: center;">
                        <h4 style="color: #0033a0; margin: 0 0 10px 0; font-size:16px;">{row['Nama_Agen']}</h4>
                        <div style="font-size: 20px; font-weight: bold; margin-bottom: 15px;">
                            <span style="color: #FFD700;">⭐</span> {str(row.get(kolom_rating, 0)).replace('.', ',')}
                        </div>
                        <a href="{url_maps}" target="_blank" style="display: block; width: 100%; padding: 10px 0; background-color: #ed1c24; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px;">
                            📍 BUKA DI GOOGLE MAPS
                        </a>
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[row["Latitude"], row["Longitude"]],
                        radius=8 if not st.session_state.selected_agent else 12, # Besarkan marker jika di-klik
                        color="white", 
                        weight=2,
                        fill=True, 
                        fill_color="#0033a0" if not st.session_state.selected_agent else "#ed1c24", # Merah jika sedang fokus
                        fill_opacity=1.0,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=row['Nama_Agen'] # Penting: Ini ditangkap oleh last_object_clicked_tooltip
                    ).add_to(m)
            
            # Render peta & tangkap klik peta
            map_data = st_folium(m, use_container_width=True, height=400)
            
            if map_data and map_data.get("last_object_clicked_tooltip"):
                clicked_map_agent = map_data["last_object_clicked_tooltip"]
                if clicked_map_agent != st.session_state.selected_agent:
                    st.session_state.selected_agent = clicked_map_agent
                    st.rerun()

        # ================= KOLOM KANAN =================
        with col3:
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>RATA-RATA RATING PER KATEGORI</div>", unsafe_allow_html=True)
            
            # Bar chart lebih relevan tidak difilter hingga 1 agen, agar perbandingannya terlihat
            df_bar_unik = df_filtered_cat.drop_duplicates(subset=["Nama_Agen"]).copy()
            df_bar = df_bar_unik.groupby(kolom_kategori)[kolom_rating].mean().reset_index()
            df_bar = df_bar.sort_values(by=kolom_rating, ascending=True)
            
            fig_bar = px.bar(df_bar, x=kolom_rating, y=kolom_kategori, orientation='h', text=kolom_rating)
            fig_bar.update_traces(
                marker_color='#0033a0', 
                texttemplate='<b>%{text:.1f}</b>', 
                textposition='outside',
                cliponaxis=False
            )
            
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=40, t=10, b=0), xaxis_title=None, yaxis_title=None, height=220,
                xaxis=dict(showgrid=False, showticklabels=False),
                font=dict(family="Segoe UI", size=13)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown(f"<div class='metric-label' style='margin-top:20px; margin-bottom:10px;'>SENTIMEN ULASAN {'AGEN INI' if st.session_state.selected_agent else 'PELANGGAN'}</div>", unsafe_allow_html=True)
            
            if "Teks_Ulasan" in df.columns:
                semua_kata = []
                for ulasan in df_focus["Teks_Ulasan"].dropna():
                    semua_kata.extend(ekstrak_kata_penting(ulasan))
                    
                if semua_kata:
                    teks_gabungan = " ".join(semua_kata)
                    wordcloud = WordCloud(
                        width=600, height=350, 
                        background_color="#f4f7f6",
                        colormap="Set1", 
                        max_words=100,
                        contour_width=0
                    ).generate(teks_gabungan)
                    
                    fig_wc, ax = plt.subplots(figsize=(6, 3.5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis("off")
                    fig_wc.patch.set_facecolor('#f4f7f6')
                    st.pyplot(fig_wc)
                else:
                    st.info("Tidak ada kata sentimen yang terekam untuk pilihan ini.")
            else:
                st.info("Kolom 'Teks_Ulasan' tidak ditemukan di database.")

    except Exception as e:
        st.error(f"Gagal memuat data. Periksa penamaan kolom di Spreadsheet. Detail Error: {e}")

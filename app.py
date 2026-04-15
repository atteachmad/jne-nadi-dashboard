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
    def password_entered():
        if (st.session_state["username"] == st.secrets["credentials"]["username"] and 
            st.session_state["password"] == st.secrets["credentials"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #0033a0;'>📦 NADI Login Portal</h1>", unsafe_allow_html=True)
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
    .stApp { background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, sans-serif; }
    .metric-card {
        background-color: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px;
        transition: transform 0.2s; text-align: center; border-top: 4px solid #0033a0;
    }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
    .big-metric { font-size: 42px; font-weight: 800; color: #333; margin: 10px 0; }
    .metric-label { font-size: 14px; font-weight: 700; color: #888; text-transform: uppercase; }
    .stButton>button { background-color: #0033a0 !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; border: none !important; }
    .stButton>button:hover { background-color: #ed1c24 !important; }
</style>
""", unsafe_allow_html=True)

KATA_ABAIKAN = {"yang", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "dan", "atau", "ini", "itu", "juga", "sudah", "saya", "kami", "paket", "jne", "kurir", "barang", "kiriman", "nya", "ada", "tidak", "bisa", "belum", "aja", "banget", "sih", "kok", "sama", "buat", "sangat", "lagi", "karena", "tapi"}

def ekstrak_kata_penting(teks):
    if pd.isna(teks): return []
    teks = str(teks).lower()
    teks = re.sub(r'[^a-z\s]', '', teks)
    return [k for k in teks.split() if k not in KATA_ABAIKAN and len(k) > 2]

# ==========================================
# 4. TAMPILAN DASHBOARD UTAMA
# ==========================================
if check_password():
    # -- HEADER --
    col_logo, col_title, col_filter, col_btn = st.columns([1, 4, 2, 1])
    with col_logo:
        if os.path.exists("logo_jne.png"): st.image("logo_jne.png", width=120)
        else: st.markdown("<h2 style='color:#0033a0; margin:0; font-weight:900;'>JNE</h2>", unsafe_allow_html=True)
    with col_title:
        st.markdown("<h3 style='margin:0; padding-top:5px; color:#333;'>Dashboard Analisis Kualitas & Sentimen</h3>", unsafe_allow_html=True)
    with col_filter:
        global_filter = st.selectbox("Wilayah", ["Semua", "Bandung Kota", "Kabupaten Bandung", "Cimahi"], label_visibility="collapsed")
    with col_btn:
        if st.button("🔄 REFRESH DATA", use_container_width=True): st.cache_data.clear()

    st.divider()

    try:
        # -- KONEKSI DATA --
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="10m")
        df = df.dropna(how="all")

        # -- PENCARIAN NAMA KOLOM FLEKSIBEL --
        kolom_rating = next((c for c in df.columns if "rating" in c.lower() and "rata" in c.lower()), "Rating")
        kolom_total_ulasan = next((c for c in df.columns if "ulasan" in c.lower() and "total" in c.lower()), "Total_Ulasan")
        kolom_kategori = next((c for c in df.columns if "kategori" in c.lower()), "Kategori")
        kolom_link = next((c for c in df.columns if "link" in c.lower() or "url" in c.lower()), "Link_Maps")
        kolom_lat = next((c for c in df.columns if "lat" in c.lower()), "Latitude")
        kolom_lon = next((c for c in df.columns if "lon" in c.lower()), "Longitude")

        # -- PEMBERSIHAN DATA ANGKA & KOORDINAT SECARA AGRESIF --
        df[kolom_rating] = pd.to_numeric(df[kolom_rating].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors="coerce").fillna(0)
        
        if kolom_total_ulasan in df.columns:
            df[kolom_total_ulasan] = pd.to_numeric(df[kolom_total_ulasan].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True), errors="coerce").fillna(0)

        # Pembersihan ekstrim untuk Latitude & Longitude agar pasti terbaca sebagai angka
        if kolom_lat in df.columns and kolom_lon in df.columns:
            df[kolom_lat] = pd.to_numeric(df[kolom_lat].astype(str).str.replace(',', '.').str.replace(r'[^\d.-]', '', regex=True), errors="coerce")
            df[kolom_lon] = pd.to_numeric(df[kolom_lon].astype(str).str.replace(',', '.').str.replace(r'[^\d.-]', '', regex=True), errors="coerce")

        if "selected_kategori" not in st.session_state: st.session_state.selected_kategori = "Semua"
            
        # -- LAYOUT 3 KOLOM --
        col1, col2, col3 = st.columns([1.2, 1.6, 1.2])
        
        # ================= KOLOM KIRI =================
        with col1:
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>KATEGORI WAREHOUSE</div>", unsafe_allow_html=True)
            kategori_options = ["Semua"] + list(df[kolom_kategori].dropna().unique())
            selected_kat = st.radio("", kategori_options, horizontal=True, label_visibility="collapsed")
            st.session_state.selected_kategori = selected_kat
            
            df_filtered = df[df[kolom_kategori] == st.session_state.selected_kategori] if st.session_state.selected_kategori != "Semua" else df
                
            # Logika Tabel
            if kolom_total_ulasan in df.columns:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({kolom_rating: "max", kolom_total_ulasan: "max"}).reset_index()
            else:
                df_tabel = df_filtered.groupby("Nama_Agen").agg({kolom_rating: "max"}).reset_index()
            
            df_tabel = df_tabel.sort_values(by=kolom_rating, ascending=False)
            
            # Format tampilan tabel
            df_tabel_display = df_tabel.copy()
            df_tabel_display[kolom_rating] = df_tabel_display[kolom_rating].apply(lambda x: f"{x:.1f}".replace(".", ","))
            if kolom_total_ulasan in df_tabel_display.columns:
                df_tabel_display[kolom_total_ulasan] = df_tabel_display[kolom_total_ulasan].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            
            rata_rating = df_tabel[kolom_rating].mean() if not df_tabel.empty else 0
            
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Rata-rata Rating</div>
                    <div class='big-metric'><span style='color:#FFD700;'>⭐</span> {f"{rata_rating:.1f}".replace(".", ",")}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # TABEL INTERAKTIF (Bisa di-klik untuk filter Peta)
            st.caption("💡 *Klik baris tabel di bawah untuk melihat lokasi agen di peta*")
            tabel_event = st.dataframe(
                df_tabel_display, 
                hide_index=True, 
                use_container_width=True, 
                height=420,
                on_select="rerun", # Memicu update saat di klik
                selection_mode="single-row"
            )

        # ================= KOLOM TENGAH =================
        with col2:
            total_ulasan = df_tabel[kolom_total_ulasan].sum() if kolom_total_ulasan in df.columns else len(df_filtered)
            
            st.markdown(f"""
                <div class='metric-card' style='border-top: 4px solid #ed1c24;'>
                    <div class='metric-label'>Total Ulasan Pelanggan</div>
                    <div class='big-metric'>🗣️ {f"{total_ulasan:,.0f}".replace(",", ".")}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>PETA LOKASI AGEN</div>", unsafe_allow_html=True)
            
            # -- LOGIKA FILTER PETA BERDASARKAN KLIK TABEL --
            df_map_unik = df_filtered.drop_duplicates(subset=["Nama_Agen"]).copy()
            
            if len(tabel_event.selection.rows) > 0:
                # Jika ada baris yang diklik, filter peta khusus untuk agen tersebut
                idx_terpilih = tabel_event.selection.rows[0]
                nama_agen_terpilih = df_tabel_display.iloc[idx_terpilih]["Nama_Agen"]
                df_map_unik = df_map_unik[df_map_unik["Nama_Agen"] == nama_agen_terpilih]

            # Filter hanya data yang punya koordinat valid
            df_map_valid = df_map_unik.dropna(subset=[kolom_lat, kolom_lon])
            
            if not df_map_valid.empty:
                # Auto-center map berdasarkan data yang difilter
                center_lat = df_map_valid[kolom_lat].mean()
                center_lon = df_map_valid[kolom_lon].mean()
                zoom_level = 14 if len(df_map_valid) == 1 else 11
                
                m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level, tiles="CartoDB positron")
                
                for _, row in df_map_valid.iterrows():
                    # Prioritaskan Link_Maps dari GSheets, jika kosong buat otomatis dari koordinat
                    link_spreadsheet = str(row.get(kolom_link, ""))
                    if link_spreadsheet != "nan" and link_spreadsheet.strip() != "":
                        url_maps = link_spreadsheet
                    else:
                        url_maps = f"https://www.google.com/maps/search/?api=1&query={row[kolom_lat]},{row[kolom_lon]}"
                    
                    rating_agen = str(row.get(kolom_rating, 0)).replace('.', ',')
                    
                    popup_html = f"""
                    <div style="font-family: 'Segoe UI', sans-serif; min-width: 200px; text-align: center;">
                        <h4 style="color: #0033a0; margin: 0 0 5px 0;">{row['Nama_Agen']}</h4>
                        <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px;">⭐ {rating_agen}</div>
                        <a href="{url_maps}" target="_blank" style="display: block; padding: 10px; background-color: #ed1c24; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            📍 BUKA DI GOOGLE MAPS
                        </a>
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[row[kolom_lat], row[kolom_lon]],
                        radius=8,
                        color="white", weight=2, fill=True, fill_color="#0033a0", fill_opacity=1.0,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"Klik untuk detail: {row['Nama_Agen']}"
                    ).add_to(m)
                
                st_folium(m, use_container_width=True, height=450, returned_objects=[])
            else:
                st.warning("Titik koordinat tidak ditemukan atau formatnya salah pada Spreadsheet.")

        # ================= KOLOM KANAN =================
        with col3:
            st.markdown("<div class='metric-label' style='margin-bottom:10px;'>RATA-RATA RATING PER KATEGORI</div>", unsafe_allow_html=True)
            
            df_bar = df_filtered.drop_duplicates(subset=["Nama_Agen"]).groupby(kolom_kategori)[kolom_rating].mean().reset_index()
            df_bar = df_bar.sort_values(by=kolom_rating, ascending=True)
            
            fig_bar = px.bar(df_bar, x=kolom_rating, y=kolom_kategori, orientation='h', text=kolom_rating)
            fig_bar.update_traces(marker_color='#0033a0', texttemplate='<b>%{text:.1f}</b>', textposition='outside', cliponaxis=False)
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=40, t=10, b=0), xaxis_title=None, yaxis_title=None, height=220,
                xaxis=dict(showgrid=False, showticklabels=False), font=dict(family="Segoe UI", size=13)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("<div class='metric-label' style='margin-top:20px; margin-bottom:10px;'>SENTIMEN ULASAN PELANGGAN</div>", unsafe_allow_html=True)
            
            kolom_teks = next((c for c in df.columns if "teks" in c.lower() or "ulasan" in c.lower() and c != kolom_total_ulasan), None)
            
            if kolom_teks and not df_filtered[kolom_teks].dropna().empty:
                semua_kata = []
                for ulasan in df_filtered[kolom_teks].dropna():
                    semua_kata.extend(ekstrak_kata_penting(ulasan))
                    
                if semua_kata:
                    wordcloud = WordCloud(
                        width=600, height=350, background_color="#f4f7f6", colormap="Set1", max_words=100
                    ).generate(" ".join(semua_kata))
                    
                    fig_wc, ax = plt.subplots(figsize=(6, 3.5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis("off")
                    fig_wc.patch.set_facecolor('#f4f7f6')
                    st.pyplot(fig_wc)
                else:
                    st.info("Kata ulasan terlalu pendek untuk dianalisis.")
            else:
                st.info("Tidak ada teks ulasan untuk ditampilkan.")

    except Exception as e:
        st.error(f"Gagal memuat data. Pastikan format kolom Spreadsheet benar. Error: {e}")

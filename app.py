import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import calendar

st.set_page_config(page_title="KPI Productivity Tracking", layout="wide")

# --- HELPER: MENCARI SITE ID & SITE NAME OTOMATIS ---
def extract_site_info(df):
    site_id = "N/A"
    site_name = "N/A"
    # Cari berdasarkan nama kolom (header)
    for col in df.columns:
        col_name = str(col).lower()
        if 'site id' in col_name or 'site_id' in col_name:
            site_id = df[col]
        elif 'site name' in col_name or 'nama site' in col_name:
            site_name = df[col]
    return site_id, site_name

# --- DATA PROCESSOR BERDASARKAN NAMA FILE ---
def process_uploaded_file(file):
    filename = file.name.lower()
    try:
        df = pd.read_excel(file)
    except Exception as e:
        st.error(f"Gagal membaca file {file.name}: {e}")
        return pd.DataFrame()

    # Pastikan jumlah kolom mencukupi sebelum memproses index (A=0, B=1, C=2... AH=33)
    if df.empty: return pd.DataFrame()
    
    site_id, site_name = extract_site_info(df)
    result_df = pd.DataFrame()

    # 1. TICKET SWFM (BPS/TS)
    if filename.startswith("ticket_swfm"):
        if df.shape[1] > 13:
            ticket = df.iloc[:, 2]  # C
            nama = df.iloc[:, 11]   # L
            tanggal = df.iloc[:, 12] # M
            checkin = df.iloc[:, 13] # N
            takeover = df.iloc[:, 12] # M (Take Over Date)
            
            # Validasi: Jika M atau N terisi, hitung sebagai tiket
            valid_mask = checkin.notna() | takeover.notna()
            
            result_df = pd.DataFrame({
                'Source': 'Ticket SWFM',
                'Ticket ID': ticket[valid_mask],
                'Nama PIC': nama[valid_mask],
                'Tanggal': tanggal[valid_mask],
                'Status Validasi': 'Visit / Take Over',
                'Site ID': site_id[valid_mask] if isinstance(site_id, pd.Series) else site_id,
                'Site Name': site_name[valid_mask] if isinstance(site_name, pd.Series) else site_name
            })

    # 2. PM SITE (PMS)
    elif filename.startswith("pm site"):
        if df.shape[1] > 15:
            ticket = df.iloc[:, 4]   # E
            status = df.iloc[:, 13]  # N
            tanggal = df.iloc[:, 14] # O
            nama = df.iloc[:, 15]    # P
            
            valid_status = ['waiting approval amesty', 'submitted', 'closed']
            valid_mask = status.astype(str).str.lower().isin(valid_status)
            
            result_df = pd.DataFrame({
                'Source': 'PM Site',
                'Ticket ID': ticket[valid_mask],
                'Nama PIC': nama[valid_mask],
                'Tanggal': tanggal[valid_mask],
                'Status Validasi': status[valid_mask],
                'Site ID': site_id[valid_mask] if isinstance(site_id, pd.Series) else site_id,
                'Site Name': site_name[valid_mask] if isinstance(site_name, pd.Series) else site_name
            })

    # 3. PM GENSET (PMG)
    elif filename.startswith("pm genset"):
        if df.shape[1] > 16:
            ticket = df.iloc[:, 4]   # E
            status = df.iloc[:, 14]  # O
            tanggal = df.iloc[:, 15] # P
            nama = df.iloc[:, 16]    # Q
            
            valid_status = ['waiting approval amesty', 'submitted', 'closed']
            valid_mask = status.astype(str).str.lower().isin(valid_status)
            
            result_df = pd.DataFrame({
                'Source': 'PM Genset',
                'Ticket ID': ticket[valid_mask],
                'Nama PIC': nama[valid_mask],
                'Tanggal': tanggal[valid_mask],
                'Status Validasi': status[valid_mask],
                'Site ID': site_id[valid_mask] if isinstance(site_id, pd.Series) else site_id,
                'Site Name': site_name[valid_mask] if isinstance(site_name, pd.Series) else site_name
            })

    # 4. EXPORT LIST TICKET FIELD OPERATION (PNA)
    elif filename.startswith("export list ticket"):
        if df.shape[1] > 33:
            ticket = df.iloc[:, 2]   # Asumsi C untuk Ticket ID (karena tidak disebutkan)
            tanggal = df.iloc[:, 26] # AA
            nama = df.iloc[:, 27]    # AB
            status = df.iloc[:, 33]  # AH
            
            valid_mask = status.astype(str).str.lower() == 'closed'
            
            result_df = pd.DataFrame({
                'Source': 'Field Operation (PNA)',
                'Ticket ID': ticket[valid_mask],
                'Nama PIC': nama[valid_mask],
                'Tanggal': tanggal[valid_mask],
                'Status Validasi': status[valid_mask],
                'Site ID': site_id[valid_mask] if isinstance(site_id, pd.Series) else site_id,
                'Site Name': site_name[valid_mask] if isinstance(site_name, pd.Series) else site_name
            })
            
    return result_df

# --- UI DASHBOARD ---
st.title("📊 Master KPI & Productivity Tracker")

with st.sidebar:
    st.header("📂 Auto-Detect Upload")
    st.info("Upload seluruh file sekaligus. Sistem akan mendeteksi dari awalan nama file:\n- Ticket_SWFM...\n- PM Site...\n- PM Genset...\n- Export List Ticket...")
    uploaded_files = st.file_uploader("Upload File Excel", type=['xlsx', 'xls'], accept_multiple_files=True)
    
    st.markdown("---")
    st.subheader("Parameter Harian")
    current_day = st.number_input("Tanggal Berjalan (Target Harian)", min_value=1, max_value=31, value=datetime.now().day)

# --- PEMROSESAN UTAMA ---
master_data = pd.DataFrame()

if uploaded_files:
    dataframes = []
    for f in uploaded_files:
        processed_df = process_uploaded_file(f)
        if not processed_df.empty:
            dataframes.append(processed_df)
    
    if dataframes:
        master_data = pd.concat(dataframes, ignore_index=True)
        # Cleansing format tanggal
        master_data['Tanggal'] = pd.to_datetime(master_data['Tanggal'], errors='coerce')
        master_data['Bulan-Tahun'] = master_data['Tanggal'].dt.to_period('M')
        master_data = master_data.dropna(subset=['Nama PIC']) # Buang baris jika PIC kosong

if master_data.empty:
    st.warning("Silakan upload data Excel yang valid untuk melihat analisis performa.")
else:
    # --- KALKULASI HARIAN (CURRENT METRICS) ---
    # Ambil bulan terakhir di dataset sebagai "Bulan Berjalan"
    current_month_period = master_data['Bulan-Tahun'].max()
    df_current_month = master_data[master_data['Bulan-Tahun'] == current_month_period]
    
    daily_stats = df_current_month.groupby('Nama PIC').size().reset_index(name='Total Tiket Bulan Ini')
    daily_stats['Rasio Harian'] = daily_stats['Total Tiket Bulan Ini'] / current_day
    
    def get_daily_status(ratio):
        if ratio == 0: return "Zero (0)"
        elif ratio < 0.2: return "Very Poor"
        elif ratio < 1.0: return "Poor"
        else: return "Good"
        
    daily_stats['Kategori Harian'] = daily_stats['Rasio Harian'].apply(get_daily_status)

    # --- KALKULASI HISTORIS 4 BULAN (4-MONTH PERFORMANCE) ---
    monthly_counts = master_data.groupby(['Nama PIC', 'Bulan-Tahun']).size().reset_index(name='Tickets')
    
    # Hitung rasio bulanan (Tiket / Jumlah Hari dalam Bulan tersebut)
    def calculate_month_ratio(row):
        year, month = row['Bulan-Tahun'].year, row['Bulan-Tahun'].month
        days_in_month = calendar.monthrange(year, month)[1]
        return row['Tickets'] / days_in_month

    monthly_counts['Rasio Bulanan'] = monthly_counts.apply(calculate_month_ratio, axis=1)
    monthly_counts['Is_Good'] = monthly_counts['Rasio Bulanan'] >= 1.0

    # Evaluasi 4 bulan terakhir
    last_4_months = sorted(master_data['Bulan-Tahun'].dropna().unique())[-4:]
    df_last_4m = monthly_counts[monthly_counts['Bulan-Tahun'].isin(last_4_months)]
    
    historical_eval = df_last_4m.groupby('Nama PIC').agg(
        Total_Bulan_Aktif=('Bulan-Tahun', 'count'),
        Bulan_Good_Ratio=('Is_Good', 'sum')
    ).reset_index()

    def evaluate_4m_performance(row):
        # Good performance jika rasio > 1 sebanyak 3 atau 4 kali dari 4 bulan terakhir
        if row['Bulan_Good_Ratio'] >= 3:
            return "🌟 Good Performance"
        else:
            return "⚠️ Warning / Bad Performance"

    historical_eval['Kinerja 4 Bulan'] = historical_eval.apply(evaluate_4m_performance, axis=1)

    # --- TABS LAYOUT ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Rasio Harian", "📈 Historis 4 Bulan", "🗄️ Master Data & Export", "💬 Broadcast WA"])

    with tab1:
        st.subheader(f"Performa Harian (Bulan: {current_month_period}) - Target Rasio 1.0 di Tanggal {current_day}")
        
        col_chart, col_data = st.columns([2, 1])
        with col_chart:
            fig = px.bar(daily_stats, x='Nama PIC', y='Rasio Harian', color='Kategori Harian',
                         color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'})
            fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Target Aman")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_data:
            st.dataframe(daily_stats[['Nama PIC', 'Total Tiket Bulan Ini', 'Rasio Harian']].style.format({'Rasio Harian': "{:.2f}"}), use_container_width=True)

    with tab2:
        st.subheader("Evaluasi Kinerja Jangka Panjang (4 Bulan Terakhir)")
        st.markdown(f"**Bulan yang dievaluasi:** {', '.join([str(m) for m in last_4_months])}")
        
        # Pivot untuk memperlihatkan trend per bulan
        pivot_trend = df_last_4m.pivot(index='Nama PIC', columns='Bulan-Tahun', values='Rasio Bulanan').fillna(0)
        eval_merged = pd.merge(pivot_trend, historical_eval[['Nama PIC', 'Kinerja 4 Bulan']], on='Nama PIC', how='left')
        
        st.dataframe(eval_merged.style.format(precision=2), use_container_width=True)

    with tab3:
        st.subheader("Master Data Rangkuman")
        st.write("Semua data yang berhasil difilter dan divalidasi dari 4 file yang di-upload.")
        st.dataframe(master_data, use_container_width=True)
        
        # EXPORT TO EXCEL
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            master_data.to_excel(writer, index=False, sheet_name='Master Data')
            eval_merged.to_excel(writer, index=False, sheet_name='Evaluasi 4 Bulan')
        
        st.download_button(
            label="📥 Download Data Gabungan (Excel)",
            data=output.getvalue(),
            file_name=f"Master_KPI_Data_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with tab4:
        st.subheader("Draft Broadcast WhatsApp Harian")
        waktu = datetime.now().strftime("%H:%00 WIB")
        
        txt = f"📢 *UPDATE TICKETING PRODUCTIVITY* 📢\n"
        txt += f"📅 Tanggal: {datetime.now().strftime('%d %b %Y')}\n"
        txt += f"🎯 Target Hari Ini: {current_day} Tiket (Rasio 1.0)\n\n"
        
        need_attention = daily_stats[daily_stats['Kategori Harian'] != 'Good'].sort_values('Rasio Harian')
        
        if need_attention.empty:
            txt += "✅ *Semua tim mencapai target rasio 1.0 hari ini!* Pertahankan.\n"
        else:
            txt += "🚨 *STATUS: NOT SAFE (Rasio < 1.0)* 🚨\nSegera lengkapi tiket harian Anda:\n\n"
            for _, row in need_attention.iterrows():
                sisa = current_day - row['Total Tiket Bulan Ini']
                sisa = sisa if sisa > 0 else 0
                txt += f"▪️ @{row['Nama PIC'].replace(' ', '')} - {row['Kategori Harian'].upper()}\n"
                txt += f"   Total Tiket: {row['Total Tiket Bulan Ini']} | Rasio: {row['Rasio Harian']:.2f}\n"
                txt += f"   Butuh: {sisa} tiket lagi.\n\n"
                
        st.text_area("Copy Teks Broadcast:", value=txt, height=350)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import calendar

st.set_page_config(page_title="Productivity Tracking", layout="wide")

# --- HELPER FUNCTIONS ---
def calculate_ratio(total_tickets, target_days):
    if target_days == 0: return 0
    return total_tickets / target_days

def get_daily_status(daily_tickets):
    if daily_tickets == 0:
        return "🔴 0 ticketing"
    elif daily_tickets == 1:
        return "🟡 Not safe, need more ticket"
    else:
        return "🟢 Safe, waiting next ticket"

def get_productivity_category(ratio):
    if ratio >= 1.0: return "Good"
    elif 0.2 <= ratio < 1.0: return "Poor"
    elif 0 < ratio < 0.2: return "Very Poor"
    else: return "Zero"

# --- LOGIKA AUTO-DETECT KOLOM NAMA & TANGGAL ---
def auto_detect_pic_column(df):
    if df is None or df.empty: return None
    keywords = ['nama', 'pic', 'teknisi', 'petugas', 'engineer', 'pelaksana', 'resource', 'assignee', 'user submitter']
    for col in df.columns:
        if any(kw in str(col).lower() for kw in keywords): return col
    for col in df.columns:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str)
            if not sample.empty:
                avg_len = sample.apply(len).mean()
                if 3 <= avg_len <= 30: return col
    return None

def get_date_col(df, known_cols):
    for col in df.columns:
        if str(col).strip().lower() in known_cols: return col
    return None

# --- DATA PROCESSORS (MENGEMBALIKAN RAW DATA) ---
def process_ticketing_bps_ts(df, source_name):
    if df is not None and not df.empty:
        name_col = auto_detect_pic_column(df)
        if not name_col:
            return pd.DataFrame()
            
        date_col = get_date_col(df, ['take over date', 'created at', 'check in at'])
        check_in_col = next((c for c in df.columns if 'check in' in str(c).lower()), None)
        take_over_col = next((c for c in df.columns if 'take over' in str(c).lower()), None)
        
        # Validasi
        if check_in_col and take_over_col:
            valid_df = df[df[check_in_col].notna() | df[take_over_col].notna()].copy()
        else:
            valid_df = df.copy()
            
        if not valid_df.empty:
            valid_df = valid_df.rename(columns={name_col: 'Nama PIC'})
            valid_df['Tanggal'] = pd.to_datetime(valid_df[date_col], errors='coerce') if date_col else pd.NaT
            valid_df['Source'] = source_name
            return valid_df[['Nama PIC', 'Tanggal', 'Source']]
    return pd.DataFrame()

def process_general_status(df, source_name, target_status):
    if df is not None and not df.empty:
        name_col = auto_detect_pic_column(df)
        if not name_col:
            return pd.DataFrame()
            
        date_col = get_date_col(df, ['submitted date', 'submit time', 'created date', 'created at'])
        status_col = next((col for col in df.columns if 'status' in str(col).lower()), None)
        
        if status_col:
            if source_name in ["PMS", "PMG"]:
                valid_status = ['waiting approval amesty', 'submitted', 'closed']
                valid_df = df[df[status_col].astype(str).str.lower().isin(valid_status)].copy()
            else:
                valid_df = df[df[status_col].astype(str).str.lower() == target_status.lower()].copy()
        else:
            valid_df = df.copy()
            
        if not valid_df.empty:
            valid_df = valid_df.rename(columns={name_col: 'Nama PIC'})
            valid_df['Tanggal'] = pd.to_datetime(valid_df[date_col], errors='coerce') if date_col else pd.NaT
            valid_df['Source'] = source_name
            return valid_df[['Nama PIC', 'Tanggal', 'Source']]
    return pd.DataFrame()

# --- UI DASHBOARD ---
st.title("📊 Productivity Ticketing Dashboard & Matrix")

with st.sidebar:
    st.header("📂 Upload 4 File Data")
    
    file_ticketing = st.file_uploader("1. Upload File Ticketing (BPS & TS)", type=['xlsx', 'csv'])
    file_pms = st.file_uploader("2. Upload File PMS", type=['xlsx', 'csv'])
    file_pmg = st.file_uploader("3. Upload File PMG", type=['xlsx', 'csv'])
    file_pna = st.file_uploader("4. Upload File PNA", type=['xlsx', 'csv'])
    
    st.markdown("---")
    st.header("⚙️ Parameter Rentang Waktu")
    
    today = datetime.now()
    first_day = today.replace(day=1)
    date_range = st.date_input("Rentang Waktu Tiket", value=(first_day, today))
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        target_days = (date_range[1] - date_range[0]).days + 1
    else:
        target_days = 1
        
    st.info(f"🎯 Target Hari Evaluasi = {target_days} Hari")
    
    st.markdown("---")
    kategori_options = ["Good", "Poor", "Very Poor", "Zero"]
    kategori_filter = st.multiselect("Filter Kategori (Untuk Tab 1 & 3)", options=kategori_options, default=kategori_options)

# --- PROSES PENGGABUNGAN RAW DATA ---
raw_data_list = []

if file_ticketing: raw_data_list.append(process_ticketing_bps_ts(pd.read_excel(file_ticketing), "Ticketing (BPS & TS)"))
if file_pms: raw_data_list.append(process_general_status(pd.read_excel(file_pms), "PMS", "submit"))
if file_pmg: raw_data_list.append(process_general_status(pd.read_excel(file_pmg), "PMG", "submit"))
if file_pna: raw_data_list.append(process_general_status(pd.read_excel(file_pna), "PNA", "close"))

if not raw_data_list:
    st.info("Silakan upload minimal 1 file Excel dari menu di samping kiri untuk melihat data sebenarnya.")
    df_raw = pd.DataFrame(columns=['Nama PIC', 'Tanggal', 'Source'])
else:
    df_raw = pd.concat(raw_data_list, ignore_index=True)
    df_raw = df_raw.dropna(subset=['Nama PIC'])

# --- TABS LAYOUT ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Analisa Rentang Waktu", "📅 Matriks Performa Bulanan", "💬 WA Broadcast Generator", "🗄️ Raw Data & Export"])

if not df_raw.empty:
    
    # === DATA PREP TAB 1 (FILTER RENTANG WAKTU) ===
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1]).replace(hour=23, minute=59, second=59)
    df_filtered_date = df_raw[(df_raw['Tanggal'] >= start_date) & (df_raw['Tanggal'] <= end_date)]
    
    df_master = df_filtered_date.groupby('Nama PIC').size().reset_index(name='Tickets')
    df_master['Daily_Tickets'] = 1 
    
    # Ambil PIC yang tiketnya 0 di rentang waktu tersebut
    all_pics = df_raw['Nama PIC'].unique()
    missing_pics = set(all_pics) - set(df_master['Nama PIC'].unique())
    if missing_pics:
        df_missing = pd.DataFrame({'Nama PIC': list(missing_pics), 'Tickets': 0, 'Daily_Tickets': 0})
        df_master = pd.concat([df_master, df_missing], ignore_index=True)

    df_master['Ratio'] = df_master['Tickets'].apply(lambda x: calculate_ratio(x, target_days))
    df_master['Status Harian'] = df_master['Daily_Tickets'].apply(get_daily_status)
    df_master['Kategori Produktivitas'] = df_master['Ratio'].apply(get_productivity_category)
    df_master['Sisa Target'] = df_master['Tickets'].apply(lambda x: target_days - x if x < target_days else 0)

    if kategori_filter:
        df_master = df_master[df_master['Kategori Produktivitas'].isin(kategori_filter)]

    # === TAB 1: DASHBOARD UTAMA ===
    with tab1:
        st.subheader(f"Performa Rentang Waktu (Target: {target_days} Hari)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total PIC Ditampilkan", len(df_master))
        col2.metric("Good Productivity", len(df_master[df_master['Kategori Produktivitas'] == 'Good']))
        col3.metric("Warning (Zero/Very Poor)", len(df_master[df_master['Kategori Produktivitas'].isin(['Zero', 'Very Poor'])]))
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns([2,1])
        with col_chart1:
            if not df_master.empty:
                fig_bar = px.bar(df_master.sort_values('Ratio', ascending=False), x='Nama PIC', y='Ratio', color='Kategori Produktivitas',
                                 color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'})
                fig_bar.add_hline(y=1.0, line_dash="dash", annotation_text="Target Rasio 1.0", line_color="red")
                st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.dataframe(df_master[['Nama PIC', 'Tickets', 'Ratio', 'Kategori Produktivitas']].style.format({'Ratio': "{:.2f}"}), use_container_width=True)

    # === TAB 2: MATRIKS PERFORMA BULANAN (LIKE IMAGE) ===
    with tab2:
        st.subheader("Matriks Rasio Produktivitas Bulanan")
        
        # Ekstrak Bulan & Hitung Kapasitas Hari per Bulan
        df_matrix_raw = df_raw.dropna(subset=['Tanggal']).copy()
        df_matrix_raw['Bulan'] = df_matrix_raw['Tanggal'].dt.strftime('%b-%y')
        df_matrix_raw['Bulan_Sort'] = df_matrix_raw['Tanggal'].dt.to_period('M')
        
        # Hitung jumlah hari dalam bulan tersebut untuk pembagi rasio
        df_matrix_raw['DaysInMonth'] = df_matrix_raw['Tanggal'].dt.daysinmonth
        
        # Pivot agregasi
        monthly_tickets = df_matrix_raw.groupby(['Nama PIC', 'Bulan_Sort', 'Bulan', 'DaysInMonth']).size().reset_index(name='Tickets')
        monthly_tickets['Ratio'] = monthly_tickets['Tickets'] / monthly_tickets['DaysInMonth']
        
        matrix_pivot = monthly_tickets.pivot(index='Nama PIC', columns='Bulan_Sort', values='Ratio').fillna(0)
        
        # Ambil 4 bulan terakhir (jika ada)
        available_months = sorted(matrix_pivot.columns)
        last_4_months = available_months[-4:] if len(available_months) >= 4 else available_months
        
        matrix_display = matrix_pivot[last_4_months].copy()
        
        # Hitung Remark (Good jika >= 1.0 minimal 3/4 dari bulan yang dievaluasi)
        threshold_good = 3 if len(last_4_months) == 4 else (len(last_4_months) - 1 if len(last_4_months) > 1 else 1)
        
        def calculate_remark(row):
            good_months = sum(row >= 1.0)
            return "Good" if good_months >= threshold_good else "Bad"
            
        matrix_display['Remark'] = matrix_display.apply(calculate_remark, axis=1)
        
        # Ubah nama kolom agar rapi (Jun-26, Jul-26, dst)
        rename_cols = {col: col.strftime('%b-%y') for col in last_4_months}
        matrix_display = matrix_display.rename(columns=rename_cols)
        month_str_cols = list(rename_cols.values())

        # Styling Dataframe mirip gambar
        def style_matrix(val):
            if isinstance(val, str):
                if val == 'Good': return 'background-color: #5cb85c; color: white; font-weight: bold'
                elif val == 'Bad': return 'background-color: #e9967a; color: white; font-weight: bold'
                return ''
            if val >= 1.0: return 'background-color: #5cb85c; color: white' # Hijau
            elif val >= 0.2: return 'background-color: #f0ad4e; color: white' # Kuning
            else: return 'background-color: #d9534f; color: white' # Merah

        # Tambahkan Filter PIC untuk matrix
        search_pic = st.text_input("🔍 Cari Nama PIC (Kosongkan untuk tampil semua)")
        if search_pic:
            matrix_display = matrix_display[matrix_display.index.str.contains(search_pic, case=False, na=False)]

        st.dataframe(matrix_display.style.map(style_matrix).format({col: "{:.2f}" for col in month_str_cols}), use_container_width=True, height=600)

    # === TAB 3: WA BROADCAST ===
    with tab3:
        st.subheader(f"Generate Broadcast (Berdasarkan Target {target_days} Hari)")
        waktu = datetime.now().strftime("%H:%00 WIB")
        
        txt = f"📢 *UPDATE TICKETING PRODUCTIVITY* 📢\n"
        txt += f"📅 Tanggal: {datetime.now().strftime('%d %b %Y')}\n"
        txt += f"⏰ Waktu: {waktu}\n"
        txt += f"🎯 Target Rentang Evaluasi: {target_days} Tiket (Rasio 1.0)\n\n"
        
        need_attention = df_master[df_master['Kategori Produktivitas'].isin(['Zero', 'Very Poor', 'Poor'])].sort_values('Ratio')
        
        if need_attention.empty:
            txt += "✅ *Luar biasa! Semua tim berada di rasio Good (Rasio >= 1.0).* Pertahankan!\n"
        else:
            txt += "🚨 *PERLU PERHATIAN KHUSUS (Status: Not Safe / Warning)* 🚨\nHarap selesaikan tiket untuk memperbaiki rasio produktivitas Anda:\n\n"
            for index, row in need_attention.iterrows():
                tag_name = f"@{row['Nama PIC'].replace(' ', '')}"
                txt += f"▪️ {tag_name} - *{row['Kategori Produktivitas'].upper()}*\n"
                txt += f"   Total Tiket: {row['Tickets']} | Rasio: {row['Ratio']:.2f}\n"
                txt += f"   *Butuh {row['Sisa Target']} tiket lagi* untuk rasio aman (1.0).\n\n"
                
        st.text_area("Copy Teks di Bawah Ini:", value=txt, height=400)

    # === TAB 4: MASTER RAW DATA EXPORT ===
    with tab4:
        st.subheader("🗄️ Database Siap Sharing (Raw Data)")
        st.write("Tabel di bawah adalah gabungan seluruh data tiket valid dari file yang di-upload.")
        
        col_f1, col_f2 = st.columns(2)
        filter_source = col_f1.multiselect("Filter Sumber Data", options=df_raw['Source'].unique(), default=df_raw['Source'].unique())
        filter_nama = col_f2.text_input("Filter Nama PIC di Database Mentah")
        
        # Apply filter
        df_export = df_raw.copy()
        if filter_source:
            df_export = df_export[df_export['Source'].isin(filter_source)]
        if filter_nama:
            df_export = df_export[df_export['Nama PIC'].str.contains(filter_nama, case=False, na=False)]
            
        # Format Tanggal
        df_export['Tanggal'] = df_export['Tanggal'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(df_export, use_container_width=True)
        
        # Download Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Master Data')
            matrix_display.reset_index().to_excel(writer, index=False, sheet_name='Matriks Bulanan')
            
        st.download_button(
            label="📥 Download Database ke Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Master_Ticketing_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

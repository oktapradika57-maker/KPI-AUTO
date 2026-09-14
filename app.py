import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import calendar

st.set_page_config(page_title="Productivity & KPI Tracking", layout="wide")

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

# --- CACHED PROCESSORS UNTUK MASING-MASING FILE ---
@st.cache_data(show_spinner=False)
def process_swfm_file(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if df.empty: return pd.DataFrame()
        
        ticket = df['Ticket Number SWFM'] if 'Ticket Number SWFM' in df.columns else df.iloc[:, 1]
        site_id = df['Site Id'] if 'Site Id' in df.columns else df.iloc[:, 4]
        site_name = df['Site Name'] if 'Site Name' in df.columns else df.iloc[:, 5]
        pic = df['PIC Take Over Ticket'] if 'PIC Take Over Ticket' in df.columns else df.iloc[:, 17]
        take_over = df['Take Over Date'] if 'Take Over Date' in df.columns else df.iloc[:, 35]
        check_in = df['Check In At'] if 'Check In At' in df.columns else df.iloc[:, 36]
        
        valid_mask = take_over.notna() | check_in.notna()
        sub = pd.DataFrame({
            'Source': 'TS/BPS',
            'Ticket ID': ticket[valid_mask],
            'Site ID': site_id[valid_mask],
            'Site Name': site_name[valid_mask],
            'Nama PIC': pic[valid_mask],
            'Status': 'Visit / Take Over',
            'Take Over Date': take_over[valid_mask],
            'Check In At': check_in[valid_mask],
            'Tanggal Utama': take_over[valid_mask].fillna(check_in[valid_mask])
        })
        return sub
    except Exception as e:
        st.error(f"Error pembacaan Ticket SWFM: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def process_pms_file(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if df.empty: return pd.DataFrame()
        
        ticket = df['Ticket No'] if 'Ticket No' in df.columns else df.iloc[:, 4]
        site_id = df['Site'] if 'Site' in df.columns else df.iloc[:, 5]
        site_name = df['Site Name'] if 'Site Name' in df.columns else df.iloc[:, 6]
        status = df['Status'] if 'Status' in df.columns else df.iloc[:, 13]
        tanggal = df['Submitted Date'] if 'Submitted Date' in df.columns else df.iloc[:, 14]
        pic = df['PIC'] if 'PIC' in df.columns else df.iloc[:, 15]
        
        valid_status = ['waiting approval amesty', 'submitted', 'closed']
        valid_mask = status.astype(str).str.lower().isin(valid_status)
        sub = pd.DataFrame({
            'Source': 'PMS',
            'Ticket ID': ticket[valid_mask],
            'Site ID': site_id[valid_mask],
            'Site Name': site_name[valid_mask],
            'Nama PIC': pic[valid_mask],
            'Status': status[valid_mask],
            'Take Over Date': pd.NaT,
            'Check In At': pd.NaT,
            'Tanggal Utama': tanggal[valid_mask]
        })
        return sub
    except Exception as e:
        st.error(f"Error pembacaan PM Site: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def process_pmg_file(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if df.empty: return pd.DataFrame()
        
        ticket = df['Ticket No'] if 'Ticket No' in df.columns else df.iloc[:, 4]
        site_id = df['Site'] if 'Site' in df.columns else df.iloc[:, 5]
        site_name = df['Site Name'] if 'Site Name' in df.columns else df.iloc[:, 6]
        status = df['Status'] if 'Status' in df.columns else df.iloc[:, 14]
        tanggal = df['Submitted Date'] if 'Submitted Date' in df.columns else df.iloc[:, 15]
        pic = df['PIC'] if 'PIC' in df.columns else df.iloc[:, 16]
        
        valid_status = ['waiting approval amesty', 'submitted', 'closed']
        valid_mask = status.astype(str).str.lower().isin(valid_status)
        sub = pd.DataFrame({
            'Source': 'PMG',
            'Ticket ID': ticket[valid_mask],
            'Site ID': site_id[valid_mask],
            'Site Name': site_name[valid_mask],
            'Nama PIC': pic[valid_mask],
            'Status': status[valid_mask],
            'Take Over Date': pd.NaT,
            'Check In At': pd.NaT,
            'Tanggal Utama': tanggal[valid_mask]
        })
        return sub
    except Exception as e:
        st.error(f"Error pembacaan PM Genset: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def process_fna_file(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if df.empty: return pd.DataFrame()
        
        ticket = df['No ticket'] if 'No ticket' in df.columns else df.iloc[:, 0]
        site_id = df['Site'] if 'Site' in df.columns else df.iloc[:, 1]
        site_name = df['Site name'] if 'Site name' in df.columns else df.iloc[:, 2]
        status = df['Status'] if 'Status' in df.columns else df.iloc[:, 33]
        tanggal = df['Submit time'] if 'Submit time' in df.columns else df.iloc[:, 26]
        pic = df['User submitter'] if 'User submitter' in df.columns else df.iloc[:, 27]
        checkin_time = df['Checkin time'] if 'Checkin time' in df.columns else df.iloc[:, 23]
        
        valid_mask = status.astype(str).str.lower() == 'closed'
        sub = pd.DataFrame({
            'Source': 'FNA',
            'Ticket ID': ticket[valid_mask],
            'Site ID': site_id[valid_mask],
            'Site Name': site_name[valid_mask],
            'Nama PIC': pic[valid_mask],
            'Status': status[valid_mask],
            'Take Over Date': pd.NaT,
            'Check In At': checkin_time[valid_mask],
            'Tanggal Utama': tanggal[valid_mask]
        })
        return sub
    except Exception as e:
        st.error(f"Error pembacaan Export List Ticket (FNA): {e}")
        return pd.DataFrame()

# --- UI DASHBOARD ---
st.title("📊 Master Productivity & KPI Tracker")

with st.sidebar:
    st.header("📂 Upload 4 File Utama")
    
    file_swfm = st.file_uploader("1. Ticket_SWFM (TS & BPS)", type=['xlsx', 'xls'])
    file_pms = st.file_uploader("2. PM Site", type=['xlsx', 'xls'])
    file_pmg = st.file_uploader("3. PM Genset", type=['xlsx', 'xls'])
    file_fna = st.file_uploader("4. Export List Ticket Field Operation (FNA)", type=['xlsx', 'xls'])
    
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
    kategori_filter = st.multiselect("Filter Kategori (Tab 1 & 3)", options=kategori_options, default=kategori_options)

# --- PROSES PENGGABUNGAN RAW DATA ---
raw_data_list = []

if file_swfm: raw_data_list.append(process_swfm_file(file_swfm.getvalue()))
if file_pms: raw_data_list.append(process_pms_file(file_pms.getvalue()))
if file_pmg: raw_data_list.append(process_pmg_file(file_pmg.getvalue()))
if file_fna: raw_data_list.append(process_fna_file(file_fna.getvalue()))

if not raw_data_list:
    st.warning("⚠️ Silakan upload file Excel pada menu di sidebar kiri (TS/BPS, PMS, PMG, FNA) untuk melihat data.")
    df_raw = pd.DataFrame(columns=['Source', 'Ticket ID', 'Site ID', 'Site Name', 'Nama PIC', 'Status', 'Take Over Date', 'Check In At', 'Tanggal Utama'])
else:
    df_raw = pd.concat(raw_data_list, ignore_index=True)
    df_raw['Tanggal Utama'] = pd.to_datetime(df_raw['Tanggal Utama'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Nama PIC'])

# --- TABS LAYOUT ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Analisa Rentang Waktu", "📅 Matriks Performa Bulanan", "💬 WA Broadcast", "🗄️ Raw Data & Export"])

if not df_raw.empty:
    
    # === DATA PREP TAB 1 (FILTER RENTANG WAKTU) ===
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1]).replace(hour=23, minute=59, second=59)
    df_filtered_date = df_raw[(df_raw['Tanggal Utama'] >= start_date) & (df_raw['Tanggal Utama'] <= end_date)]
    
    df_master = df_filtered_date.groupby('Nama PIC').size().reset_index(name='Tickets')
    df_master['Daily_Tickets'] = 1 
    
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
                                 color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'},
                                 title="Rasio Produktivitas per PIC")
                fig_bar.add_hline(y=1.0, line_dash="dash", annotation_text="Target Rasio 1.0", line_color="red")
                st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.dataframe(df_master[['Nama PIC', 'Tickets', 'Ratio', 'Kategori Produktivitas']].style.format({'Ratio': "{:.2f}"}), use_container_width=True)

    # === TAB 2: MATRIKS PERFORMA BULANAN ===
    with tab2:
        st.subheader("Matriks Rasio Produktivitas Bulanan (4 Bulan Terakhir)")
        
        df_matrix_raw = df_raw.dropna(subset=['Tanggal Utama']).copy()
        df_matrix_raw['Bulan_Sort'] = df_matrix_raw['Tanggal Utama'].dt.to_period('M')
        df_matrix_raw['DaysInMonth'] = df_matrix_raw['Tanggal Utama'].dt.daysinmonth
        
        monthly_tickets = df_matrix_raw.groupby(['Nama PIC', 'Bulan_Sort', 'DaysInMonth']).size().reset_index(name='Tickets')
        monthly_tickets['Ratio'] = monthly_tickets['Tickets'] / monthly_tickets['DaysInMonth']
        
        matrix_pivot = monthly_tickets.pivot(index='Nama PIC', columns='Bulan_Sort', values='Ratio').fillna(0)
        
        available_months = sorted(matrix_pivot.columns)
        last_4_months = available_months[-4:] if len(available_months) >= 4 else available_months
        
        if last_4_months:
            matrix_display = matrix_pivot[last_4_months].copy()
            
            threshold_good = 3 if len(last_4_months) == 4 else (len(last_4_months) - 1 if len(last_4_months) > 1 else 1)
            
            def calculate_remark(row):
                good_months = sum(row >= 1.0)
                return "Good" if good_months >= threshold_good else "Bad"
                
            matrix_display['Remark'] = matrix_display.apply(calculate_remark, axis=1)
            
            rename_cols = {col: col.strftime('%b-%y') for col in last_4_months}
            matrix_display = matrix_display.rename(columns=rename_cols)
            month_str_cols = list(rename_cols.values())

            def style_matrix(val):
                if isinstance(val, str):
                    if val == 'Good': return 'background-color: #5cb85c; color: white; font-weight: bold'
                    elif val == 'Bad': return 'background-color: #e9967a; color: white; font-weight: bold'
                    return ''
                if val >= 1.0: return 'background-color: #5cb85c; color: white'
                elif val >= 0.2: return 'background-color: #f0ad4e; color: white'
                else: return 'background-color: #d9534f; color: white'

            search_pic = st.text_input("🔍 Cari Nama PIC pada Matriks")
            if search_pic:
                matrix_display = matrix_display[matrix_display.index.str.contains(search_pic, case=False, na=False)]

            st.dataframe(matrix_display.style.map(style_matrix).format({col: "{:.2f}" for col in month_str_cols}), use_container_width=True, height=600)
        else:
            st.info("Data tanggal belum mencukupi untuk membentuk matriks bulanan.")

    # === TAB 3: WA BROADCAST ===
    with tab3:
        st.subheader("Generate Broadcast WhatsApp")
        waktu = datetime.now().strftime("%H:%00 WIB")
        
        txt = f"📢 *UPDATE TICKETING PRODUCTIVITY* 📢\n"
        txt += f"📅 Tanggal: {datetime.now().strftime('%d %b %Y')}\n"
        txt += f"⏰ Waktu: {waktu}\n"
        txt += f"🎯 Target Rentang Evaluasi: {target_days} Hari (Rasio 1.0)\n\n"
        
        need_attention = df_master[df_master['Kategori Produktivitas'].isin(['Zero', 'Very Poor', 'Poor'])].sort_values('Ratio')
        
        if need_attention.empty:
            txt += "✅ *Luar biasa! Semua tim berada di rasio Good (Rasio >= 1.0).* Pertahankan!\n"
        else:
            txt += "🚨 *PERLU PERHATIAN KHUSUS (Status: Not Safe / Warning)* 🚨\nHarap selesaikan tiket untuk memperbaiki rasio produktivitas:\n\n"
            for index, row in need_attention.iterrows():
                tag_name = f"@{row['Nama PIC'].replace(' ', '')}"
                txt += f"▪️ {tag_name} - *{row['Kategori Produktivitas'].upper()}*\n"
                txt += f"   Total Tiket: {row['Tickets']} | Rasio: {row['Ratio']:.2f}\n"
                txt += f"   *Butuh {row['Sisa Target']} tiket lagi* untuk rasio aman (1.0).\n\n"
                
        st.text_area("Copy Teks Broadcast:", value=txt, height=400)

    # === TAB 4: RAW DATA & EXPORT ===
    with tab4:
        st.subheader("🗄️ Master Database Gabungan (TS/BPS, PMS, PMG, FNA)")
        st.write("Semua data berhasil digabungkan lengkap dengan informasi Site, Status, serta Tanggal Check-in/Take-over.")
        
        col_f1, col_f2 = st.columns(2)
        filter_source = col_f1.multiselect("Filter Sumber File", options=df_raw['Source'].unique(), default=df_raw['Source'].unique())
        filter_nama = col_f2.text_input("Cari Nama PIC di Database")
        
        df_export = df_raw.copy()
        if filter_source:
            df_export = df_export[df_export['Source'].isin(filter_source)]
        if filter_nama:
            df_export = df_export[df_export['Nama PIC'].str.contains(filter_nama, case=False, na=False)]
            
        df_export['Tanggal Utama'] = df_export['Tanggal Utama'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(df_export, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Master Raw Data')
            if 'matrix_display' in locals() and not matrix_display.empty:
                matrix_display.reset_index().to_excel(writer, index=False, sheet_name='Matriks Bulanan')
            
        st.download_button(
            label="📥 Download Master Database ke Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Master_KPI_All_Files_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

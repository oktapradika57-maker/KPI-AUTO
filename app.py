import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

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
    if ratio >= 1.0:
        return "Good"
    elif 0.2 <= ratio < 1.0:
        return "Poor"
    elif 0 < ratio < 0.2:
        return "Very Poor"
    else:
        return "Zero"

# --- LOGIKA AUTO-DETECT KOLOM NAMA & TANGGAL ---
def auto_detect_pic_column(df):
    if df is None or df.empty:
        return None
        
    # Prioritas utama: Cari dari nama header, ditambahkan 'user submitter' sesuai file Export List Ticket
    keywords = ['nama', 'pic', 'teknisi', 'petugas', 'engineer', 'pelaksana', 'resource', 'assignee', 'user submitter']
    for col in df.columns:
        if any(kw in str(col).lower() for kw in keywords):
            return col
            
    # Alternatif: Cari berdasarkan isi baris data (tipe Teks dengan panjang mirip nama orang)
    for col in df.columns:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str)
            if not sample.empty:
                avg_len = sample.apply(len).mean()
                if 3 <= avg_len <= 30:
                    return col
    return None

def get_date_col(df, known_cols):
    for col in df.columns:
        if str(col).strip().lower() in known_cols:
            return col
    return None

def filter_by_date(df, date_col, date_range):
    if date_col and len(date_range) == 2:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        start_date = pd.to_datetime(date_range[0])
        # Pastikan tiket yang terjadi hingga 23:59:59 di hari terakhir tetap terhitung
        end_date = pd.to_datetime(date_range[1]).replace(hour=23, minute=59, second=59)
        return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
    return df

# --- DATA PROCESSORS ---
def process_ticketing_bps_ts(df, source_name, date_range):
    if df is not None and not df.empty:
        name_col = auto_detect_pic_column(df)
        if not name_col:
            st.warning(f"⚠️ Tidak dapat mendeteksi kolom nama di file {source_name}.")
            return pd.DataFrame(columns=['Nama PIC', 'Tickets'])
            
        df = df.rename(columns={name_col: 'Nama PIC'})
        
        # Filter Tanggal (Deteksi otomatis Take Over Date atau Created At sesuai Excel aslinya)
        date_col = get_date_col(df, ['take over date', 'created at', 'check in at'])
        if date_col:
            df = filter_by_date(df, date_col, date_range)
        
        # Logika validasi BPS & TS
        check_in_col = next((c for c in df.columns if 'check in' in str(c).lower()), 'Check_In_Date')
        take_over_col = next((c for c in df.columns if 'take over' in str(c).lower()), 'Take_Over_Status')
        
        if check_in_col in df.columns and take_over_col in df.columns:
            # Karena Take Over Date di data asli formatnya tanggal, kita cukup cek apakah notna() (tidak kosong)
            valid_tickets = df[df[check_in_col].notna() | df[take_over_col].notna()]
            return valid_tickets.groupby('Nama PIC').size().reset_index(name='Tickets')
        else:
            return df.groupby('Nama PIC').size().reset_index(name='Tickets')
    return pd.DataFrame(columns=['Nama PIC', 'Tickets'])

def process_general_status(df, source_name, target_status, date_range):
    if df is not None and not df.empty:
        name_col = auto_detect_pic_column(df)
        if not name_col:
            st.warning(f"⚠️ Tidak dapat mendeteksi kolom nama di file {source_name}.")
            return pd.DataFrame(columns=['Nama PIC', 'Tickets'])
            
        df = df.rename(columns={name_col: 'Nama PIC'})
        
        # Filter Tanggal (Deteksi submitted date, submit time, dll)
        date_col = get_date_col(df, ['submitted date', 'submit time', 'created date', 'created at'])
        if date_col:
            df = filter_by_date(df, date_col, date_range)
        
        # Cari kolom status (Cari yang mengandung kata 'status')
        status_col = next((col for col in df.columns if 'status' in str(col).lower()), None)
        
        if status_col:
            # Tambahan validasi untuk file PM Site & Genset agar membaca ketiga status
            if source_name in ["PMS", "PMG"]:
                valid_status = ['waiting approval amesty', 'submitted', 'closed']
                valid_tickets = df[df[status_col].astype(str).str.lower().isin(valid_status)]
            else:
                valid_tickets = df[df[status_col].astype(str).str.lower() == target_status.lower()]
                
            return valid_tickets.groupby('Nama PIC').size().reset_index(name='Tickets')
        else:
            return df.groupby('Nama PIC').size().reset_index(name='Tickets')
    return pd.DataFrame(columns=['Nama PIC', 'Tickets'])

# --- UI DASHBOARD ---
st.title("📊 Productivity Ticketing Dashboard")

with st.sidebar:
    st.header("📂 Upload 4 File Data")
    
    file_ticketing = st.file_uploader("1. Upload File Ticketing (BPS & TS)", type=['xlsx', 'csv'])
    file_pms = st.file_uploader("2. Upload File PMS", type=['xlsx', 'csv'])
    file_pmg = st.file_uploader("3. Upload File PMG", type=['xlsx', 'csv'])
    file_pna = st.file_uploader("4. Upload File PNA", type=['xlsx', 'csv'])
    
    st.markdown("---")
    st.header("⚙️ Parameter & Filter")
    
    # 1. Filter Rentang Waktu (Menggantikan number input 'Tanggal Berjalan')
    today = datetime.now()
    first_day = today.replace(day=1)
    date_range = st.date_input("Rentang Waktu Tiket", value=(first_day, today))
    
    # Otomatis menghitung Target Tiket dari jumlah hari rentang tanggal (Contoh: Tgl 1 - 14 = 14 Hari Target)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        target_days = (date_range[1] - date_range[0]).days + 1
    else:
        target_days = 1
        
    st.info(f"🎯 Target Hari Evaluasi = {target_days} Hari")
    
    # 2. Filter Kategori Rasio
    kategori_options = ["Good", "Poor", "Very Poor", "Zero"]
    kategori_filter = st.multiselect("Filter Rasio Produktivitas", 
                                     options=kategori_options,
                                     default=kategori_options)

# --- PROSES PENGGABUNGAN DATA ---
data_list = []

# Proses membaca dan memfilter data berdasarkan rentang waktu pilihan user
if isinstance(date_range, tuple) and len(date_range) == 2:
    if file_ticketing: 
        data_list.append(process_ticketing_bps_ts(pd.read_excel(file_ticketing), "Ticketing (BPS & TS)", date_range))
    if file_pms: 
        data_list.append(process_general_status(pd.read_excel(file_pms), "PMS", "submit", date_range))
    if file_pmg: 
        data_list.append(process_general_status(pd.read_excel(file_pmg), "PMG", "submit", date_range))
    if file_pna: 
        data_list.append(process_general_status(pd.read_excel(file_pna), "PNA", "close", date_range))

if not data_list:
    st.info("Silakan upload minimal 1 file Excel dari menu di samping kiri untuk melihat data sebenarnya.")
    df_master = pd.DataFrame({
        'Nama PIC': ['Andi', 'Budi', 'Citra', 'Deni', 'Eka'],
        'Tickets': [14, 7, 2, 0, 20],
        'Daily_Tickets': [2, 1, 0, 0, 3] 
    })
else:
    df_merged = pd.concat(data_list)
    if not df_merged.empty:
        df_master = df_merged.groupby('Nama PIC')['Tickets'].sum().reset_index()
        df_master['Daily_Tickets'] = 1 
    else:
        df_master = pd.DataFrame(columns=['Nama PIC', 'Tickets', 'Daily_Tickets'])

# --- KALKULASI METRIK & TERAPKAN FILTER RASIO ---
if not df_master.empty:
    df_master['Ratio'] = df_master['Tickets'].apply(lambda x: calculate_ratio(x, target_days))
    df_master['Status Harian'] = df_master['Daily_Tickets'].apply(get_daily_status)
    df_master['Kategori Produktivitas'] = df_master['Ratio'].apply(get_productivity_category)
    df_master['Sisa Target'] = df_master['Tickets'].apply(lambda x: target_days - x if x < target_days else 0)

    # Filter data yang akan ditampilkan berdasarkan ceklis kategori di Sidebar
    if kategori_filter:
        df_master = df_master[df_master['Kategori Produktivitas'].isin(kategori_filter)]

# --- TABS LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📈 Dashboard & Analytics", "📋 Data Tabel", "💬 WA Broadcast Generator"])

if not df_master.empty:
    with tab1:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total PIC Ditampilkan", len(df_master))
        col2.metric("Good Productivity", len(df_master[df_master['Kategori Produktivitas'] == 'Good']))
        col3.metric("Warning (Zero/Very Poor)", len(df_master[df_master['Kategori Produktivitas'].isin(['Zero', 'Very Poor'])]))
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_bar = px.bar(df_master, x='Nama PIC', y='Tickets', color='Kategori Produktivitas',
                             color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'},
                             title=f"Total Tiket per PIC (Target: {target_days} Hari)")
            fig_bar.add_hline(y=target_days, line_dash="dash", annotation_text="Target Rasio 1.0", line_color="red")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            if len(df_master['Kategori Produktivitas'].unique()) > 0:
                fig_pie = px.pie(df_master, names='Kategori Produktivitas', 
                                 color='Kategori Produktivitas',
                                 color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'},
                                 title="Distribusi Produktivitas Tim (Tampil)")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("Silakan pilih minimal 1 kategori pada sidebar untuk memunculkan grafik.")
    
    with tab2:
        st.subheader(f"Data Perhitungan Produktivitas (Target: {target_days} Hari)")
        df_display = df_master.style.format({'Ratio': "{:.2f}"})
        st.dataframe(df_display, use_container_width=True)
    
    with tab3:
        st.subheader("Generate Broadcast WhatsApp")
        
        def generate_broadcast(df, target_days):
            waktu = datetime.now().strftime("%H:%00 WIB")
            
            txt = f"📢 *UPDATE TICKETING PRODUCTIVITY* 📢\n"
            txt += f"📅 Tanggal: {datetime.now().strftime('%d %b %Y')}\n"
            txt += f"⏰ Waktu: {waktu}\n"
            txt += f"🎯 Target Hari Evaluasi: {target_days} Tiket (Rasio 1.0)\n\n"
            
            need_attention = df[df['Kategori Produktivitas'].isin(['Zero', 'Very Poor', 'Poor'])].sort_values('Ratio')
            
            if need_attention.empty:
                txt += "✅ *Luar biasa! Semua tim berada di rasio Good (Rasio >= 1.0).* Pertahankan!\n"
            else:
                txt += "🚨 *PERLU PERHATIAN KHUSUS (Status: Not Safe / Warning)* 🚨\n"
                txt += "Harap segera ambil dan selesaikan tiket untuk memperbaiki rasio produktivitas Anda:\n\n"
                
                for index, row in need_attention.iterrows():
                    tag_name = f"@{row['Nama PIC'].replace(' ', '')}"
                    txt += f"▪️ {tag_name} - *{row['Kategori Produktivitas'].upper()}*\n"
                    txt += f"   Total Tiket: {row['Tickets']} | Rasio: {row['Ratio']:.2f}\n"
                    txt += f"   Status Hari Ini: {row['Status Harian']}\n"
                    txt += f"   *Butuh {row['Sisa Target']} tiket lagi* untuk mencapai rasio aman (1.0).\n\n"
                    
            txt += "Terima kasih atas kerja kerasnya. Semangat! 💪"
            return txt
    
        broadcast_text = generate_broadcast(df_master, target_days)
        st.text_area("Copy Teks di Bawah Ini ke Grup WA:", value=broadcast_text, height=400)
else:
    st.warning("Data kosong atau format file tidak dikenali. Pastikan file Excel berisi data yang valid.")

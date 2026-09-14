import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Productivity Tracking", layout="wide")

# --- HELPER FUNCTIONS ---
def calculate_ratio(total_tickets, current_day):
    if current_day == 0: return 0
    return total_tickets / current_day

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

# --- DATA PROCESSORS ---
def process_ticketing_bps_ts(df):
    # Logika untuk file pertama: BPS & TS (Kalkulasi dari Check-In atau Take Over)
    if df is not None:
        # Pengecekan kolom disesuaikan dengan header Excel lapangan
        if 'Check_In_Date' in df.columns and 'Take_Over_Status' in df.columns:
            valid_tickets = df[df['Check_In_Date'].notna() | (df['Take_Over_Status'].astype(str).str.lower() == 'yes')]
            return valid_tickets.groupby('Nama PIC').size().reset_index(name='Tickets')
        else:
            return df.groupby('Nama PIC').size().reset_index(name='Tickets')
    return pd.DataFrame(columns=['Nama PIC', 'Tickets'])

def process_pms_pmg(df):
    # Logika untuk file PMS dan PMG (Kalkulasi dari status Submit)
    if df is not None:
        if 'Status' in df.columns:
            valid_tickets = df[df['Status'].astype(str).str.lower() == 'submit']
            return valid_tickets.groupby('Nama PIC').size().reset_index(name='Tickets')
        else:
            return df.groupby('Nama PIC').size().reset_index(name='Tickets')
    return pd.DataFrame(columns=['Nama PIC', 'Tickets'])

def process_pna(df):
    # Logika untuk file PNA (Kalkulasi dari status Close)
    if df is not None:
        if 'Status' in df.columns:
            valid_tickets = df[df['Status'].astype(str).str.lower() == 'close']
            return valid_tickets.groupby('Nama PIC').size().reset_index(name='Tickets')
        else:
            return df.groupby('Nama PIC').size().reset_index(name='Tickets')
    return pd.DataFrame(columns=['Nama PIC', 'Tickets'])

# --- UI DASHBOARD ---
st.title("📊 Productivity Ticketing Dashboard")

with st.sidebar:
    st.header("📂 Upload 4 File Data")
    
    # Perubahan struktur 4 file uploader
    file_ticketing = st.file_uploader("1. Upload File Ticketing (BPS & TS)", type=['xlsx', 'csv'])
    file_pms = st.file_uploader("2. Upload File PMS", type=['xlsx', 'csv'])
    file_pmg = st.file_uploader("3. Upload File PMG", type=['xlsx', 'csv'])
    file_pna = st.file_uploader("4. Upload File PNA", type=['xlsx', 'csv'])
    
    st.markdown("---")
    current_day = st.number_input("Tanggal Berjalan (Target Tiket)", min_value=1, max_value=31, value=datetime.now().day)

# --- PROSES PENGGABUNGAN DATA ---
data_list = []

# Membaca masing-masing uploader dan memasukkannya ke kalkulasi utama
if file_ticketing: 
    data_list.append(process_ticketing_bps_ts(pd.read_excel(file_ticketing)))
if file_pms: 
    data_list.append(process_pms_pmg(pd.read_excel(file_pms)))
if file_pmg: 
    data_list.append(process_pms_pmg(pd.read_excel(file_pmg)))
if file_pna: 
    data_list.append(process_pna(pd.read_excel(file_pna)))

# Data dummy untuk visualisasi jika belum ada file yang diunggah
if not data_list:
    st.info("Silakan upload minimal 1 file Excel dari menu di samping kiri untuk melihat data sebenarnya.")
    df_master = pd.DataFrame({
        'Nama PIC': ['Andi', 'Budi', 'Citra', 'Deni', 'Eka'],
        'Tickets': [14, 7, 2, 0, 20],
        'Daily_Tickets': [2, 1, 0, 0, 3] 
    })
else:
    # Menggabungkan semua tiket dari 4 file berdasarkan Nama PIC
    df_master = pd.concat(data_list).groupby('Nama PIC')['Tickets'].sum().reset_index()
    # Asumsi sementara tiket harian di-set 1 (bisa disesuaikan logic filter tanggalnya nanti)
    df_master['Daily_Tickets'] = 1 

# --- KALKULASI METRIK ---
df_master['Ratio'] = df_master['Tickets'].apply(lambda x: calculate_ratio(x, current_day))
df_master['Status Harian'] = df_master['Daily_Tickets'].apply(get_daily_status)
df_master['Kategori Produktivitas'] = df_master['Ratio'].apply(get_productivity_category)
df_master['Sisa Target'] = df_master['Tickets'].apply(lambda x: current_day - x if x < current_day else 0)

# --- TABS LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📈 Dashboard & Analytics", "📋 Data Tabel", "💬 WA Broadcast Generator"])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total PIC Aktif", len(df_master))
    col2.metric("Good Productivity", len(df_master[df_master['Kategori Produktivitas'] == 'Good']))
    col3.metric("Warning (Zero/Very Poor)", len(df_master[df_master['Kategori Produktivitas'].isin(['Zero', 'Very Poor'])]))
    
    st.markdown("---")
    
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_bar = px.bar(df_master, x='Nama PIC', y='Tickets', color='Kategori Produktivitas',
                         color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'},
                         title=f"Total Tiket per PIC (Target: {current_day})")
        fig_bar.add_hline(y=current_day, line_dash="dash", annotation_text="Target Rasio 1.0", line_color="red")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_chart2:
        fig_pie = px.pie(df_master, names='Kategori Produktivitas', 
                         color='Kategori Produktivitas',
                         color_discrete_map={'Good': '#00CC96', 'Poor': '#FFA15A', 'Very Poor': '#EF553B', 'Zero': '#636EFA'},
                         title="Distribusi Produktivitas Tim")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("Data Perhitungan Produktivitas")
    df_display = df_master.style.format({'Ratio': "{:.2f}"})
    st.dataframe(df_display, use_container_width=True)

with tab3:
    st.subheader("Generate Broadcast WhatsApp")
    
    def generate_broadcast(df, current_day):
        waktu = datetime.now().strftime("%H:%00 WIB")
        
        txt = f"📢 *UPDATE TICKETING PRODUCTIVITY* 📢\n"
        txt += f"📅 Tanggal: {datetime.now().strftime('%d %b %Y')}\n"
        txt += f"⏰ Waktu: {waktu}\n"
        txt += f"🎯 Target Hari Ini: {current_day} Tiket (Rasio 1.0)\n\n"
        
        need_attention = df[df['Kategori Produktivitas'].isin(['Zero', 'Very Poor', 'Poor'])].sort_values('Ratio')
        
        if need_attention.empty:
            txt += "✅ *Luar biasa! Semua tim berada di rasio Good (Rasio >= 1.0).* Pertahankan!\n"
        else:
            txt += "🚨 *PERLU PERHATIAN KHUSUS (Status: Not Safe / Warning)* 🚨\n"
            txt += "Harap segera ambil dan selesaikan tiket untuk memperbaiki rasio produktivitas harian Anda:\n\n"
            
            for index, row in need_attention.iterrows():
                tag_name = f"@{row['Nama PIC'].replace(' ', '')}"
                txt += f"▪️ {tag_name} - *{row['Kategori Produktivitas'].upper()}*\n"
                txt += f"   Total Tiket: {row['Tickets']} | Rasio: {row['Ratio']:.2f}\n"
                txt += f"   Status Hari Ini: {row['Status Harian']}\n"
                txt += f"   *Butuh {row['Sisa Target']} tiket lagi* untuk mencapai rasio aman (1.0).\n\n"
                
        txt += "Terima kasih atas kerja kerasnya. Semangat! 💪"
        return txt

    broadcast_text = generate_broadcast(df_master, current_day)
    st.text_area("Copy Teks di Bawah Ini ke Grup WA:", value=broadcast_text, height=400)

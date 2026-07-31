import streamlit as st
import pandas as pd
import numpy as np

# Pengaturan halaman
st.set_page_config(page_title="Auto Analisa KPI", page_icon="📊", layout="wide")
st.title("📊 Automated KPI Dashboard")
st.markdown("Unggah file data **Incident Alarm** Anda (Pastikan terdapat sheet bernama `Ticket List`).")

# Widget untuk upload file
uploaded_file = st.file_uploader("Upload File Raw Data (Format: .xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Membaca raw data
        df = pd.read_excel(uploaded_file, sheet_name='Ticket List')
        st.success("✅ File berhasil dimuat! Menghitung parameter KPI...")
        
        # --- LOGIKA PERHITUNGAN KPI ---
        kpi_data = []
        
        # Fungsi bantuan untuk P90
        def calc_p90(severity):
            mttr_values = df[df['Severity'] == severity]['MTTR']
            return np.percentile(mttr_values.dropna(), 90) if not mttr_values.empty else 0
            
        # 1-4. MTTR P90 (Critical, Major, Minor, Low)
        targets = [('Critical', '4 Jam', 13), ('Major', '8 Jam', 6), 
                   ('Minor', '10 Jam', 4), ('Low', '13 Jam', 2)]
        for sev, target, bobot in targets:
            p90 = calc_p90(sev)
            kpi_data.append([f"MTTR P90 {sev}", target, bobot, len(df[df['Severity'] == sev]), "N/A", p90])
            
        # 5. Take Over Work Order (Critical and Major)
        crit_maj = df[df['Severity'].isin(['Critical', 'Major'])]
        denom_to_cm = len(crit_maj)
        num_to_cm = crit_maj['PICName'].notna().sum()
        perc_to_cm = (num_to_cm / denom_to_cm * 100) if denom_to_cm > 0 else 0
        kpi_data.append(["Take Over Work Order (Critical & Major)", "30%", 3, denom_to_cm, num_to_cm, perc_to_cm])

        # 6. Take Over Work Order (Minor and Low)
        min_low = df[df['Severity'].isin(['Minor', 'Low'])]
        denom_to_ml = len(min_low)
        num_to_ml = min_low['PICName'].notna().sum()
        perc_to_ml = (num_to_ml / denom_to_ml * 100) if denom_to_ml > 0 else 0
        kpi_data.append(["Take Over Work Order (Minor & Low)", "30%", 2, denom_to_ml, num_to_ml, perc_to_ml])
        
        # 7. Site Visitation (Critical and Major)
        crit_maj_pic = crit_maj[crit_maj['PICName'].notna()]
        denom_sv = len(crit_maj_pic)
        num_sv = (crit_maj_pic['IsCheckin'] == 'Yes').sum()
        perc_sv = (num_sv / denom_sv * 100) if denom_sv > 0 else 0
        kpi_data.append(["Site Visitation (Critical & Major)", "40%", 5, denom_sv, num_sv, perc_sv])
        
        # 8. Top 5 Site Priority (Critical and Major)
        # Asumsi: Rank didefinisikan dari kolom Rank (<=5)
        crit_maj_pic_rank5 = crit_maj_pic[crit_maj_pic['Rank'] <= 5]
        denom_top5 = len(crit_maj_pic_rank5)
        num_top5 = (crit_maj_pic_rank5['IsCheckin'] == 'Yes').sum()
        perc_top5 = (num_top5 / denom_top5 * 100) if denom_top5 > 0 else 0
        kpi_data.append(["Top 5 Site Priority (Critical & Major)", "50%", 5, denom_top5, num_top5, perc_top5])
        
        # 9. Closing Ticket
        denom_ct = len(df)
        num_ct = (df['TicketStatus'] == 'CLOSED').sum()
        perc_ct = (num_ct / denom_ct * 100) if denom_ct > 0 else 0
        kpi_data.append(["Closing Ticket", "95%", 1, denom_ct, num_ct, perc_ct])
        
        # 10. RCA Accuracy & Validation
        # Asumsi: RCA tervalidasi jika PICName ada dan RootcauseCategory terisi
        has_pic = df[df['PICName'].notna()]
        denom_rca = len(has_pic)
        num_rca = has_pic['RootcauseCategory'].notna().sum()
        perc_rca = (num_rca / denom_rca * 100) if denom_rca > 0 else 0
        kpi_data.append(["RCA Accuracy & Validation", "30%", 1, denom_rca, num_rca, perc_rca])
        
        # --- MENAMPILKAN HASIL ---
        df_kpi = pd.DataFrame(kpi_data, columns=[
            'Metric', 'Target SLA', 'Bobot KPI', 'Total Ticket WO', 'Num', 'Pencapaian'
        ])
        
        st.subheader("📋 Tabel Ringkasan KPI")
        # Format kolom pencapaian agar menampikan 2 angka di belakang koma
        st.dataframe(df_kpi.style.format({'Pencapaian': '{:.2f}'}), use_container_width=True)
        
        # --- VISUALISASI DATA DASAR (Insight Tambahan) ---
        st.markdown("---")
        st.subheader("📈 Analisa Cepat (Quick Insights)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Distribusi Severity**")
            st.bar_chart(df['Severity'].value_counts())
            
        with col2:
            st.markdown("**Status Tiket**")
            st.bar_chart(df['TicketStatus'].value_counts())
            
        with col3:
            st.markdown("**Check-in vs No Check-in**")
            st.bar_chart(df['IsCheckin'].value_counts())

    except ValueError as e:
        st.error(f"❌ Terjadi kesalahan pada format file. Pastikan terdapat sheet bernama 'Ticket List'. Detail error: {e}")
    except Exception as e:
        st.error(f"❌ Terjadi error tak terduga: {e}")
else:
    st.info("Silakan unggah file Excel untuk melihat Dashboard otomatis.")

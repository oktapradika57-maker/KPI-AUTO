import html as html_lib
import inspect
import io
import os
import zlib
import difflib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Productivity & KPI Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
#  KONSTANTA & IDENTITAS VISUAL
# =============================================================================
WIB = timezone(timedelta(hours=7))  # server cloud berjalan di UTC -> paksa WIB
SOURCE_COLS = ['PMS', 'PMG', 'FNA', 'BPS', 'TS']
CATEGORY_ORDER = ["Zero", "Very Poor", "Poor", "Good"]  # urutan keparahan (kritis -> aman)
RAW_COLS = ['Source', 'Ticket ID', 'Site ID', 'Site Name', 'Nama PIC', 'Status',
            'Take Over Date', 'Check In At', 'Tanggal Utama']

SOURCE_COLORS = {
    'PMS': '#1B3A6B', 'PMG': '#3F7CC4', 'FNA': '#159A8C', 'BPS': '#94A3B8', 'TS': '#C58B2A',
}

CATEGORY_META = {
    "Zero": dict(
        slug="zero", emoji="🔴", color="#B42318", soft="#F9D0CB", ink="#7F1409",
        remark="URGENT", rule="Rasio = 0 (belum ada tiket)",
        wa_title="🚨 *URGENT | ZERO PRODUCTIVITY* 🚨",
        wa_note="Belum ada tiket tercatat pada periode ini. Wajib eskalasi & tindak lanjut HARI INI. "
                "Mohon balas dengan rencana & ETA di grup ini.",
    ),
    "Very Poor": dict(
        slug="vpoor", emoji="🟠", color="#D4501A", soft="#FCDCC8", ink="#8A340B",
        remark="URGENT", rule="0 < Rasio < 0.20",
        wa_title="🚨 *URGENT | VERY POOR* 🚨",
        wa_note="Rasio di bawah 0.20. Segera susun rencana kejar target & laporkan progres hari ini. "
                "Mohon balas dengan rencana & ETA di grup ini.",
    ),
    "Poor": dict(
        slug="poor", emoji="🟡", color="#D99A00", soft="#FCEFC4", ink="#6E4B00",
        remark="WARNING", rule="0.20 ≤ Rasio < 1.00",
        wa_title="⚠️ *WARNING | POOR* ⚠️",
        wa_note="Rasio 0.20 - 0.99, belum mencapai target. Mohon percepat penyelesaian tiket.",
    ),
    "Good": dict(
        slug="good", emoji="🟢", color="#0F8A5F", soft="#D8F0E4", ink="#085A3E",
        remark="ON TRACK", rule="Rasio ≥ 1.00",
        wa_title="✅ *ON TRACK | GOOD PRODUCTIVITY* ✅",
        wa_note="Rasio ≥ 1.0. Terima kasih atas kinerjanya, mohon pertahankan.",
    ),
}
REMARK_CLASS = {"URGENT": "r-urgent", "WARNING": "r-warn", "ON TRACK": "r-ok"}

WA_LINE = "━━━━━━━━━━━━━━━━━━━━━━"
WA_FOOTER = "Terima kasih atas dedikasinya rekan-rekan. Tetap semangat dan selalu jaga keselamatan kerja! 🚀"
WA_MAX_CHARS = 2800      # batas aman per pesan agar nyaman dibaca di WhatsApp
WA_LINK_LIMIT = 7800     # batas panjang URL wa.me


# =============================================================================
#  CSS  (tema enterprise: navy / cobalt, status semantik merah-oranye-kuning-hijau)
# =============================================================================
APP_CSS = '''
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root{--ink:#0B1F3A;--slate:#51627A;--mist:#F4F6FA;--surface:#FFFFFF;--line:#DDE3EC;--cobalt:#1E4FB5;--zero:#B42318;--vpoor:#D4501A;--poor:#D99A00;--good:#0F8A5F;}
.stApp{background:var(--mist);color:var(--ink);}
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp button,.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:'IBM Plex Sans',-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;}
[data-testid="stMainBlockContainer"],.block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1500px;}
[data-testid="stHeader"]{background:transparent;}
footer,.stDeployButton,.stAppDeployButton{visibility:hidden;}
.stApp button:focus-visible,.stApp a:focus-visible{outline:2px solid var(--cobalt);outline-offset:2px;}

section[data-testid="stSidebar"]{background:var(--surface);border-right:1px solid var(--line);}
.sb-title{font-size:13.5px;font-weight:700;color:var(--ink);margin:20px 0 2px;}
.sb-hint{font-size:12px;color:var(--slate);margin-bottom:8px;line-height:1.5;}
.sb-ref{font-size:12.5px;color:var(--ink);background:#EEF3FC;border:1px solid #D5E0F5;border-radius:8px;padding:9px 12px;margin-bottom:12px;line-height:1.5;}
.rd{display:flex;align-items:center;gap:8px;font-size:12.5px;padding:6px 0;border-bottom:1px solid #EEF2F7;}
.rd i{width:8px;height:8px;border-radius:50%;background:#C3CCD9;flex:none;}
.rd i.on{background:var(--good);}
.rd i.warn{background:var(--poor);}
.rd span{flex:1;color:var(--ink);}
.rd em{font-style:normal;color:var(--slate);font-variant-numeric:tabular-nums;}
.tgt{background:#EEF3FC;border:1px solid #D5E0F5;border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.5;margin-top:6px;}
.tgt b{color:var(--cobalt);}

.hero{background:var(--ink);color:#fff;border-radius:12px;padding:22px 28px;display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;border-bottom:3px solid var(--cobalt);}
.hero-title{font-size:26px;font-weight:600;letter-spacing:-0.01em;color:#fff;line-height:1.25;}
.hero-sub{font-size:14px;color:#B8C4D6;margin-top:5px;max-width:580px;line-height:1.5;}
.hero-meta{display:flex;gap:30px;flex-wrap:wrap;}
.hero-meta div{display:flex;flex-direction:column;gap:2px;}
.hero-meta span{font-size:12px;color:#93A4BD;}
.hero-meta b{font-size:15px;font-weight:600;color:#fff;font-variant-numeric:tabular-nums;}

.note{border-radius:10px;padding:12px 16px;font-size:13.5px;line-height:1.6;border:1px solid var(--line);border-left-width:4px;background:var(--surface);margin:12px 0;color:var(--ink);}
.note.crit{border-left-color:var(--zero);background:#FEF6F5;}
.note.warn{border-left-color:var(--poor);background:#FFFBEF;}
.note.ok{border-left-color:var(--good);background:#F3FBF7;}
.note.info{border-left-color:var(--cobalt);background:#F3F7FE;}

.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:var(--surface);border:1px solid var(--line);border-radius:12px;margin:14px 0 12px;}
.kpi{padding:16px 22px;border-right:1px solid var(--line);}
.kpi:last-child{border-right:0;}
.kpi-l{font-size:12.5px;color:var(--slate);font-weight:500;}
.kpi-v{font-size:30px;line-height:1.15;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;margin:4px 0 2px;}
.kpi-s{font-size:12px;color:var(--slate);}

.health{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:12px;}
.health-h{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px;}
.health-h b{font-size:14.5px;font-weight:600;}
.health-h span{font-size:12.5px;color:var(--slate);}
.bar{display:flex;height:16px;border-radius:8px;overflow:hidden;background:#E8EDF4;gap:2px;}
.seg{display:block;height:100%;}
.lgs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:16px;}
.lg{border-left:3px solid;padding-left:12px;}
.lg-t{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--slate);font-weight:500;flex-wrap:wrap;}
.lg-t em{font-style:normal;font-size:10.5px;font-weight:700;padding:1px 8px;border-radius:999px;}
.lg-n{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.3;}
.lg-n small{font-size:12px;font-weight:500;color:var(--slate);margin-left:6px;}
.r-urgent{background:#F9D0CB;color:#7F1409;}
.r-warn{background:#FCEFC4;color:#6E4B00;}
.r-ok{background:#D8F0E4;color:#085A3E;}

.sec{margin:26px 0 10px;}
.sec h3{font-size:17px;font-weight:600;margin:0;color:var(--ink);line-height:1.35;}
.sec p{font-size:13px;color:var(--slate);margin:3px 0 0;line-height:1.5;}

.chip{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;margin-right:6px;}
.chip.zero{background:#F9D0CB;color:#7F1409;}
.chip.vpoor{background:#FCDCC8;color:#8A340B;}
.chip.poor{background:#FCEFC4;color:#6E4B00;}
.chip.good{background:#D8F0E4;color:#085A3E;}
.legend{margin:6px 0 12px;}

.cb{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--cobalt);border-radius:10px;padding:12px 16px;margin:8px 0 10px;}
.cb b{font-size:15px;font-weight:600;}
.cb .rule{color:var(--slate);font-size:13px;}
.cb .cnt{margin-left:auto;font-weight:600;font-variant-numeric:tabular-nums;}
.ml{display:flex;justify-content:space-between;font-size:12.5px;color:var(--slate);margin:14px 0 6px;font-weight:500;}
.ml b{color:var(--ink);font-weight:600;}

.rt{width:100%;border-collapse:collapse;font-size:13px;}
.rt th{text-align:left;font-weight:600;color:var(--slate);padding:8px 10px;border-bottom:1px solid var(--line);font-size:12px;}
.rt td{padding:9px 10px;border-bottom:1px solid #EEF2F7;vertical-align:top;line-height:1.5;}

.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{height:46px;padding:0 18px;font-weight:600;color:var(--slate);}
.stTabs [aria-selected="true"]{color:var(--cobalt);}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--cobalt);height:3px;}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:10px;background:var(--surface);}
[data-testid="stAlert"]{border-radius:10px;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px;overflow:hidden;}
.stDownloadButton button,.stLinkButton a{border-radius:8px;font-weight:600;border:1px solid var(--cobalt);}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{border:1.5px dashed #AFC0DD;border-radius:10px;background:#F8FAFD;}

@media (max-width:900px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr));}.kpi{border-bottom:1px solid var(--line);}.lgs{grid-template-columns:repeat(2,minmax(0,1fr));}.hero-title{font-size:21px;}}
'''

def collapse(s):
    return "".join(line.strip() for line in str(s).strip().splitlines())

def esc(x):
    return html_lib.escape(str(x)).replace("$", "&#36;")

def render(s):
    st.markdown(collapse(s), unsafe_allow_html=True)

st.markdown(f"<style>{collapse(APP_CSS)}</style>", unsafe_allow_html=True)

def _stretch(fn):
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {}
    if "use_container_width" in params:
        return {"use_container_width": True}
    if "width" in params:
        return {"width": "stretch"}
    return {}

DF_KW = _stretch(st.dataframe)
PLOT_KW = _stretch(st.plotly_chart)
BTN_KW = _stretch(st.download_button)
LINK_KW = _stretch(st.link_button) if hasattr(st, "link_button") else {}

def show_df(data, hide_index=False):
    st.dataframe(data, hide_index=hide_index, **DF_KW)

def show_chart(fig):
    st.plotly_chart(fig, theme=None, **PLOT_KW)

def show_code(text):
    try:
        st.code(text, language=None, wrap_lines=True)
    except TypeError:
        st.code(text, language=None)

def panel():
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()

def style_cells(styler, func, subset=None):
    fn = styler.map if hasattr(styler, "map") else styler.applymap
    return fn(func, subset=subset) if subset is not None else fn(func)

def calculate_ratio(total_tickets, target_days):
    if target_days == 0: return 0
    return total_tickets / target_days

def get_productivity_category(ratio):
    if ratio >= 1.0: return "Good"
    elif 0.2 <= ratio < 1.0: return "Poor"
    elif 0 < ratio < 0.2: return "Very Poor"
    else: return "Zero"

def normalize_name(name):
    return str(name).strip().title()

@st.cache_data(show_spinner=False)
def process_swfm_file(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if df.empty: return pd.DataFrame()
        ticket = df.iloc[:, 1]
        site_id = df.iloc[:, 4]
        site_name = df.iloc[:, 5]
        pic = df.iloc[:, 17]
        take_over = df.iloc[:, 35]
        check_in = df.iloc[:, 36]
        valid_mask = check_in.notna()
        ticket_series = ticket[valid_mask].astype(str)
        source_series = ticket_series.apply(lambda x: 'BPS' if x.startswith('BPS') else ('TS' if x.startswith('TS') else 'TS'))
        sub = pd.DataFrame({
            'Source': source_series,
            'Ticket ID': ticket[valid_mask],
            'Site ID': site_id[valid_mask],
            'Site Name': site_name[valid_mask],
            'Nama PIC': pic[valid_mask],
            'Status': 'Visit',
            'Take Over Date': take_over[valid_mask],
            'Check In At': check_in[valid_mask],
            'Tanggal Utama': check_in[valid_mask]
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

def section_title(title, desc=None):
    d = f"<p>{esc(desc)}</p>" if desc else ""
    render(f'<div class="sec"><h3>{esc(title)}</h3>{d}</div>')

def note(kind, html_text):
    render(f'<div class="note {kind}">{html_text}</div>')

def fmt_period(a, b):
    if a.year == b.year:
        return f"{a:%d %b} – {b:%d %b %Y}"
    return f"{a:%d %b %Y} – {b:%d %b %Y}"

def describe_nops(selected, available, max_names=3):
    if not selected: return "Semua NOP"
    if available and set(selected) == set(available): return f"Semua NOP ({len(available)})"
    if len(selected) <= max_names: return ", ".join(selected)
    return f"{len(selected)} NOP terpilih"

def render_hero(period_txt, target_days, area_txt, n_sources):
    render(f'''
    <div class="hero">
      <div>
        <div class="hero-title">Master Productivity &amp; KPI Tracker</div>
        <div class="hero-sub">Monitoring produktivitas PIC lintas sumber tiket SWFM, PM Site, PM Genset, dan FNA.</div>
      </div>
      <div class="hero-meta">
        <div><span>Periode</span><b>{esc(period_txt)}</b></div>
        <div><span>Target evaluasi</span><b>{target_days} hari</b></div>
        <div><span>Area</span><b>{esc(area_txt)}</b></div>
        <div><span>Sumber data</span><b>{n_sources} dari 4 file</b></div>
      </div>
    </div>
    ''')

def kpi_strip(items):
    cells = "".join(
        f'<div class="kpi"><div class="kpi-l">{esc(l)}</div><div class="kpi-v">{esc(v)}</div><div class="kpi-s">{esc(s)}</div></div>'
        for l, v, s in items
    )
    render(f'<div class="kpis">{cells}</div>')

def health_bar(counts, total):
    segs, legend = "", ""
    for cat in CATEGORY_ORDER:
        n = counts.get(cat, 0)
        m = CATEGORY_META[cat]
        pct = (n / total * 100) if total else 0
        if n:
            segs += f'<span class="seg" style="width:{pct:.2f}%;background:{m["color"]}" title="{cat}: {n} PIC ({pct:.0f}%)"></span>'
        legend += (
            f'<div class="lg" style="border-color:{m["color"]}">'
            f'<div class="lg-t">{cat}<em class="{REMARK_CLASS[m["remark"]]}">{m["remark"]}</em></div>'
            f'<div class="lg-n">{n}<small>PIC ({pct:.0f}%)</small></div></div>'
        )
    render(
        f'<div class="health"><div class="health-h"><b>Distribusi status produktivitas</b>'
        f'<span>{total} PIC pada area terpilih</span></div>'
        f'<div class="bar">{segs}</div><div class="lgs">{legend}</div></div>'
    )

def build_insight(b, target_days):
    total = len(b)
    if total == 0: return None
    vc = b['Kategori Produktivitas'].value_counts()
    z, vp, p, g = (int(vc.get(c, 0)) for c in CATEGORY_ORDER)
    urgent = z + vp
    pct = g / total * 100
    gap = int(b['Sisa Target'].sum())
    if urgent > 0:
        worst = b[b['Kategori Produktivitas'].isin(['Zero', 'Very Poor'])].groupby('NOP').size().sort_values(ascending=False)
        area = f" Area dengan PIC urgent terbanyak: <b>{esc(worst.index[0])}</b> ({int(worst.iloc[0])} PIC)." if len(worst) else ""
        return "crit", (
            f"<b>{urgent} PIC berstatus URGENT</b> (Zero {z}, Very Poor {vp}) memerlukan eskalasi hari ini.{area} "
            f"Secara keseluruhan <b>{g} dari {total} PIC ({pct:.0f}%)</b> berstatus Good, dengan total kekurangan "
            f"<b>{gap} tiket</b> terhadap target {target_days} hari per PIC."
        )
    if p > 0:
        return "warn", (
            f"Tidak ada PIC URGENT. <b>{p} PIC berstatus WARNING</b> (Poor) perlu mengejar target. "
            f"<b>{g} dari {total} PIC ({pct:.0f}%)</b> sudah Good; kekurangan total <b>{gap} tiket</b> "
            f"terhadap target {target_days} hari per PIC."
        )
    return "ok", f"Seluruh <b>{total} PIC</b> telah mencapai rasio Good (≥ 1.0). Pertahankan kinerjanya."

def style_fig(fig, height=430, rotate=True):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="IBM Plex Sans, Segoe UI, Arial, sans-serif", size=12, color="#0B1F3A"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, margin=dict(l=8, r=8, t=64, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
    )
    fig.update_xaxes(showgrid=False, title_text=None, **({"tickangle": -45} if rotate else {}))
    fig.update_yaxes(gridcolor="#E7ECF3", zeroline=False)
    return fig

def cat_cell_style(val):
    m = CATEGORY_META.get(val)
    return f"background-color:{m['soft']};color:{m['ink']};font-weight:600" if m else ''

def remark_cell_style(val):
    cat = {"URGENT": "Zero", "WARNING": "Poor", "ON TRACK": "Good"}.get(val)
    return cat_cell_style(cat) if cat else ''

def ratio_cell_style(val):
    m = CATEGORY_META[get_productivity_category(val)]
    return f"color:{m['ink']};font-weight:700"

def matrix_cell_style(val):
    if isinstance(val, str):
        if val == 'Good': return cat_cell_style('Good')
        if val == 'Bad': return cat_cell_style('Zero')
        return ''
    return cat_cell_style(get_productivity_category(val))

def wa_sorted(df, cat):
    asc = cat != "Good"
    return df.sort_values(['Ratio', 'Total Tiket', 'Nama PIC'], ascending=[asc, asc, True])

def wa_header(nops_display, d_start, d_end, waktu_str, target_days):
    return (
        "📊 *DAILY PRODUCTIVITY REPORT* 📊\n"
        f"📍 *Area / NOP:* {nops_display}\n"
        f"🗓️ *Periode:* {d_start.strftime('%d %b %Y')} s/d {d_end.strftime('%d %b %Y')}\n"
        f"⏰ *Update:* {waktu_str}\n"
        f"🎯 *Target:* {target_days} Hari (Rasio Aman >= 1.0)\n"
        f"{WA_LINE}\n\n"
    )

def wa_name(row, tag):
    nm = str(row['Nama PIC'])
    return "@" + nm.replace(' ', '') if tag else nm

def wa_entry(i, row, cat, opts, target_days):
    m = CATEGORY_META[cat]
    total = int(row['Total Tiket'])
    nop_part = "" if opts.get('group_nop') else f" — *{row['NOP']}*"
    t = f"{i}. {m['emoji']} {wa_name(row, opts['tag'])}{nop_part}\n"
    if cat == "Good":
        surplus = max(total - target_days, 0)
        extra = f"Surplus *+{surplus}* tiket" if surplus else "Tepat target"
        t += f"   └ Total *{total}* | Rasio *{row['Ratio']:.2f}* | {extra}\n"
    else:
        t += f"   └ Total *{total}* | Rasio *{row['Ratio']:.2f}* | Kurang *{int(row['Sisa Target'])}* tiket\n"
    if opts['src']:
        t += "   └ " + " | ".join(f"{c}:{int(row[c])}" for c in SOURCE_COLS) + "\n"
    return t + "\n"

def wa_section_blocks(df_cat, cat, opts, target_days, lead_divider=False):
    m = CATEGORY_META[cat]
    pending = (f"{WA_LINE}\n" if lead_divider else "")
    pending += f"{m['wa_title']}\n_{m['wa_note']}_\n*Jumlah: {len(df_cat)} PIC*\n\n"
    blocks, idx = [], 0
    def add(entry):
        nonlocal pending
        blocks.append(pending + entry)
        pending = ""
    if opts['group_nop']:
        for nop, g in df_cat.groupby('NOP', sort=True):
            pending += f"📍 *{nop}* ({len(g)} PIC)\n"
            for _, row in g.iterrows():
                idx += 1
                add(wa_entry(idx, row, cat, opts, target_days))
    else:
        for _, row in df_cat.iterrows():
            idx += 1
            add(wa_entry(idx, row, cat, opts, target_days))
    return blocks

def wa_paginate(header, blocks, footer=WA_FOOTER, max_chars=WA_MAX_CHARS):
    cont = "📊 *DAILY PRODUCTIVITY REPORT* (lanjutan)\n" + WA_LINE + "\n\n"
    pages, cur, has_body = [], header, False
    for b in blocks:
        if has_body and len(cur) + len(b) > max_chars:
            pages.append(cur.rstrip() + "\n\n_… bersambung ke pesan berikutnya_\n")
            cur, has_body = cont, False
        if not has_body and b.startswith(WA_LINE + "\n"):
            b = b[len(WA_LINE) + 1:]
        cur += b
        has_body = True
    cur += f"{WA_LINE}\n{footer}"
    pages.append(cur)
    if len(pages) > 1:
        n = len(pages)
        pages = [p.replace("\n", f"\n_Bagian {i} dari {n}_\n", 1) for i, p in enumerate(pages, 1)]
    return pages

def build_wa_category(df, cat, opts, header, target_days):
    dfc = wa_sorted(df[df['Kategori Produktivitas'] == cat], cat)
    if dfc.empty: return []
    return wa_paginate(header, wa_section_blocks(dfc, cat, opts, target_days))

def build_wa_executive(df, cats, opts, header, target_days):
    total = len(df)
    counts = {c: int((df['Kategori Produktivitas'] == c).sum()) for c in CATEGORY_ORDER}
    pct = counts['Good'] / total * 100 if total else 0

    s = "📌 *RINGKASAN STATUS*\n"
    for c in CATEGORY_ORDER:
        m = CATEGORY_META[c]
        s += f"{m['emoji']} {c}: *{counts[c]}* PIC _({m['remark']})_\n"
    s += f"📈 *Compliance Rate:* {pct:.0f}% ({counts['Good']} dari {total} PIC Good)\n\n"
    blocks = [s]

    need = df[df['Kategori Produktivitas'].isin(['Zero', 'Very Poor', 'Poor'])].sort_values(['Ratio', 'Total Tiket', 'Nama PIC'])
    if need.empty:
        blocks.append("✅ *LUAR BIASA!* Seluruh personel telah mencapai Rasio *GOOD* (>= 1.0).\n\nPertahankan kinerjanya! 💪\n\n")
    elif opts['top3']:
        t = "⚠️ *TOP 3 PIC PERLU PERHATIAN UTAMA* ⚠️\n_Diharap untuk segera menyelesaikan / mengambil tiket:_\n\n"
        for i, (_, r) in enumerate(need.head(3).iterrows(), 1):
            t += f"{i}. {wa_name(r, opts['tag'])} ({r['NOP']}) ➔ Rasio: *{r['Ratio']:.2f}* (Total {int(r['Total Tiket'])} Tiket)\n"
        blocks.append(t + "\n")

    for c in CATEGORY_ORDER:
        if c in cats:
            dfc = wa_sorted(df[df['Kategori Produktivitas'] == c], c)
            if not dfc.empty:
                blocks += wa_section_blocks(dfc, c, opts, target_days, lead_divider=True)
    return wa_paginate(header, blocks)

def render_wa_pages(pages, key_prefix, file_stub):
    for i, page in enumerate(pages, 1):
        label = f"Pesan {i} dari {len(pages)}" if len(pages) > 1 else "Pesan siap kirim"
        render(f'<div class="ml"><b>{label}</b><span>{len(page):,} karakter</span></div>')
        show_code(page)
        c1, c2 = st.columns(2)
        with c1:
            link = "https://wa.me/?text=" + quote(page)
            if hasattr(st, "link_button") and len(link) <= WA_LINK_LIMIT:
                st.link_button("Buka di WhatsApp", link, **LINK_KW)
            else:
                st.caption("Pesan terlalu panjang untuk tautan langsung.")
        with c2:
            st.download_button("Unduh sebagai .txt", data=page, file_name=f"{file_stub}_{i}.txt",
                               mime="text/plain", key=f"{key_prefix}_dl_{i}", **BTN_KW)
        with st.expander("Edit manual sebelum dikirim"):
            st.text_area("Teks pesan", value=page, height=320, label_visibility="collapsed",
                         key=f"{key_prefix}_edit_{i}_{zlib.crc32(page.encode('utf-8'))}")

def cat_banner(cat, n, title=None, rule=None):
    if cat:
        m = CATEGORY_META[cat]
        color, remark = m['color'], m['remark']
        title, rule = cat, m['rule']
    else:
        color, remark = "#1E4FB5", None
    pill = f'<span class="chip {CATEGORY_META[cat]["slug"]}">{remark}</span>' if cat else ""
    render(f'<div class="cb" style="border-left-color:{color}">{pill}<b>{esc(title)}</b>'
           f'<span class="rule">{esc(rule)}</span><span class="cnt">{n} PIC</span></div>')

def render_wa_tab(broadcast_all, has_data, n_sources, nops_display, d_start, d_end, target_days, waktu_str, excluded_count):
    section_title("Generate Broadcast WhatsApp", "Template profesional, dipisah per kategori agar mudah dibaca tim.")
    if not has_data:
        note("warn", "<b>Belum ada data sumber.</b>")
        return
    if n_sources < 4:
        note("warn", f"<b>Data belum lengkap ({n_sources} dari 4 sumber).</b>")
    if broadcast_all.empty:
        note("info", "Tidak ada PIC yang dapat ditampilkan pada area terpilih.")
        return

    counts = {c: int((broadcast_all['Kategori Produktivitas'] == c).sum()) for c in CATEGORY_ORDER}
    header = wa_header(nops_display, d_start, d_end, waktu_str, target_days)

    ctrl, view = st.columns([1, 2.4], gap="large")
    with ctrl:
        with panel():
            st.markdown("**Pengaturan pesan**")
            opt_tag = st.toggle("Tag nama PIC (@)", value=True, key="wa_opt_tag")
            opt_src = st.toggle("Rincian sumber tiket", value=True, key="wa_opt_src")
            opt_top3 = st.toggle("Top 3 prioritas", value=True, key="wa_opt_top3")
            opt_sort = st.radio("Susun daftar PIC", ["Terendah dulu", "Per NOP"], key="wa_opt_sort")
            exec_cats = st.multiselect("Kategori pada Ringkasan Eksekutif", options=CATEGORY_ORDER,
                                       default=["Zero", "Very Poor", "Poor"], key="wa_opt_cats")
            if excluded_count:
                st.caption(f"{excluded_count} PIC dikecualikan dari broadcast.")

    opts = dict(tag=opt_tag, src=opt_src, top3=opt_top3, group_nop=(opt_sort == "Per NOP"))
    with view:
        labels = ["Ringkasan Eksekutif"] + [f"{CATEGORY_META[c]['emoji']} {c} ({counts[c]})" for c in CATEGORY_ORDER]
        subtabs = st.tabs(labels)
        with subtabs[0]:
            cat_banner(None, len(broadcast_all), title="Ringkasan Eksekutif", rule="Gabungan kategori terpilih")
            pages = build_wa_executive(broadcast_all, exec_cats, opts, header, target_days)
            render_wa_pages(pages, "wa_exec", "WA_Ringkasan")

        for k, c in enumerate(CATEGORY_ORDER, 1):
            with subtabs[k]:
                cat_banner(c, counts[c])
                if counts[c] == 0:
                    note("info", f"Tidak ada PIC {c}.")
                else:
                    pages = build_wa_category(broadcast_all, c, opts, header, target_days)
                    render_wa_pages(pages, f"wa_{CATEGORY_META[c]['slug']}", f"WA_{c.replace(' ', '')}")

def build_excel(sheets):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        wb = writer.book
        hdr = wb.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#0B1F3A',
                             'valign': 'vcenter', 'border': 1, 'border_color': '#DDE3EC'})
        fmts = {c: wb.add_format({'bg_color': CATEGORY_META[c]['soft'], 'font_color': CATEGORY_META[c]['ink'], 'bold': True}) for c in CATEGORY_ORDER}
        text_map = {'Zero': 'Zero', 'Very Poor': 'Very Poor', 'Poor': 'Poor', 'Good': 'Good',
                    'URGENT': 'Zero', 'WARNING': 'Poor', 'ON TRACK': 'Good', 'Bad': 'Zero'}
        for name, df, is_matrix in sheets:
            df.to_excel(writer, index=False, sheet_name=name)
            ws = writer.sheets[name]
            ws.set_row(0, 22)
            ws.freeze_panes(1, 0)
            n = len(df)
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), hdr)
                try:
                    mx = df[col].astype(str).str.len().max() if n else 0
                    mx = 0 if pd.isna(mx) else int(mx)
                except Exception:
                    mx = 10
                ws.set_column(j, j, min(max(len(str(col)), mx) + 3, 42))
                if n and col in ('Kategori Produktivitas', 'Remark'):
                    for val, cat in text_map.items():
                        ws.conditional_format(1, j, n, j, {'type': 'cell', 'criteria': '==', 'value': f'"{val}"', 'format': fmts[cat]})
                if n and is_matrix and col not in ('Nama PIC', 'Remark'):
                    rules = [('>=', 1, None, 'Good'), ('between', 0.2, 0.999999, 'Poor'),
                             ('between', 0.000001, 0.199999, 'Very Poor'), ('==', 0, None, 'Zero')]
                    for crit, v1, v2, cat in rules:
                        cfg = {'type': 'cell', 'criteria': crit, 'format': fmts[cat]}
                        if crit == 'between': cfg.update({'minimum': v1, 'maximum': v2})
                        else: cfg['value'] = v1
                        ws.conditional_format(1, j, n, j, cfg)
            if n: ws.autofilter(0, 0, n, len(df.columns) - 1)
    return out.getvalue()

master_pic_df = pd.DataFrame(columns=['Nama PIC', 'NOP'])
file_master_name = "nama pic_2.xlsx"
excluded_from_all = ['okta pradika', 'harminto', 'armadi', 'muhamad rayhan']
master_notices = []

actual_master_file = None
for f in os.listdir():
    if f.lower() == file_master_name.lower():
        actual_master_file = f
        break

if actual_master_file:
    try:
        df_master_pic = pd.read_excel(actual_master_file)
        name_col = df_master_pic.columns[0]
        for col in df_master_pic.columns:
            if 'nama' in str(col).lower() or 'pic' in str(col).lower():
                name_col = col
                break
        nop_col = df_master_pic.columns[1] if len(df_master_pic.columns) > 1 else None
        for col in df_master_pic.columns:
            if 'nop' in str(col).lower():
                nop_col = col
                break
        df_master_pic = df_master_pic.dropna(subset=[name_col])
        master_pic_df['Nama PIC'] = df_master_pic[name_col].apply(normalize_name)
        if nop_col is not None:
            def format_nop(x):
                x = str(x).strip()
                if x.lower() in ['nan', '', 'none', 'nat']: return 'Tidak Terdeteksi'
                if not x.lower().startswith('nop'): return 'NOP ' + x.title()
                return 'NOP ' + x[4:].strip().title()
            master_pic_df['NOP'] = df_master_pic[nop_col].apply(format_nop)
        else:
            master_pic_df['NOP'] = 'Tidak Terdeteksi'
        master_pic_df = master_pic_df[~master_pic_df['Nama PIC'].str.lower().apply(lambda x: any(ex in x for ex in excluded_from_all))]
        master_pic_df = master_pic_df.drop_duplicates(subset=['Nama PIC'])
    except Exception as e:
        master_notices.append(("warn", f"Gagal memproses file <b>{esc(file_master_name)}</b>: {esc(e)}"))
else:
    master_notices.append(("crit", f"File <b>{esc(file_master_name)}</b> tidak ditemukan di sistem."))

hero_slot = st.container()
notice_slot = st.container()

with st.sidebar:
    render('<div class="sb-title" style="margin-top:4px">Sumber Data</div><div class="sb-hint">Unggah 4 file utama format Excel.</div>')
    render(f'<div class="sb-ref">Referensi baku <b>{esc(file_master_name)}</b> aktif.</div>')
    file_swfm = st.file_uploader("1. Ticket_SWFM (TS & BPS)", type=['xlsx', 'xls'])
    file_pms = st.file_uploader("2. PM Site", type=['xlsx', 'xls'])
    file_pmg = st.file_uploader("3. PM Genset", type=['xlsx', 'xls'])
    file_fna = st.file_uploader("4. Export List Ticket Field Operation (FNA)", type=['xlsx', 'xls'])
    readiness_slot = st.container()
    render('<div class="sb-title">Rentang Waktu</div>')
    wib_now = datetime.now(WIB)
    today = wib_now.date()
    first_day = today.replace(day=1)
    date_range = st.date_input("Rentang Waktu Tiket", value=(first_day, today))
    date_incomplete = False
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        d_start, d_end = date_range
    else:
        d_start = d_end = date_range[0] if isinstance(date_range, (tuple, list)) and len(date_range) else date_range
        date_incomplete = True
    target_days = (d_end - d_start).days + 1
    if date_incomplete:
        st.warning("Pilih tanggal akhir.")
    render(f'<div class="tgt">Target hari evaluasi: <b>{target_days} hari</b><br>Rasio aman ≥ 1.0 berarti minimal {target_days} tiket per PIC.</div>')

src_frames = {}
if file_swfm: src_frames['Ticket SWFM (TS & BPS)'] = process_swfm_file(file_swfm.getvalue())
if file_pms: src_frames['PM Site'] = process_pms_file(file_pms.getvalue())
if file_pmg: src_frames['PM Genset'] = process_pmg_file(file_pmg.getvalue())
if file_fna: src_frames['Export List Ticket (FNA)'] = process_fna_file(file_fna.getvalue())

n_sources = len(src_frames)
valid_frames = [d for d in src_frames.values() if d is not None and not d.empty]
has_data = len(valid_frames) > 0

with readiness_slot:
    rows = ""
    for label in ['Ticket SWFM (TS & BPS)', 'PM Site', 'PM Genset', 'Export List Ticket (FNA)']:
        d = src_frames.get(label)
        if d is None: rows += f'<div class="rd"><i></i><span>{label}</span><em>Belum diunggah</em></div>'
        elif d.empty: rows += f'<div class="rd"><i class="warn"></i><span>{label}</span><em>0 baris valid</em></div>'
        else: rows += f'<div class="rd"><i class="on"></i><span>{label}</span><em>{len(d):,} baris valid</em></div>'
    render(f'<div class="sb-title">Kesiapan Data</div>{rows}')

if not has_data:
    df_raw = pd.DataFrame(columns=RAW_COLS + ['NOP'])
    df_raw['Tanggal Utama'] = pd.to_datetime(df_raw['Tanggal Utama'], errors='coerce')
else:
    df_raw = pd.concat(valid_frames, ignore_index=True)
    df_raw['Tanggal Utama'] = pd.to_datetime(df_raw['Tanggal Utama'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Nama PIC'])
    df_raw['Nama PIC'] = df_raw['Nama PIC'].apply(normalize_name)
    df_raw['Nama Asli Tarikan'] = df_raw['Nama PIC']  # Backup nama asli untuk fitur log

    # === FITUR TRACKING & VALIDASI NAMA (AUTO-MAP & MANUAL OVERRIDE) ===
    if not master_pic_df.empty:
        valid_master_names = master_pic_df['Nama PIC'].tolist()
        raw_names_unique = df_raw['Nama PIC'].unique()
        
        unmatched_names = [n for n in raw_names_unique if n not in valid_master_names]
        
        if 'name_overrides' not in st.session_state:
            st.session_state['name_overrides'] = {}
            
        mapping_data = []
        for un in unmatched_names:
            if un in st.session_state['name_overrides']:
                mapped = st.session_state['name_overrides'][un]
                status = "Manual Edit"
            else:
                matches = difflib.get_close_matches(un, valid_master_names, n=1, cutoff=0.7)
                mapped = matches[0] if matches else None
                if not mapped:
                    un_first = un.split()[0].lower()
                    for vmn in valid_master_names:
                        if vmn.split()[0].lower() == un_first:
                            mapped = vmn
                            break
                status = "Auto-Mapped" if mapped else "Unmapped"
            
            mapping_data.append({
                "Nama Tarikan (Asli)": un,
                "Nama di Master Data": mapped if mapped else None,
                "Status": status
            })
            
        st.session_state['mapping_df'] = pd.DataFrame(mapping_data)
        
        apply_map = {}
        if mapping_data:
            for row in mapping_data:
                if row['Nama di Master Data']:
                    apply_map[row['Nama Tarikan (Asli)']] = row['Nama di Master Data']
                    
        if apply_map:
            df_raw['Nama PIC'] = df_raw['Nama PIC'].replace(apply_map)

        df_raw = pd.merge(df_raw, master_pic_df[['Nama PIC', 'NOP']], on='Nama PIC', how='inner')
    else:
        df_raw['NOP'] = 'Tidak Terdeteksi'

selected_nops = []
available_nops = []
if not master_pic_df.empty:
    with st.sidebar:
        render('<div class="sb-title">Filter Area (NOP)</div>')
        available_nops = sorted(master_pic_df['NOP'].unique())
        selected_nops = st.multiselect("Pilih NOP yang ingin ditampilkan", options=available_nops, default=available_nops)
        if selected_nops:
            df_raw = df_raw[df_raw['NOP'].isin(selected_nops)]
            master_pic_df = master_pic_df[master_pic_df['NOP'].isin(selected_nops)]
        render('<div class="sb-title">Filter Kategori</div>')
        kategori_options = ["Good", "Poor", "Very Poor", "Zero"]
        kategori_filter = st.multiselect("Filter Kategori", options=kategori_options, default=kategori_options, label_visibility="collapsed")
else:
    kategori_filter = []

with hero_slot:
    render_hero(fmt_period(d_start, d_end), target_days, describe_nops(selected_nops, available_nops, 3), n_sources)
with notice_slot:
    for kind, text in master_notices:
        note(kind, text)

# --- TABS LAYOUT TERBARU (TAB 5 DITAMBAHKAN) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Analisa Rentang Waktu", "Matriks Performa Bulanan", "WA Broadcast", "Raw Data & Export", "Validasi Nama PIC"])

matrix_display = pd.DataFrame()
df_master = pd.DataFrame()

if not df_raw.empty or (not master_pic_df.empty and selected_nops):
    start_date = pd.to_datetime(d_start)
    end_date = pd.to_datetime(d_end).replace(hour=23, minute=59, second=59)
    df_filtered_date = df_raw[(df_raw['Tanggal Utama'] >= start_date) & (df_raw['Tanggal Utama'] <= end_date)]

    if not df_filtered_date.empty:
        breakdown = pd.pivot_table(df_filtered_date, index='Nama PIC', columns='Source', values='Ticket ID', aggfunc='count', fill_value=0).reset_index()
        breakdown.columns.name = None
    else:
        breakdown = pd.DataFrame(columns=['Nama PIC'])

    for col in SOURCE_COLS:
        if col not in breakdown.columns: breakdown[col] = 0

    breakdown = breakdown[['Nama PIC'] + SOURCE_COLS]

    if not master_pic_df.empty:
        breakdown = pd.merge(master_pic_df[['Nama PIC', 'NOP']], breakdown, on='Nama PIC', how='left').fillna(0)
    else:
        all_pics = df_raw['Nama PIC'].unique()
        missing_pics = set(all_pics) - set(breakdown['Nama PIC'].unique())
        if missing_pics:
            df_missing = pd.DataFrame({'Nama PIC': list(missing_pics), 'PMS': 0, 'PMG': 0, 'FNA': 0, 'BPS': 0, 'TS': 0})
            breakdown = pd.concat([breakdown, df_missing], ignore_index=True)
        if 'NOP' not in breakdown.columns:
            breakdown['NOP'] = 'Tidak Terdeteksi'

    breakdown[SOURCE_COLS] = breakdown[SOURCE_COLS].astype(int)
    breakdown['Total Tiket'] = breakdown[SOURCE_COLS].sum(axis=1)
    breakdown['Ratio'] = breakdown['Total Tiket'].apply(lambda x: calculate_ratio(x, target_days))
    breakdown['Kategori Produktivitas'] = breakdown['Ratio'].apply(get_productivity_category)
    breakdown['Sisa Target'] = breakdown['Total Tiket'].apply(lambda x: target_days - x if x < target_days else 0)
    breakdown['Remark'] = breakdown['Kategori Produktivitas'].map(lambda c: CATEGORY_META[c]['remark'])

    df_master = breakdown.copy()
    if kategori_filter:
        df_master = df_master[df_master['Kategori Produktivitas'].isin(kategori_filter)]

    with tab1:
        if not has_data: note("warn", "<b>Belum ada data sumber.</b>")
        elif n_sources < 4: note("warn", f"<b>Data belum lengkap ({n_sources} dari 4 sumber).</b>")

        total_pic = len(breakdown)
        total_tiket = int(breakdown['Total Tiket'].sum())
        counts_all = {c: int((breakdown['Kategori Produktivitas'] == c).sum()) for c in CATEGORY_ORDER}
        compliance = (counts_all['Good'] / total_pic * 100) if total_pic else 0
        gap_total = int(breakdown['Sisa Target'].sum())

        kpi_strip([
            ("Total PIC Aktif", f"{total_pic:,}", "Pada area (NOP) terpilih"),
            ("Total Tiket", f"{total_tiket:,}", f"Rata-rata {(total_tiket / total_pic if total_pic else 0):.1f} tiket per PIC"),
            ("Compliance Rate", f"{compliance:.0f}%", f"{counts_all['Good']} PIC berstatus Good"),
            ("Kekurangan Tiket", f"{gap_total:,}", f"Terhadap target {target_days} hari per PIC"),
        ])
        health_bar(counts_all, total_pic)

        insight = build_insight(breakdown, target_days)
        if insight and has_data: note(insight[0], "<b>Ringkasan eksekutif.</b> " + insight[1])

        if not master_pic_df.empty:
            st.caption("Master mapping aktif & Auto-Validasi Nama PIC bekerja di latar belakang (cek Tab Validasi).")

        section_title(f"Rincian Perolehan Tiket per PIC (Target: {target_days} Hari)")
        if df_master.empty:
            note("info", "Tidak ada PIC pada kategori yang dipilih.")
        else:
            table_cols = ['Nama PIC', 'NOP'] + SOURCE_COLS + ['Total Tiket', 'Ratio', 'Sisa Target', 'Kategori Produktivitas', 'Remark']
            fmt = {c: '{:.0f}' for c in SOURCE_COLS + ['Total Tiket', 'Sisa Target']}
            fmt['Ratio'] = '{:.2f}'
            tbl = df_master.sort_values(['Ratio', 'Total Tiket', 'Nama PIC'])[table_cols].style.format(fmt)
            tbl = style_cells(tbl, cat_cell_style, subset=['Kategori Produktivitas'])
            tbl = style_cells(tbl, remark_cell_style, subset=['Remark'])
            tbl = style_cells(tbl, ratio_cell_style, subset=['Ratio'])
            show_df(tbl, hide_index=True)

            # --- FITUR BARU: TOMBOL DOWNLOAD UNTUK SETIAP ROW (PER PIC) ---
            section_title("📥 Export Rincian per PIC (Row-by-Row)", "Unduh daftar tiket spesifik untuk masing-masing personel (format CSV).")
            with st.expander("Buka Tabel Download Per Baris"):
                h1, h2, h3, h4, h5 = st.columns([3, 2.5, 1.5, 2, 3])
                h1.markdown("**Nama PIC**")
                h2.markdown("**Area (NOP)**")
                h3.markdown("**Total Tiket**")
                h4.markdown("**Status**")
                h5.markdown("**Aksi (Download)**")
                st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                
                for idx, row in df_master.sort_values(['Ratio', 'Total Tiket', 'Nama PIC']).iterrows():
                    c1, c2, c3, c4, c5 = st.columns([3, 2.5, 1.5, 2, 3])
                    c1.write(f"**{row['Nama PIC']}**")
                    c2.write(f"{row['NOP']}")
                    c3.write(f"{row['Total Tiket']}")
                    
                    cat_slug = CATEGORY_META[row['Kategori Produktivitas']]['slug']
                    c4.markdown(f'<span class="chip {cat_slug}">{row["Kategori Produktivitas"]}</span>', unsafe_allow_html=True)
                    
                    pic_raw = df_raw[df_raw['Nama PIC'] == row['Nama PIC']]
                    csv_data = pic_raw.to_csv(index=False).encode('utf-8')
                    
                    c5.download_button(
                        label="⬇️ Download CSV",
                        data=csv_data,
                        file_name=f"Tiket_{row['Nama PIC'].replace(' ', '_')}_{d_start.strftime('%Y%m%d')}.csv",
                        key=f"dl_row_{idx}_{row['Nama PIC']}"
                    )
            
            section_title("Visualisasi Performa", "Komposisi sumber tiket dan posisi rasio setiap PIC terhadap target.")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                with panel():
                    fig_bar = px.bar(df_master.sort_values('Total Tiket', ascending=False), x='Nama PIC', y=SOURCE_COLS,
                                     title="Komposisi Perolehan Tiket per PIC", color_discrete_map=SOURCE_COLORS)
                    show_chart(style_fig(fig_bar))
            with col_chart2:
                with panel():
                    fig_ratio = px.bar(df_master.sort_values('Ratio', ascending=False), x='Nama PIC', y='Ratio',
                                       color='Kategori Produktivitas',
                                       color_discrete_map={c: CATEGORY_META[c]['color'] for c in CATEGORY_ORDER},
                                       category_orders={'Kategori Produktivitas': CATEGORY_ORDER},
                                       title="Rasio Produktivitas")
                    fig_ratio.add_hline(y=1.0, line_dash="dash")
                    show_chart(style_fig(fig_ratio))

        if breakdown['NOP'].nunique() > 1:
            section_title("Perbandingan Antar Area (NOP)")
            cat_counts = pd.crosstab(breakdown['NOP'], breakdown['Kategori Produktivitas']).reindex(columns=CATEGORY_ORDER, fill_value=0)
            nop_tbl = cat_counts.copy()
            nop_tbl.insert(0, 'Total PIC', breakdown.groupby('NOP').size())
            nop_tbl['Compliance %'] = (nop_tbl['Good'] / nop_tbl['Total PIC'] * 100)
            nop_tbl['Total Tiket'] = breakdown.groupby('NOP')['Total Tiket'].sum()
            nop_tbl['Rata-rata Rasio'] = breakdown.groupby('NOP')['Ratio'].mean()
            nop_tbl = nop_tbl.sort_values(['Compliance %', 'Total PIC']).reset_index()
            c_n1, c_n2 = st.columns([1.15, 1])
            with c_n1:
                nop_style = nop_tbl.style.format({'Compliance %': '{:.0f}%', 'Rata-rata Rasio': '{:.2f}', 'Total Tiket': '{:.0f}'})
                for c in CATEGORY_ORDER:
                    nop_style = style_cells(nop_style, (lambda v, _c=c: cat_cell_style(_c) if v > 0 else ''), subset=[c])
                show_df(nop_style, hide_index=True)
            with c_n2:
                with panel():
                    nop_long = cat_counts.reset_index().melt(id_vars='NOP', var_name='Kategori', value_name='Jumlah PIC')
                    fig_nop = px.bar(nop_long, y='NOP', x='Jumlah PIC', color='Kategori', orientation='h',
                                     color_discrete_map={c: CATEGORY_META[c]['color'] for c in CATEGORY_ORDER},
                                     category_orders={'Kategori': CATEGORY_ORDER})
                    show_chart(style_fig(fig_nop, height=max(300, 60 * breakdown['NOP'].nunique() + 120), rotate=False))

    with tab2:
        section_title("Matriks Rasio Produktivitas Bulanan")
        df_matrix_raw = df_raw.dropna(subset=['Tanggal Utama']).copy()
        df_matrix_raw['Bulan_Sort'] = df_matrix_raw['Tanggal Utama'].dt.to_period('M')
        df_matrix_raw['DaysInMonth'] = df_matrix_raw['Tanggal Utama'].dt.daysinmonth
        monthly_tickets = df_matrix_raw.groupby(['Nama PIC', 'Bulan_Sort', 'DaysInMonth']).size().reset_index(name='Tickets')

        if monthly_tickets.empty:
            note("info", "Belum ada tiket bertanggal pada data.")
        else:
            monthly_tickets['Ratio'] = monthly_tickets['Tickets'] / monthly_tickets['DaysInMonth']
            matrix_pivot = monthly_tickets.pivot(index='Nama PIC', columns='Bulan_Sort', values='Ratio').fillna(0)
            available_months = sorted(matrix_pivot.columns)

            if not master_pic_df.empty:
                missing_matrix = [p for p in master_pic_df['Nama PIC'] if p not in matrix_pivot.index]
                if missing_matrix:
                    matrix_pivot = pd.concat([matrix_pivot, pd.DataFrame(0.0, index=missing_matrix, columns=matrix_pivot.columns)])
            matrix_pivot.index.name = 'Nama PIC'

            col_m1, col_m2 = st.columns(2)
            selected_months = col_m1.multiselect("Pilih Bulan", options=available_months,
                                                 default=available_months[-4:] if len(available_months) >= 4 else available_months,
                                                 format_func=lambda x: x.strftime('%B %Y'))
            all_matrix_pics = sorted(matrix_pivot.index.tolist())
            selected_matrix_pics = col_m2.multiselect("Filter Nama PIC", options=all_matrix_pics, default=[])

            if selected_months:
                matrix_display = matrix_pivot[selected_months].copy()
                threshold_good = 3 if len(selected_months) == 4 else (len(selected_months) - 1 if len(selected_months) > 1 else 1)
                def calculate_remark(row):
                    good_months = sum(row >= 1.0)
                    return "Good" if good_months >= threshold_good else "Bad"
                matrix_display['Remark'] = matrix_display.apply(calculate_remark, axis=1)
                rename_cols = {col: col.strftime('%b-%y') for col in selected_months}
                matrix_display = matrix_display.rename(columns=rename_cols)
                month_str_cols = list(rename_cols.values())

                if selected_matrix_pics:
                    matrix_display = matrix_display[matrix_display.index.isin(selected_matrix_pics)]

                n_good_pic = int((matrix_display['Remark'] == 'Good').sum())
                n_bad_pic = int((matrix_display['Remark'] == 'Bad').sum())
                kpi_strip([
                    ("PIC pada matriks", f"{len(matrix_display):,}", f"{len(selected_months)} bulan dipilih"),
                    ("Remark Good", f"{n_good_pic:,}", f"Rasio ≥ 1.0 minimal {threshold_good} dari {len(selected_months)} bulan"),
                    ("Remark Bad", f"{n_bad_pic:,}", "Belum konsisten"),
                ])
                matrix_style = style_cells(matrix_display.style.format({col: "{:.2f}" for col in month_str_cols}), matrix_cell_style)
                show_df(matrix_style)

    with tab3:
        excluded_from_wa = ['darli', 'indra', 'riko setiadi', 'riki hidayat']
        broadcast_df = breakdown[~breakdown['Nama PIC'].str.lower().apply(lambda x: any(ex in x for ex in excluded_from_wa))]
        render_wa_tab(
            broadcast_all=broadcast_df, has_data=has_data, n_sources=n_sources,
            nops_display=describe_nops(selected_nops, available_nops, 8),
            d_start=d_start, d_end=d_end, target_days=target_days,
            waktu_str=wib_now.strftime("%d %b %Y - %H:%M WIB"),
            excluded_count=len(breakdown) - len(broadcast_df),
        )

    with tab4:
        section_title("Master Database Gabungan")
        col_f1, col_f2 = st.columns(2)
        filter_source = col_f1.multiselect("Filter Sumber Kategori", options=df_raw['Source'].unique(), default=df_raw['Source'].unique())
        filter_nama = col_f2.text_input("Cari Nama PIC di Database")

        df_export = df_raw.copy()
        if filter_source:
            df_export = df_export[df_export['Source'].isin(filter_source)]
        if filter_nama:
            df_export = df_export[df_export['Nama PIC'].str.contains(filter_nama, case=False, na=False)]
        df_export['Tanggal Utama'] = pd.to_datetime(df_export['Tanggal Utama'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

        kpi_strip([
            ("Baris data", f"{len(df_export):,}", "Sesuai filter aktif"),
            ("PIC unik", f"{df_export['Nama PIC'].nunique():,}", "Pada data tampil"),
            ("Sumber aktif", f"{df_export['Source'].nunique()}", "Dari PMS, PMG, FNA, BPS, TS"),
        ])
        show_df(df_export)

        sheets = [("Master Raw Data", df_export, False)]
        summary_cols = ['Nama PIC', 'NOP'] + SOURCE_COLS + ['Total Tiket', 'Ratio', 'Kategori Produktivitas', 'Remark', 'Sisa Target']
        sheets.append(("Summary Per PIC", df_master[summary_cols], False))
        if not matrix_display.empty:
            md = matrix_display.reset_index()
            md.columns = ['Nama PIC'] + list(md.columns[1:])
            sheets.append(("Matriks Bulanan", md, True))
        st.download_button(
            label="Download Master Database ke Excel (.xlsx)",
            data=build_excel(sheets),
            file_name=f"Master_KPI_Filtered_NOP_{wib_now.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # === TAB 5: VALIDASI NAMA PIC ===
    with tab5:
        section_title("Tracking & Validasi Nama PIC", "Sesuaikan jika terdapat nama ditarikan tiket yang sedikit berbeda dengan Master Data.")
        if 'mapping_df' in st.session_state and not st.session_state['mapping_df'].empty:
            note("warn", "Ditemukan nama pada tiket yang tidak sama persis dengan Master Data. Sistem telah mencoba mencocokkan otomatis (Auto-Mapped). "
                         "Anda dapat mengedit kolom <b>Nama di Master Data</b> secara manual di tabel bawah jika hasil otomatis kurang tepat.")
            
            master_choices = [""] + sorted(master_pic_df['Nama PIC'].unique().tolist())
            
            edited_df = st.data_editor(
                st.session_state['mapping_df'],
                column_config={
                    "Nama Tarikan (Asli)": st.column_config.TextColumn("Nama Tarikan (Asli)", disabled=True),
                    "Nama di Master Data": st.column_config.SelectboxColumn(
                        "Nama di Master Data",
                        help="Pilih nama yang benar sesuai list master",
                        options=master_choices,
                        required=False
                    ),
                    "Status": st.column_config.TextColumn("Status", disabled=True)
                },
                use_container_width=True,
                key="editor_mapping",
                num_rows="fixed"
            )
            
            if st.button("Simpan Perubahan & Update Data", type="primary"):
                has_changes = False
                for idx, row in edited_df.iterrows():
                    orig = row['Nama Tarikan (Asli)']
                    new_val = row['Nama di Master Data']
                    if pd.notna(new_val) and str(new_val).strip() != "":
                        if orig not in st.session_state['name_overrides'] or st.session_state['name_overrides'].get(orig) != new_val:
                            st.session_state['name_overrides'][orig] = new_val
                            has_changes = True
                    else:
                        if orig in st.session_state['name_overrides']:
                            del st.session_state['name_overrides'][orig]
                            has_changes = True
                            
                if has_changes:
                    st.success("Perubahan mapping nama berhasil disimpan! Sedang memperbarui dashboard...")
                    st.rerun()
                else:
                    st.info("Tidak ada perubahan baru untuk disimpan.")
        else:
            note("ok", "Luar biasa! Seluruh nama PIC dari data tarikan tiket sudah cocok 100% dengan nama di file Master.")

else:
    for t in (tab1, tab2, tab3, tab4, tab5):
        with t:
            note("info", "<b>Belum ada data untuk ditampilkan.</b> Unggah file sumber pada panel kiri.")

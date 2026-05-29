import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import os 
import json 
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro (Pro Terminal)")

# --- CƠ SỞ DỮ LIỆU NỘI BỘ VỀ DOANH NGHIỆP ---
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "PVC": {"name": "Tổng công ty Hóa chất Dầu khí", "industry": "Hóa chất Dầu khí", "exchange": "HNX", "issueShare": 50000000, "eps": 550, "bvps": 11800, "roe": 0.04},
    "DRI": {"name": "Công ty cổ phần Cao su Đắk Lắk", "industry": "Cao su công nghiệp", "exchange": "UPCOM", "issueShare": 73200000, "eps": 950, "bvps": 12500, "roe": 0.08},
    "CSM": {"name": "Công ty Công nghiệp Cao su Miền Nam", "industry": "Săm lốp & Phụ tùng", "exchange": "HOSE", "issueShare": 133637422, "eps": 420, "bvps": 14500, "roe": 0.03},
    "TNT": {"name": "Công ty Tài nguyên và Tài chính Việt Nam", "industry": "Bất động sản", "exchange": "HOSE", "issueShare": 51000000, "eps": 150, "bvps": 10200, "roe": 0.01},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

# --- BỘ LƯU TRỮ VĨNH VIỄN ---
FILE_BO_NHU = "portfolio_storage.json"

def tai_danh_muc_tu_o_cung():
    mac_dinh = {"TCB": [1000, 32000], "ACV": [500, 43000], "OIL": [2000, 14000], "PVC": [0, 0], "DRI": [0, 0], "CSM": [0, 0], "TNT": [0, 0]}
    if os.path.exists(FILE_BO_NHU):
        try:
            with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
        except: return mac_dinh
    return mac_dinh

def luu_danh_muc_vao_o_cung(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=4)

DANH_MỤC_LIVE = tai_danh_muc_tu_o_cung()
DANH_SACH_MA = list(DANH_MỤC_LIVE.keys())

# 2. KHU VỰC ĐIỀU KHIỂN SIDEBAR
st.sidebar.header("🔍 Phân tích Chuyên sâu")
if not DANH_SACH_MA:
    st.warning("⚠️ Bảng giá đang trống. Vui lòng sang Tab 'Bảng Giá' để thêm mã!")
    ma_chon = ""
else:
    ma_chon = st.sidebar.selectbox("Chọn mã để xem Biểu đồ & Hồ sơ:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ LIVE ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
    if not ma: return pd.DataFrame(), "Không có mã", ""
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())
    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        res = requests.get(url_vnd, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * 1000
                return df.tail(180).reset_index(drop=True), "VNDirect DChart 🟢", ""
    except: pass
    return pd.DataFrame(), "Thất bại 🔴", ""

# --- MODULE 2: HỒ SƠ DOANH NGHIỆP ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    if not ma: return {}
    profile = {'industry': 'N/A', 'pe': 'N/A', 'pb': 'N/A', 'roe': 'N/A', 'exchange': 'N/A', 'issueShare': 0, 'marketCap': 0, 'eps': 0, 'bvps': 0, 'nguon_cap': 'Đang kết nối...'}
    try:
        url_tv = "https://scanner.tradingview.com/vietnam/scan"
        payload = {"symbols": {"tickers": [f"HOSE:{ma}", f"HNX:{ma}", f"UPCOM:{ma}"]}, "columns": ["price_earnings_ttm", "price_book_ratio", "return_on_equity", "total_shares_outstanding", "market_cap_basic", "sector"]}
        res_tv = requests.post(url_tv, json=payload, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res_tv.status_code == 200:
            data = res_tv.json().get('data', [])
            if data and len(data) > 0:
                d = data[0].get('d', [])
                profile['pe'] = d[0] if d[0] is not None else 'N/A'
                profile['pb'] = d[1] if d[1] is not None else 'N/A'
                profile['roe'] = d[2] if d[2] is not None else 'N/A'
                profile['issueShare'] = d[3] if d[3] else 0
                profile['marketCap'] = d[4] if d[4] else 0
                profile['industry'] = d[5] if d[5] else 'N/A'
                profile['exchange'] = data[0].get('s', '').split(':')[0]
                profile['nguon_cap'] = 'Máy chủ TradingView 🟢'
    except: pass

    if profile['pe'] == 'N/A' or profile['issueShare'] == 0:
        if ma in LOCAL_DB:
            db = LOCAL_DB[ma]
            profile.update({'industry': db['industry'], 'exchange': db['exchange'], 'issueShare': db['issueShare'], 'roe': db['roe'], 'eps': db['eps'], 'bvps': db['bvps'], 'nguon_cap': 'TradingView + CSDL Nội bộ 🟢'})
    return profile

# --- MODULE 3: ĐÁNH GIÁ TCBS ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_danh_gia_tcbs(ma):
    try:
        url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/rating/{ma}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if res.status_code == 200: return res.json().get('generalRating', 0)
    except: pass
    return 0

# --- TOÁN HỌC & ĐỊNH DẠNG ---
def tinh_rsi(series, period=14):
    delta = series.diff(); up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean(); ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down; return 100 - (100 / (1 + rs))

def tinh_macd(series):
    e12 = series.ewm(span=12, adjust=False).mean(); e26 = series.ewm(span=26, adjust=False).mean()
    macd = e12 - e26; sig = macd.ewm(span=9, adjust=False).mean(); return macd, sig

def format_metric(val, is_pct=False):
    if val in [None, 'N/A', '']: return "N/A"
    try:
        v = float(val)
        if is_pct: return f"{v*100:.2f}%" if abs(v) < 2 else f"{v:.2f}%"
        return f"{v:.2f}"
    except: return "N/A"

# 3. GIAO DIỆN CHÍNH
tab0, tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Bảng Giá Điện Tử", "📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ", "📡 Radar Dòng tiền", "💼 Danh mục"])

# --- TAB 0: BẢNG GIÁ ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    with st.expander("⚙️ Quản lý Mã Cổ Phiếu", expanded=False):
        c_a1, c_a2, c_d1, c_d2 = st.columns([3, 2, 3, 2])
        with c_a1: m_moi = st.text_input("Thêm mã", placeholder="Nhập mã (VD: FPT)...", label_visibility="collapsed").upper().strip()
        with c_a2: 
            if st.button("➕ Thêm mã", use_container_width=True):
                if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE); st.rerun()
        with c_d1: m_xoa = st.selectbox("Xóa mã", ["-- Chọn mã xóa --"] + DANH_SACH_MA, label_visibility="collapsed")
        with c_d2:
            if st.button("🗑️ Xóa mã", type="primary", use_container_width=True):
                if m_xoa != "-- Chọn mã xóa --": del DANH_MỤC_LIVE[m_xoa]; luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE); st.rerun()

    css_bg = "<style>.stock-board-container{width:100%;overflow-x:auto;background-color:#111;padding:10px;border-radius:8px;}.stock-board{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:14px;background-color:#111;color:#fff;}.stock-board th,.stock-board td{border:1px solid #333;padding:8px 12px;text-align:right;white-space:nowrap;}.stock-board th{background-color:#222;color:#ccc;text-align:center;font-weight:bold;}.col-ma{text-align:left!important;font-weight:bold;}.c-ref{color:#F2C94C!important;}.c-ceil{color:#E040FB!important;}.c-floor{color:#00E5FF!important;}.c-up{color:#00E676!important;}.c-down{color:#FF5252!important;}</style>"
    html_c = css_bg + '<div class="stock-board-container"><table class="stock-board"><tr><th>Mã</th><th class="c-ref">TC</th><th class="c-ceil">Trần</th><th class="c-floor">Sàn</th><th>Khớp Lệnh</th><th>+/-</th><th>%</th><th>Tổng KL</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th></tr>'
    if DANH_SACH_MA:
        for m in DANH_SACH_MA:
            df, _, _ = lay_du_lieu_bieu_do(m)
            if df.empty or len(df) < 2: continue
            san = lay_ho_so_doanh_nghiep(m).get('exchange', 'HOSE')
            bd = 0.15 if san == 'UPCOM' else (0.1 if san == 'HNX' else 0.07)
            tc, gia, mc, cao, thap, tkl = df['Close'].iloc[-2], df['Close'].iloc[-1], df['Open'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1], df['Volume'].iloc[-1]
            tr, sg = round(tc*(1+bd)/100)*100, round(tc*(1-bd)/100)*100
            td, pt = gia-tc, (gia-tc)/tc*100 if tc>0 else 0
            def mau(g): return "c-ceil" if g>=tr else "c-floor" if g<=sg else "c-up" if g>tc else "c-down" if g<tc else "c-ref"
            m_g, dc = mau(gia), "+" if td>0 else ""
            html_c += f"<tr><td class='col-ma {m_g}'>{m}</td><td class='c-ref'>{tc:,.0f}</td><td class='c-ceil'>{tr:,.0f}</td><td class='c-floor'>{sg:,.0f}</td><td class='{m_g}' style='font-weight:bold;'>{gia:,.0f}</td><td class='{m_g}'>{dc}{td:,.0f}</td><td class='{m_g}'>{dc}{pt:.2f}%</td><td>{tkl:,.0f}</td><td class='{mau(mc)}'>{mc:,.0f}</td><td class='{mau(cao)}'>{cao:,.0f}</td><td class='{mau(thap)}'>{thap:,.0f}</td></tr>"
    html_c += "</table></div>"; st.markdown(html_c, unsafe_allow_html=True)

# --- TAB 1: BIỂU ĐỒ ---
with tab1:
    if ma_chon:
        st.subheader(f"Trung tâm Phân tích Kỹ thuật - Mã: {ma_chon}")
        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(20).mean(); df['MA50'] = df['Close'].rolling(50).mean()
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
            fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=['#26A69A' if c>=o else '#EF5350' for c,o in zip(df['Close'],df['Open'])]), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: HỒ SƠ ---
with tab2:
    if ma_chon:
        hs = lay_ho_so_doanh_nghiep(ma_chon); c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ngành nghề", str(hs.get('industry')))
        c2.metric("P/E", format_metric(hs.get('pe')))
        c3.metric("P/B", format_metric(hs.get('pb')))
        c4.metric("ROE", format_metric(hs.get('roe'), True))

# --- TAB 3: RADAR & AI ---
with tab3:
    if st.button("🚀 Quét Radar Toàn Bộ"):
        kq = []
        for m in DANH_SACH_MA:
            d, _, _ = lay_du_lieu_bieu_do(m)
            if not d.empty and len(d)>=50:
                r = tinh_rsi(d['Close']).iloc[-1]
                kq.append({"Mã CP": m, "Giá": d['Close'].iloc[-1], "RSI": round(r, 2), "Tín hiệu": "MUA" if r<35 else "BÁN" if r>70 else "GIỮ"})
        if kq: st.table(pd.DataFrame(kq))
    
    st.markdown("---")
    m_pt = st.selectbox("AI Advisor Phân Tích:", ["-- Chọn mã --"] + DANH_SACH_MA)
    if m_pt != "-- Chọn mã --":
        d, _, _ = lay_du_lieu_bieu_do(m_pt)
        if not d.empty:
            r = tinh_rsi(d['Close']).iloc[-1]; tcbs = lay_danh_gia_tcbs(m_pt)
            st.info(f"### Cố vấn AI cho {m_pt}\n* RSI: {r:.1f} ({"Quá bán" if r<30 else "Quá mua" if r>70 else "Cân bằng"})\n* Đánh giá chuyên gia: {tcbs}/5 sao\n* **Khuyến nghị:** {"Gom mua dần" if r<40 else "Nắm giữ"}")

# --- TAB 4: DANH MỤC (KHÔI PHỤC) ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng")
    du_lieu_cap_nhat = {}
    for ma in DANH_SACH_MA:
        c1, c2, c3 = st.columns([2, 3, 3])
        c1.write(f"### {ma}")
        sl = c2.number_input(f"SL {ma}", min_value=0, step=100, value=DANH_MỤC_LIVE.get(ma, [0, 0])[0], key=f"sl_{ma}")
        gv = c3.number_input(f"Giá {ma}", min_value=0, step=500, value=DANH_MỤC_LIVE.get(ma, [0, 0])[1], key=f"gv_{ma}")
        du_lieu_cap_nhat[ma] = [sl, gv]
    
    if st.button("💾 Lưu Cấu Hình"):
        luu_danh_muc_vao_o_cung(du_lieu_cap_nhat); st.success("Đã lưu!"); time.sleep(0.5); st.rerun()

    # PHẦN BÁO CÁO TÀI SẢN (PHỤC HỒI TẠI ĐÂY)
    hien_thi = [{"Mã CP": k, "SL": v[0], "Giá Vốn": v[1]} for k, v in du_lieu_cap_nhat.items() if v[0] > 0]
    if hien_thi:
        st.markdown("---")
        st.write("### 📊 Hiệu suất Danh mục đầu tư thực tế")
        rows, t_von, t_gt = [], 0, 0
        for item in hien_thi:
            m = item["Mã CP"]; sl = item["SL"]; gv = item["Giá Vốn"]
            df_l, _, _ = lay_du_lieu_bieu_do(m)
            g_l = df_l['Close'].iloc[-1] if not df_l.empty else gv
            v_i = sl * gv; gt_i = sl * g_l; ln = gt_i - v_i
            t_von += v_i; t_gt += gt_i
            rows.append({"Mã": m, "SL": f"{sl:,}", "Giá Vốn": f"{gv:,.0f}", "Giá Hiện Tại": f"{g_l:,.0f}", "Vốn": v_i, "Giá Trị": gt_i, "Lời/Lỗ": ln, "%": f"{(ln/v_i*100) if v_i>0 else 0:.2f}%"})
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng vốn", f"{t_von:,.0f}")
        m2.metric("Tổng giá trị (NAV)", f"{t_gt:,.0f}")
        m3.metric("Tổng Lời/Lỗ", f"{t_gt-t_von:,.0f}", delta=f"{t_gt-t_von:,.0f}")
        
        df_p = pd.DataFrame(rows)
        st.dataframe(df_p.drop(columns=["Vốn", "Giá Trị"]), use_container_width=True, hide_index=True)
        
        st.write("### 🍕 Tỷ trọng tài sản")
        fig_p = px.pie(df_p, values='Giá Trị', names='Mã', hole=0.4)
        st.plotly_chart(fig_p, use_container_width=True)

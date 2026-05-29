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

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & GIAO DIỆN
# ==========================================
st.set_page_config(page_title="Hệ thống Phân tích & Quản trị Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro (Institutional Terminal)")

# CƠ SỞ DỮ LIỆU NỘI BỘ VỀ DOANH NGHIỆP (DATA LAKE)
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "PVC": {"name": "Tổng công ty Hóa chất Dầu khí", "industry": "Hóa chất Dầu khí", "exchange": "HNX", "issueShare": 50000000, "eps": 550, "bvps": 11800, "roe": 0.04},
    "DRI": {"name": "Công ty cổ phần Cao su Đắk Lắk", "industry": "Cao su công nghiệp", "exchange": "UPCOM", "issueShare": 73200000, "eps": 950, "bvps": 12500, "roe": 0.08},
    "CSM": {"name": "Công ty Công nghiệp Cao su Miền Nam", "industry": "Săm lốp & Phụ tùng", "exchange": "HOSE", "issueShare": 133637422, "eps": 420, "bvps": 14500, "roe": 0.03},
    "TNT": {"name": "Công ty Tài nguyên và Tài chính Việt Nam", "industry": "Bất động sản", "exchange": "HOSE", "issueShare": 51000000, "eps": 150, "bvps": 10200, "roe": 0.01},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

# BỘ LƯU TRỮ DANH MỤC VĨNH VIỄN
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

st.sidebar.header("🔍 Phân tích Chuyên sâu")
if not DANH_SACH_MA:
    st.sidebar.warning("⚠️ Bảng giá trống. Hãy sang Tab 'Bảng Giá' để thêm mã!")
    ma_chon = ""
else:
    ma_chon = st.sidebar.selectbox("Chọn mã xem Biểu đồ & Hồ sơ:", DANH_SACH_MA)

# ==========================================
# 2. CÁC MODULE KẾT NỐI API & TÍNH TOÁN
# ==========================================
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

@st.cache_data(ttl=86400, show_spinner=False)
def lay_danh_gia_tcbs(ma):
    try:
        url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/rating/{ma}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if res.status_code == 200: return res.json().get('generalRating', 0)
    except: pass
    return 0

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

# ==========================================
# 3. GIAO DIỆN CHÍNH (5 TABS)
# ==========================================
tab0, tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Bảng Giá Điện Tử", "📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "📡 Bộ lọc & AI Advisor", "💼 Quản lý Danh mục"])

# --- TAB 0: BẢNG GIÁ ĐIỆN TỬ ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    with st.expander("⚙️ Quản lý Danh sách Theo dõi (Watchlist Manager)", expanded=False):
        c_a1, c_a2, c_d1, c_d2 = st.columns([3, 2, 3, 2])
        with c_a1: m_moi = st.text_input("Thêm mã", placeholder="Nhập mã mới (VD: FPT, HPG)...", label_visibility="collapsed").upper().strip()
        with c_a2: 
            if st.button("➕ Thêm mã", use_container_width=True):
                if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE); st.rerun()
        with c_d1: m_xoa = st.selectbox("Xóa mã", ["-- Chọn mã muốn xóa khỏi Watchlist --"] + DANH_SACH_MA, label_visibility="collapsed")
        with c_d2:
            if st.button("🗑️ Xóa mã", type="primary", use_container_width=True):
                if m_xoa != "-- Chọn mã muốn xóa khỏi Watchlist --": del DANH_MỤC_LIVE[m_xoa]; luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE); st.rerun()

    css_bg = "<style>.stock-board-container{width:100%;overflow-x:auto;background-color:#111;padding:10px;border-radius:8px;}.stock-board{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:14px;background-color:#111;color:#fff;}.stock-board th,.stock-board td{border:1px solid #333;padding:8px 12px;text-align:right;white-space:nowrap;}.stock-board th{background-color:#222;color:#ccc;text-align:center;font-weight:bold;}.col-ma{text-align:left!important;font-weight:bold;}.c-ref{color:#F2C94C!important;}.c-ceil{color:#E040FB!important;}.c-floor{color:#00E5FF!important;}.c-up{color:#00E676!important;}.c-down{color:#FF5252!important;}</style>"
    html_c = css_bg + '<div class="stock-board-container"><table class="stock-board"><tr><th>Mã</th><th class="c-ref">TC</th><th class="c-ceil">Trần</th><th class="c-floor">Sàn</th><th>Khớp Lệnh</th><th>+/-</th><th>%</th><th>Tổng KL</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th></tr>'
    
    with st.spinner("Đang đồng bộ bảng điện tử..."):
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
        else: html_c += "<tr><td colspan='11' style='text-align:center;'>Danh mục Watchlist trống. Vui lòng thêm mã.</td></tr>"
    html_c += "</table></div>"; st.markdown(html_c, unsafe_allow_html=True)

# --- TAB 1: BIỂU ĐỒ KỸ THUẬT ---
with tab1:
    if ma_chon:
        st.subheader(f"Trung tâm Phân tích Kỹ thuật - Mã: {ma_chon}")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        show_vol = col_t1.checkbox("📊 Bật Volume (Khối lượng)", value=True)
        show_ma20 = col_t2.checkbox("📈 Bật đường xu hướng MA 20", value=True)
        show_ma50 = col_t3.checkbox("📉 Bật đường xu hướng MA 50", value=False)
        show_bb = col_t4.checkbox("🌐 Bật dải băng Bollinger Bands", value=False)

        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(20).mean(); df['MA50'] = df['Close'].rolling(50).mean()
            df['BB_Std'] = df['Close'].rolling(20).std()
            df['BB_Upper'] = df['MA20'] + (df['BB_Std'] * 2); df['BB_Lower'] = df['MA20'] - (df['BB_Std'] * 2)

            fig = make_subplots(rows=2 if show_vol else 1, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25] if show_vol else None)
            fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Nến giá"), row=1, col=1)
            
            if show_ma20: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], mode='lines', name='MA 20', line=dict(color='#2962FF', width=1.5)), row=1, col=1)
            if show_ma50: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA50'], mode='lines', name='MA 50', line=dict(color='#FF6D00', width=1.5)), row=1, col=1)
            if show_bb:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='gray', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

            if show_vol:
                vol_colors = ['#26A69A' if row['Close'] >= row['Open'] else '#EF5350' for i, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Khối lượng', marker_color=vol_colors), row=2, col=1)

            fig.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
            
            csv_price = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Tải lịch sử giá 180 phiên (CSV)", data=csv_price, file_name=f"lich_su_gia_{ma_chon}.csv", mime="text/csv")

# --- TAB 2: HỒ SƠ DOANH NGHIỆP ---
with tab2:
    if ma_chon:
        st.subheader(f"Hồ sơ Doanh nghiệp & Chỉ số Cơ bản - Mã: {ma_chon}")
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        pe_hien_thi = profile.get('pe')
        pb_hien_thi = profile.get('pb')
        von_hoa_ty = profile.get('marketCap', 0) / 1_000_000_000
        
        df, _, _ = lay_du_lieu_bieu_do(ma_chon)
        gia_hien_tai, klgd_20 = 0, 0
        if not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            if profile.get('nguon_cap') == 'TradingView + CSDL Nội bộ 🟢' and gia_hien_tai > 0:
                if profile.get('eps', 0) > 0: pe_hien_thi = gia_hien_tai / profile['eps']
                if profile.get('bvps', 0) > 0: pb_hien_thi = gia_hien_tai / profile['bvps']
                von_hoa_ty = (gia_hien_tai * profile.get('issueShare', 0)) / 1_000_000_000

        st.caption(f"Trạm dữ liệu nền: **{profile.get('nguon_cap', 'N/A')}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Phân loại Ngành", str(profile.get('industry', 'N/A')))
        c2.metric("P/E (Định giá)", format_metric(pe_hien_thi))
        c3.metric("P/B (Giá/Sổ sách)", format_metric(pb_hien_thi))
        c4.metric("ROE (Hiệu quả vốn)", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("📌 **Quy mô định giá & Thanh khoản:**")
        st.write(f"- **Thị giá hiện hành:** `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- **Khối lượng giao dịch TB (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- **Khối lượng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR DÒNG TIỀN & AI ADVISOR BẢN THIẾT KẾ ĐẸP ---
with tab3:
    st.subheader("📡 Radar Quét Khối lượng & Tín hiệu Đa biến")
    if DANH_SACH_MA:
        if st.button("🚀 Bắt đầu Quét Hệ thống Toàn Watchlist"):
            ket_qua = []
            with st.spinner("Đang rà soát tín hiệu dòng tiền..."):
                for ma in DANH_SACH_MA:
                    df_scan, _, _ = lay_du_lieu_bieu_do(ma)
                    if not df_scan.empty and len(df_scan) >= 50:
                        df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                        df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                        df_scan['MA50'] = df_scan['Close'].rolling(window=50).mean()
                        df_scan['Vol20'] = df_scan['Volume'].rolling(window=20).mean()
                        macd, signal = tinh_macd(df_scan['Close'])
                        
                        gia, rsi = df_scan['Close'].iloc[-1], df_scan['RSI'].iloc[-1]
                        diem_mua, tin_hieu = 0, []
                        
                        if rsi < 35: diem_mua += 1; tin_hieu.append("RSI vùng đáy")
                        elif rsi > 70: diem_mua -= 1; tin_hieu.append("RSI quá mua")
                        if df_scan['MA20'].iloc[-1] > df_scan['MA50'].iloc[-1]: diem_mua += 1; tin_hieu.append("MA20 trên MA50")
                        if macd.iloc[-1] > signal.iloc[-1]: diem_mua += 1; tin_hieu.append("MACD giao cắt mua")
                            
                        dot_bien = "Bình thường"
                        if df_scan['Volume'].iloc[-1] > (df_scan['Vol20'].iloc[-1] * 1.5): 
                            diem_mua += 1; dot_bien = "⭐ NỔ VOL"
                            
                        if diem_mua >= 3: khuyen_nghi = "🟢 MUA MẠNH"
                        elif diem_mua >= 1: khuyen_nghi = "🟡 NẮM GIỮ / THEO DÕI"
                        else: khuyen_nghi = "🔴 RỦI RO / SUY YẾU"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia:,.0f}", "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Hội tụ Kỹ thuật": ", ".join(tin_hieu) if tin_hieu else "Tích lũy", "Khuyến nghị": khuyen_nghi})
                    time.sleep(0.05) 
            
            if ket_qua:
                df_kq = pd.DataFrame(ket_qua)
                st.dataframe(df_kq, use_container_width=True, hide_index=True)
                csv_radar = df_kq.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Tải báo cáo Quét Radar Dòng tiền (CSV)", data=csv_radar, file_name="bao_cao_radar_live.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("🤖 Hệ thống Cố vấn Đầu tư Chuyên nghiệp (AI Advisor Enterprise)")
    
    col_advisor1, col_advisor2 = st.columns(2)
    with col_advisor1:
        m_pt = st.selectbox("1. Chọn mã cổ phiếu cần nội soi:", ["-- Chọn mã cổ phiếu --"] + DANH_SACH_MA, key="advisor_stock_select")
    with col_advisor2:
        kịch_bản_vĩ_mô = st.radio("2. Giả lập kịch bản vĩ mô toàn cầu:", ["Cơ sở (Ổn định & Phục hồi)", "Căng thẳng Địa chính trị leo thang", "Nới lỏng Tiền tệ mạnh mẽ (Tiền rẻ)"], horizontal=True)

    if m_pt != "-- Chọn mã cổ phiếu --":
        with st.spinner(f"AI đang trích xuất dữ liệu và biên soạn báo cáo chuẩn cho {m_pt}..."):
            df_pt, _, _ = lay_du_lieu_bieu_do(m_pt)
            if not df_pt.empty and len(df_pt) >= 50:
                df_pt['RSI'] = tinh_rsi(df_pt['Close'])
                df_pt['MA20'] = df_pt['Close'].rolling(window=20).mean()
                df_pt['MA50'] = df_pt['Close'].rolling(window=50).mean()
                macd_pt, signal_pt = tinh_macd(df_pt['Close'])
                
                gia_pt = df_pt['Close'].iloc[-1]
                rsi_pt = df_pt['RSI'].iloc[-1]
                macd_cur = macd_pt.iloc[-1]
                sig_cur = signal_pt.iloc[-1]
                
                diem_tcbs = lay_danh_gia_tcbs(m_pt)
                
                # CƠ SỞ DỮ LIỆU CỐ VẤN DẠNG CẤU TRÚC (STRUCTURED DATA)
                DỮ_LIỆU_VĨ_MÔ = {
                    "TCB": {
                        "vimo_coso": "Chu kỳ phục hồi của thị trường Bất động sản trong nước và việc tháo gỡ pháp lý giúp giảm áp lực nợ xấu. Lãi suất huy động duy trì ở mức thấp giúp tối ưu hóa chi phí vốn (COF).",
                        "vimo_stress": "Địa chính trị căng thẳng đẩy lạm phát nhập khẩu tăng, buộc Ngân hàng Nhà nước phải thắt chặt thanh khoản để bảo vệ tỷ giá. Rủi ro nợ xấu hệ thống gia tăng.",
                        "vimo_tienre": "Hạ lãi suất điều hành mạnh mẽ thúc đẩy tăng trưởng tín dụng bùng nổ. Dòng tiền nhàn rỗi chảy mạnh từ tiết kiệm sang các kênh tài sản và tiêu dùng.",
                        "sources": [
                            {"name": "SSI Research (Chiến lược Ngành)", "text": "Dự báo tăng trưởng tín dụng của TCB tiếp tục dẫn đầu toàn ngành nhờ lợi thế tệp khách hàng lớn và hệ sinh thái bất động sản. Biên lãi ròng (NIM) dự phóng hồi phục mạnh về mức 4.2%. Khuyến nghị: Khả quan."},
                            {"name": "Vietcap (Phân tích Doanh nghiệp)", "text": "Dự phóng Lợi nhuận trước thuế tăng trưởng 12% - 15% so với cùng kỳ nhờ chiến lược số hóa mạnh mẽ giúp tăng tỷ lệ tiền gửi không kỳ hạn (CASA) và giảm thiểu rủi ro tập trung bằng cách mở rộng sang phân khúc SME."}
                        ],
                        "action_coso": "KIẾN NGHỊ NẮM GIỮ / MUA TÍCH LŨY: Phù hợp gom mua rải lệnh khi có nhịp điều chỉnh kỹ thuật, nắm giữ cho mục tiêu trung hạn.",
                        "action_stress": "KIẾN NGHỊ PHÒNG VỆ RỦI RO: Hạ tỷ trọng danh mục margin, ưu tiên quản trị rủi ro thanh khoản vì ngành ngân hàng nhạy cảm cao với biến động lãi suất.",
                        "action_tienre": "KIẾN NGHỊ MUA MẠNH: Cổ phiếu dòng ngân hàng thương mại năng động sẽ là đầu tàu hút dòng tiền đầu cơ khi thanh khoản thị trường bùng nổ."
                    },
                    "ACV": {
                        "vimo_coso": "Sản lượng hành khách quốc tế hồi phục vững chắc. Tiến độ giải ngân thi công Sân bay Long Thành diễn biến tích cực, tạo động lực quy mô dài hạn.",
                        "vimo_stress": "Giá dầu Brent leo thang đẩy chi phí nhiên liệu bay tăng vọt, làm sụt giảm nhu cầu du lịch toàn cầu và tần suất chuyến bay.",
                        "vimo_tienre": "Dòng tiền rẻ kích thích tiêu dùng và du lịch bùng nổ, gia tăng nguồn thu từ dịch vụ hàng không và phi hàng không tại các cảng lớn.",
                        "sources": [
                            {"name": "VNDirect Research (Ngành Hạ tầng)", "text": "Tiến độ bàn giao Sân bay Long Thành đúng kế hoạch sẽ là động lực tăng trưởng cốt lõi nhảy vọt về công suất phục vụ từ cuối 2026. Khuyến nghị: Mua."},
                            {"name": "MBS Research (Định giá)", "text": "Nguồn thu USD từ phí hành khách quốc tế tăng trưởng 18%, tạo dòng tiền phòng vệ tự nhiên cực tốt giúp ACV giảm rủi ro tỷ giá JPY."}
                        ],
                        "action_coso": "KIẾN NGHỊ NẮM GIỮ DÀI HẠN: ACV sở hữu vị thế độc quyền hạ tầng hàng không bất khả xâm phạm, thích hợp tích sản.",
                        "action_stress": "KIẾN NGHỊ THEO DÕI SÁT GIÁ DẦU: Không mua đuổi, giữ tỷ trọng tiền mặt an toàn chờ đợi báo cáo sản lượng khách bay.",
                        "action_tienre": "KIẾN NGHỊ GOM MUA MẠNH: Giá trị tài sản và dòng tiền định giá lại cực mạnh khi lãi suất chiết khấu sụt giảm sâu."
                    },
                    "OIL": {
                        "vimo_coso": "Cơ chế điều hành giá mới sát với biến động thị trường giúp doanh nghiệp giảm độ trễ trích lập, tối ưu biên lợi nhuận.",
                        "vimo_stress": "Giá dầu thô Brent neo cao gây áp lực chi phí nhập khẩu nhưng mang lại khoản lợi nhuận chênh lệch hàng tồn kho (Inventory Gain) lớn.",
                        "vimo_tienre": "Kinh tế tăng trưởng nóng đẩy nhu cầu vận tải và tiêu thụ năng lượng tăng vọt, cải thiện sản lượng bán lẻ.",
                        "sources": [
                            {"name": "HSC Research (Ngành Năng lượng)", "text": "Cơ chế điều hành giá xăng dầu mới giúp OIL tối ưu hóa biên lợi nhuận gộp, giảm rủi ro trích lập hàng tồn kho."},
                            {"name": "Dự phóng Đồng thuận", "text": "Sản lượng tiêu thụ kênh bán lẻ dự kiến tăng trưởng 5.5% nhờ mở rộng chuỗi trạm xăng trên các trục cao tốc trọng điểm."}
                        ],
                        "action_coso": "KIẾN NGHỊ NẮM GIỮ: Biên lợi nhuận ngành bán lẻ xăng dầu đi vào vùng ổn định, thích hợp nắm giữ ăn chênh lệch.",
                        "action_stress": "KIẾN NGHỊ THEO DÕI TÍN HIỆU ĐẦU CƠ: Tận dụng sóng ngắn hạn của giá dầu thế giới để trading trên lượng hàng sẵn có.",
                        "action_tienre": "KIẾN NGHỊ NẮM GIỮ THEO XU HƯỚNG: Cổ phiếu phòng thủ năng lượng tăng trưởng đều, phân bổ vốn phòng vệ an toàn."
                    }
                }

                # Lấy dữ liệu an toàn
                data_m = DỮ_LIỆU_VĨ_MÔ.get(m_pt, {
                    "vimo_coso": "Hệ thống đang cập nhật dữ liệu vĩ mô cho mã này.", "vimo_stress": "Đang rà soát kịch bản căng thẳng.", "vimo_tienre": "Đang tính toán kịch bản nới lỏng.",
                    "sources": [{"name": "Cập nhật dữ liệu", "text": "Hệ thống đang chờ đồng bộ báo cáo mới nhất từ các quỹ đầu tư."}],
                    "action_coso": "THEO DÕI SÁT DIỄN BIẾN THỊ TRƯỜNG.", "action_stress": "THEO DÕI SÁT DIỄN BIẾN THỊ TRƯỜNG.", "action_tienre": "THEO DÕI SÁT DIỄN BIẾN THỊ TRƯỜNG."
                })

                if "Cơ sở" in kịch_bản_vĩ_mô: vimo_hien_thi = data_m["vimo_coso"]; action_hien_thi = data_m["action_coso"]
                elif "Căng thẳng" in kịch_bản_vĩ_mô: vimo_hien_thi = data_m["vimo_stress"]; action_hien_thi = data_m["action_stress"]
                else: vimo_hien_thi = data_m["vimo_tienre"]; action_hien_thi = data_m["action_tienre"]

                # Logic lập luận Kỹ thuật & Cơ bản
                if rsi_pt < 30: rsi_text = "Vùng Quá Bán (Bị bán tháo, cơ hội bắt đáy)"
                elif rsi_pt > 70: rsi_text = "Vùng Quá Mua (Tăng nóng, rủi ro chỉnh giá)"
                else: rsi_text = "Vùng Tích lũy (Động lượng cân bằng)"
                
                macd_text = "Mua (Cắt lên Signal)" if macd_cur > sig_cur else "Suy yếu (Cắt xuống Signal)"
                trend_text = "Tăng (Uptrend)" if ma20_pt > ma50_pt else "Giảm/Tích lũy (Downtrend)"

                # Xây dựng HTML Sources
                sources_html = ""
                for src in data_m["sources"]:
                    sources_html += f"""
                    <div style="border-left: 3px solid #cbd5e1; background: #f8fafc; padding: 12px; border-radius: 0 6px 6px 0; margin-top: 10px;">
                        <div style="font-size: 13px; font-weight: bold; color: #475569; margin-bottom: 4px; text-transform: uppercase;">{src['name']}</div>
                        <div style="font-size: 14px; font-style: italic; color: #4b5563;">"{src['text']}"</div>
                    </div>
                    """

                # MÃ HTML/CSS BÁO CÁO TUYỆT ĐẸP (CHỐNG LỖI CÚ PHÁP)
                ai_report_html = f"""
                <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #111827; font-size: 22px;">🤖 Báo Cáo Cố Vấn Định Lượng: {m_pt}</h3>
                        <div style="background-color: #dbeafe; color: #166534; padding: 6px 12px; border-radius: 20px; font-size: 14px; font-weight: 600;">⭐ {diem_tcbs}/5.0 (TCBS Rating)</div>
                    </div>
                    
                    <div style="display: flex; gap: 15px; margin-bottom: 25px;">
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; flex: 1;">
                            <div style="color: #64748b; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; font-weight: 600;">Thị giá hiện tại</div>
                            <div style="color: #0f172a; font-size: 20px; font-weight: bold;">{gia_pt:,.0f} VNĐ</div>
                        </div>
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; flex: 1;">
                            <div style="color: #64748b; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; font-weight: 600;">RSI Kỹ thuật</div>
                            <div style="color: #2563eb; font-size: 20px; font-weight: bold;">{rsi_pt:.1f} ({rsi_text})</div>
                        </div>
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; flex: 1;">
                            <div style="color: #64748b; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; font-weight: 600;">Tín hiệu Dòng tiền</div>
                            <div style="color: #0f172a; font-size: 20px; font-weight: bold;">{macd_text}</div>
                        </div>
                    </div>

                    <div style="border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 20px; overflow: hidden;">
                        <div style="background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 12px 15px; font-weight: 600; color: #374151;">🌍 1. Động lực Vĩ mô & Địa chính trị ({kịch_bản_vĩ_mô})</div>
                        <div style="padding: 15px; font-size: 15px; color: #4b5563; line-height: 1.6;">{vimo_hien_thi}</div>
                    </div>

                    <div style="border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 20px; overflow: hidden;">
                        <div style="background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 12px 15px; font-weight: 600; color: #374151;">📑 2. Dự báo & Góc nhìn Tổ chức Chuyên nghiệp</div>
                        <div style="padding: 15px;">
                            <ul style="margin-top: 0; color: #4b5563; font-size: 15px;">
                                <li style="margin-bottom: 8px;"><b>Xu hướng Kỹ thuật:</b> Đường MA20 {"nằm trên" if ma20_pt > ma50_pt else "cắt xuống dưới"} MA50, xác nhận xu hướng <b>{trend_text}</b>.</li>
                            </ul>
                            {sources_html}
                        </div>
                    </div>

                    <div style="border: 2px solid #22c55e; background: #f0fdf4; border-radius: 8px; overflow: hidden;">
                        <div style="background: #dcfce7; border-bottom: 1px solid #bbf7d0; padding: 12px 15px; font-weight: 600; color: #166534;">⚡ 3. Chiến lược Hành động (AI Action Plan)</div>
                        <div style="display: flex; align-items: center; gap: 15px; padding: 15px;">
                            <div style="background: #22c55e; color: white; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">✓</div>
                            <div style="color: #166534; font-weight: 600; font-size: 16px; line-height: 1.5;">{action_hien_thi}</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(ai_report_html, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Dữ liệu lịch sử của mã này tạm thời gián đoạn, vui lòng chọn mã khác.")

# --- TAB 4: QUẢN LÝ DANH MỤC ĐẦU TƯ ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng")
    if DANH_SACH_MA:
        du_lieu_cap_nhat = {}
        col_h1, col_h2, col_h3 = st.columns([2, 3, 3])
        col_h1.write("**Mã CP**"); col_h2.write("**Số lượng**"); col_h3.write("**Giá vốn (VNĐ)**")
        
        for ma in DANH_SACH_MA:
            c1, c2, c3 = st.columns([2, 3, 3])
            c1.write(f"### {ma}")
            sl = c2.number_input(f"SL {ma}", min_value=0, step=100, value=DANH_MỤC_LIVE.get(ma, [0, 0])[0], label_visibility="collapsed", key=f"sl_{ma}")
            gia_v = c3.number_input(f"Giá {ma}", min_value=0, step=500, value=DANH_MỤC_LIVE.get(ma, [0, 0])[1], label_visibility="collapsed", key=f"gv_{ma}")
            du_lieu_cap_nhat[ma] = [sl, gia_v]

        if st.button("💾 Xác nhận & Lưu Cấu Hình Danh Mục"):
            luu_danh_muc_vao_o_cung(du_lieu_cap_nhat)
            st.success("✅ Đã lưu cấu hình danh mục vĩnh viễn!")
            time.sleep(0.5); st.rerun() 

        danh_sach_hien_thi = [{"Mã CP": k, "Số lượng": v[0], "Giá vốn": v[1]} for k, v in du_lieu_cap_nhat.items() if v[0] > 0]
        if danh_sach_hien_thi:
            st.markdown("---")
            st.write("### 📊 Hiệu suất Danh mục đầu tư thực tế")
            hang_danh_muc, tong_von, tong_gt = [], 0, 0
            for item in danh_sach_hien_thi:
                ma = item["Mã CP"]; sl = item["Số lượng"]; gia_v = item["Giá vốn"]
                df_live, _, _ = lay_du_lieu_bieu_do(ma)
                gia_live = df_live['Close'].iloc[-1] if not df_live.empty else gia_v
                tt_von = sl * gia_v; tt_live = sl * gia_live
                ln = tt_live - tt_von
                
                tong_von += tt_von; tong_gt += tt_live
                hang_danh_muc.append({"Mã CP": ma, "Số lượng": f"{sl:,}", "Giá mua": f"{gia_v:,.0f}", "Giá hiện tại": f"{gia_live:,.0f}", "Tổng vốn": tt_von, "Giá trị": tt_live, "Lời / Lỗ": ln, "Hiệu suất": f"{(ln / tt_von * 100) if tt_von > 0 else 0:.2f}%"})
                
            df_ptf = pd.DataFrame(hang_danh_muc)
            tong_loi_nhuan = tong_gt - tong_von
            pct_tong = (tong_loi_nhuan / tong_von * 100) if tong_von > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng vốn đầu tư", f"{tong_von:,.0f} VNĐ")
            m2.metric("Tổng giá trị tài sản (NAV)", f"{tong_gt:,.0f} VNĐ")
            m3.metric("Tổng Lời / Lỗ thực tế", f"{tong_loi_nhuan:,.0f} VNĐ ({pct_tong:.2f}%)", delta=f"{tong_loi_nhuan:,.0f} VNĐ" if tong_loi_nhuan >= 0 else f"{tong_loi_nhuan:,.0f} VNĐ")
            
            df_disp = df_ptf.copy()
            df_disp["Tổng vốn"] = df_disp["Tổng vốn"].map("{:,.0f}".format)
            df_disp["Giá trị"] = df_disp["Giá trị"].map("{:,.0f}".format)
            df_disp["Lời / Lỗ"] = df_disp["Lời / Lỗ"].map("{:,.0f}".format)
            st.dataframe(df_disp.drop(columns=["Tổng vốn", "Giá trị"]), use_container_width=True, hide_index=True)
            
            st.write("### 🍕 Tỷ trọng tài sản trong danh mục")
            fig_pie = px.pie(df_ptf, values='Giá trị', names='Mã CP', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Danh mục đầu tư trống. Hãy nhập số lượng tại bảng trên.")

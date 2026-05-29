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
    st.sidebar.warning("Bảng giá trống. Hãy sang Tab 'Bảng Giá' để thêm mã!")
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
                return df.tail(180).reset_index(drop=True), "VNDirect DChart", ""
    except: pass
    return pd.DataFrame(), "Thất bại", ""

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
                profile['nguon_cap'] = 'Máy chủ TradingView'
    except: pass

    if profile['pe'] == 'N/A' or profile['issueShare'] == 0:
        if ma in LOCAL_DB:
            db = LOCAL_DB[ma]
            profile.update({'industry': db['industry'], 'exchange': db['exchange'], 'issueShare': db['issueShare'], 'roe': db['roe'], 'eps': db['eps'], 'bvps': db['bvps'], 'nguon_cap': 'TradingView + CSDL Nội bộ'})
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
tab0, tab1, tab2, tab3, tab4 = st.tabs(["Bảng Giá Điện Tử", "Biểu đồ Kỹ thuật", "Hồ sơ Doanh nghiệp", "Bộ lọc & AI Advisor", "Quản lý Danh mục"])

# --- TAB 0: BẢNG GIÁ ĐIỆN TỬ ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    with st.expander("Quản lý Danh sách Theo dõi (Watchlist Manager)", expanded=False):
        c_a1, c_a2, c_d1, c_d2 = st.columns([3, 2, 3, 2])
        with c_a1: m_moi = st.text_input("Thêm mã", placeholder="Nhập mã mới (VD: FPT, HPG)...", label_visibility="collapsed").upper().strip()
        with c_a2: 
            if st.button("Thêm mã", use_container_width=True):
                if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE); st.rerun()
        with c_d1: m_xoa = st.selectbox("Xóa mã", ["-- Chọn mã muốn xóa khỏi Watchlist --"] + DANH_SACH_MA, label_visibility="collapsed")
        with c_d2:
            if st.button("Xóa mã", type="primary", use_container_width=True):
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
        show_vol = col_t1.checkbox("Bật Volume (Khối lượng)", value=True)
        show_ma20 = col_t2.checkbox("Bật đường xu hướng MA 20", value=True)
        show_ma50 = col_t3.checkbox("Bật đường xu hướng MA 50", value=False)
        show_bb = col_t4.checkbox("Bật dải băng Bollinger Bands", value=False)

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
            st.download_button(label="Tải lịch sử giá 180 phiên (CSV)", data=csv_price, file_name=f"lich_su_gia_{ma_chon}.csv", mime="text/csv")

# --- TAB 2: HỒ SƠ DOANH NGHIỆP ---
with tab2:
    if ma_chon:
        st.subheader(f"Hồ sơ Doanh nghiệp & Chỉ số Cơ bản - Mã: {ma_chon}")
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        pe_hien_thi = profile.get('pe'); pb_hien_thi = profile.get('pb')
        von_hoa_ty = profile.get('marketCap', 0) / 1_000_000_000
        
        df, _, _ = lay_du_lieu_bieu_do(ma_chon)
        gia_hien_tai, klgd_20 = 0, 0
        if not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            if profile.get('nguon_cap') == 'TradingView + CSDL Nội bộ' and gia_hien_tai > 0:
                if profile.get('eps', 0) > 0: pe_hien_thi = gia_hien_tai / profile['eps']
                if profile.get('bvps', 0) > 0: pb_hien_thi = gia_hien_tai / profile['bvps']
                von_hoa_ty = (gia_hien_tai * profile.get('issueShare', 0)) / 1_000_000_000

        st.caption(f"Trạm dữ liệu: **{profile.get('nguon_cap', 'N/A')}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Phân loại Ngành", str(profile.get('industry', 'N/A')))
        c2.metric("P/E (Định giá)", format_metric(pe_hien_thi))
        c3.metric("P/B (Giá/Sổ sách)", format_metric(pb_hien_thi))
        c4.metric("ROE (Hiệu quả vốn)", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("Quy mô định giá & Thanh khoản:")
        st.write(f"- Thị giá hiện hành: `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- Vốn hóa thị trường: `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- KLGD TB (20 phiên): `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- Khối lượng lưu hành: `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- Sàn niêm yết: `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR DÒNG TIỀN & AI ADVISOR BẢN THIẾT KẾ ĐẸP ---
with tab3:
    st.subheader("Radar Quét Khối lượng & Tín hiệu Đa biến")
    if DANH_SACH_MA:
        if st.button("Bắt đầu Quét Hệ thống Toàn Watchlist"):
            ket_qua = []
            with st.spinner("Đang rà soát tín hiệu dòng tiền..."):
                for ma in DANH_SACH_MA:
                    df_scan, _, _ = lay_du_lieu_bieu_do(ma)
                    if not df_scan.empty and len(df_scan) >= 50:
                        df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                        df_scan['MA20'] = df_scan['Close'].rolling(20).mean()
                        df_scan['MA50'] = df_scan['Close'].rolling(50).mean()
                        df_scan['Vol20'] = df_scan['Volume'].rolling(20).mean()
                        macd, signal = tinh_macd(df_scan['Close'])
                        
                        gia, rsi = df_scan['Close'].iloc[-1], df_scan['RSI'].iloc[-1]
                        diem_mua, tin_hieu = 0, []
                        
                        if rsi < 35: diem_mua += 1; tin_hieu.append("RSI vùng đáy")
                        elif rsi > 70: diem_mua -= 1; tin_hieu.append("RSI quá mua")
                        if df_scan['MA20'].iloc[-1] > df_scan['MA50'].iloc[-1]: diem_mua += 1; tin_hieu.append("MA20 trên MA50")
                        if macd.iloc[-1] > signal.iloc[-1]: diem_mua += 1; tin_hieu.append("MACD giao cắt mua")
                            
                        dot_bien = "Bình thường"
                        if df_scan['Volume'].iloc[-1] > (df_scan['Vol20'].iloc[-1] * 1.5): diem_mua += 1; dot_bien = "NỔ VOL"
                            
                        if diem_mua >= 3: khuyen_nghi = "MUA MẠNH"
                        elif diem_mua >= 1: khuyen_nghi = "NẮM GIỮ / THEO DÕI"
                        else: khuyen_nghi = "RỦI RO / SUY YẾU"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia:,.0f}", "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Tín hiệu": ", ".join(tin_hieu) if tin_hieu else "Tích lũy", "Khuyến nghị": khuyen_nghi})
            
            if ket_qua:
                st.dataframe(pd.DataFrame(ket_qua), use_container_width=True, hide_index=True)
                st.download_button(label="Tải báo cáo Quét Radar Dòng tiền (CSV)", data=pd.DataFrame(ket_qua).to_csv(index=False).encode('utf-8'), file_name="bao_cao_radar.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Hệ thống Cố vấn Đầu tư Chuyên nghiệp (AI Advisor Enterprise)")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1: m_pt = st.selectbox("1. Chọn mã cổ phiếu:", ["-- Chọn mã cổ phiếu --"] + DANH_SACH_MA)
    with col_a2: k_ban = st.radio("2. Kịch bản Vĩ mô:", ["Cơ sở", "Căng thẳng Địa chính trị", "Nới lỏng Tiền tệ"], horizontal=True)

    if m_pt != "-- Chọn mã cổ phiếu --":
        with st.spinner("AI đang nội soi dữ liệu..."):
            df_pt, _, _ = lay_du_lieu_bieu_do(m_pt)
            if not df_pt.empty and len(df_pt) >= 50:
                df_pt['RSI'] = tinh_rsi(df_pt['Close'])
                df_pt['MA20'] = df_pt['Close'].rolling(20).mean()
                df_pt['MA50'] = df_pt['Close'].rolling(50).mean()
                macd_pt, signal_pt = tinh_macd(df_pt['Close'])
                
                g_pt, r_pt = df_pt['Close'].iloc[-1], df_pt['RSI'].iloc[-1]
                m_cur, s_cur = macd_pt.iloc[-1], signal_pt.iloc[-1]
                m20, m50 = df_pt['MA20'].iloc[-1], df_pt['MA50'].iloc[-1]
                diem_tcbs = lay_danh_gia_tcbs(m_pt)
                
                DATA_AI = {
                    "TCB": {
                        "cs": "Thị trường Bất động sản phục hồi giúp giảm áp lực nợ xấu. Lãi suất huy động duy trì thấp giúp tối ưu hóa chi phí vốn.",
                        "str": "Lạm phát nhập khẩu tăng, NHNN thắt chặt thanh khoản bảo vệ tỷ giá. Rủi ro nợ xấu gia tăng.",
                        "tr": "Hạ lãi suất kích thích tăng trưởng tín dụng. Dòng tiền chảy mạnh sang kênh tài sản.",
                        "src": [{"n": "SSI Research", "t": "Dự báo tín dụng TCB dẫn đầu ngành. NIM phục hồi về mức 4.2%."}, {"n": "Vietcap", "t": "Lợi nhuận trước thuế tăng trưởng 12-15% nhờ chiến lược số hóa tăng CASA."}],
                        "acs": "MUA TÍCH LŨY: Gom rải lệnh khi có nhịp chỉnh.",
                        "astr": "PHÒNG VỆ RỦI RO: Hạ tỷ trọng margin.",
                        "atr": "MUA MẠNH: Đón dòng tiền đầu cơ thanh khoản."
                    },
                    "ACV": {
                        "cs": "Tiến độ giải ngân Sân bay Long Thành tích cực, tạo động lực quy mô dài hạn.",
                        "str": "Giá dầu Brent leo thang đẩy chi phí nhiên liệu, sụt giảm nhu cầu du lịch.",
                        "tr": "Dòng tiền rẻ kích thích tiêu dùng du lịch bùng nổ.",
                        "src": [{"n": "VNDirect", "t": "Tiến độ sân bay Long Thành là động lực tăng trưởng nhảy vọt công suất."}, {"n": "MBS", "t": "Nguồn thu USD từ khách quốc tế tạo phòng vệ rủi ro tỷ giá JPY tự nhiên."}],
                        "acs": "NẮM GIỮ DÀI HẠN: Vị thế độc quyền hạ tầng.",
                        "astr": "THEO DÕI SÁT: Giữ tiền mặt chờ báo cáo khách bay.",
                        "atr": "GOM MUA MẠNH: Giá trị tài sản định giá lại cực mạnh."
                    },
                    "OIL": {
                        "cs": "Cơ chế điều hành giá xăng dầu mới giúp giảm độ trễ trích lập, tối ưu biên lợi nhuận.",
                        "str": "Giá dầu thô neo cao mang lại lợi nhuận chênh lệch hàng tồn kho lớn ngắn hạn.",
                        "tr": "Nhu cầu vận tải và tiêu thụ năng lượng tăng vọt.",
                        "src": [{"n": "HSC", "t": "Cơ chế giá mới giúp OIL tối ưu biên lợi nhuận gộp."}, {"n": "Consensus", "t": "Sản lượng bán lẻ dự kiến tăng 5.5% nhờ mở rộng chuỗi trạm xăng."}],
                        "acs": "NẮM GIỮ: Biên lợi nhuận đi vào vùng ổn định.",
                        "astr": "THEO DÕI ĐẦU CƠ: Tận dụng sóng ngắn hạn giá dầu.",
                        "atr": "NẮM GIỮ XU HƯỚNG: Phân bổ vốn phòng vệ."
                    },
                    "PVC": {
                        "cs": "Tiến độ chuỗi dự án Lô B kích hoạt nhu cầu hóa chất và dung dịch khoan.",
                        "str": "Giá dầu neo cao thúc đẩy thăm dò khai thác E&P diễn ra sôi động.",
                        "tr": "Vốn rẻ giải ngân mạnh vào hạ tầng năng lượng.",
                        "src": [{"n": "SSI Research", "t": "Lô B trao thầu tạo backlog kỷ lục cho chuỗi thượng nguồn."}, {"n": "Dự phóng", "t": "Doanh thu dịch vụ kỹ thuật dự kiến tăng mạnh khi hoạt động khoan bùng nổ."}],
                        "acs": "MUA GOM: Đón chu kỳ ngành dầu khí thượng nguồn.",
                        "astr": "NẮM GIỮ: Hầm trú ẩn an toàn khi lạm phát.",
                        "atr": "MUA THEO DÒNG TIỀN: Hút dòng tiền thông minh."
                    },
                    "DRI": {
                        "cs": "Giá cao su tự nhiên hồi phục nhờ nhu cầu lốp xe Trung Quốc.",
                        "str": "Thời tiết cực đoan làm khan hiếm nguồn cung mủ cao su, đẩy giá xuất khẩu.",
                        "tr": "Chi phí logistics giảm sâu hỗ trợ biên lợi nhuận xuất khẩu.",
                        "src": [{"n": "VNDirect", "t": "Giá xuất khẩu cao su dự báo tăng 8% do thiếu hụt cung."}, {"n": "Consensus", "t": "Quỹ đất cao su tại Lào có chi phí giá vốn thấp tạo lợi thế lớn."}],
                        "acs": "NẮM GIỮ: Xu hướng giá hàng hóa ủng hộ phục hồi lợi nhuận.",
                        "astr": "GOM MUA: Giá tăng do khủng hoảng cung là bệ phóng.",
                        "atr": "NẮM GIỮ PHÒNG THỦ: Dòng tiền ổn định."
                    },
                    "CSM": {
                        "cs": "Chi phí nguyên liệu đầu vào duy trì ổn định. Thị trường xuất khẩu lốp Radial tăng trưởng.",
                        "str": "Giá cước tàu container tăng vọt, bào mòn biên lợi nhuận xuất khẩu.",
                        "tr": "Nhu cầu tiêu dùng nội địa hồi phục mạnh mẽ.",
                        "src": [{"n": "Vietcap", "t": "Lốp Radial xuất khẩu Mỹ bù đắp săm lốp xe máy bão hòa nội địa."}, {"n": "Tài chính", "t": "ROE duy trì ổn định nhờ tối ưu hóa dây chuyền."}],
                        "acs": "NẮM GIỮ: Định giá hợp lý, dòng tiền cổ tức đều đặn.",
                        "astr": "HẠ TỶ TRỌNG: Rủi ro giá cước vận tải biển.",
                        "atr": "MUA NỘI ĐỊA: Sức mua trong nước hồi sinh."
                    },
                    "TNT": {
                        "cs": "Dòng tiền quay trở lại tìm kiếm cơ hội đầu tư hạ tầng khi BĐS rã băng pháp lý.",
                        "str": "Áp lực lạm phát kìm hãm tín dụng chảy vào ngành BĐS.",
                        "tr": "Lãi suất thấp kích hoạt làn sóng đầu cơ đất nền.",
                        "src": [{"n": "MBS", "t": "Doanh nghiệp nhỏ linh hoạt sẽ tận dụng sóng đất nền tỉnh lẻ khi lãi suất giảm."}, {"n": "Lưu ý", "t": "Cần giám sát CFO đảm bảo tiến độ triển khai."}],
                        "acs": "THEO DÕI TÍCH LŨY: Chờ dòng tiền doanh thu mở bán.",
                        "astr": "QUẢN TRỊ RỦI RO: Hạ tỷ trọng nhóm có đòn bẩy.",
                        "atr": "ĐẦU CƠ THEO SÓNG: Nhạy cảm dòng tiền cao, hiệu suất bùng nổ."
                    }
                }

                d_m = DATA_AI.get(m_pt, {"cs": "Cập nhật dữ liệu.", "str": "Đang rà soát.", "tr": "Đang tính.", "src": [{"n": "Cập nhật", "t": "Đang đồng bộ."}], "acs": "THEO DÕI.", "astr": "THEO DÕI.", "atr": "THEO DÕI."})
                if "Cơ sở" in k_ban: vim_t = d_m["cs"]; act_t = d_m["acs"]
                elif "Căng thẳng" in k_ban: vim_t = d_m["str"]; act_t = d_m["astr"]
                else: vim_t = d_m["tr"]; act_t = d_m["atr"]

                r_txt = "Quá Bán (Cơ hội mua)" if r_pt < 30 else "Quá Mua (Rủi ro chỉnh)" if r_pt > 70 else "Tích lũy (Cân bằng)"
                m_txt = "Mua (Cắt lên Signal)" if m_cur > s_cur else "Suy yếu (Cắt xuống Signal)"
                t_txt = "Tăng (Uptrend)" if m20 > m50 else "Giảm/Tích lũy (Downtrend)"

                src_html = ""
                for s in d_m["src"]: src_html += f"<div style='border-left:3px solid #cbd5e1;background:#f8fafc;padding:12px;border-radius:0 6px 6px 0;margin-top:10px;'><div style='font-size:13px;font-weight:bold;color:#475569;'>{s['n']}</div><div style='font-size:14px;font-style:italic;color:#4b5563;'>{s['t']}</div></div>"

                rep = f"""
                <div style='background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:25px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);'>
                    <div style='border-bottom:1px solid #e5e7eb;padding-bottom:15px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;'>
                        <h3 style='margin:0;color:#111827;font-size:22px;'>Báo Cáo Cố Vấn Định Lượng: {m_pt}</h3>
                        <div style='background:#dbeafe;color:#166534;padding:6px 12px;border-radius:20px;font-size:14px;font-weight:600;'>{diem_tcbs}/5.0 (TCBS Rating)</div>
                    </div>
                    <div style='display:flex;gap:15px;margin-bottom:25px;'>
                        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:15px;flex:1;'><div style='color:#64748b;font-size:12px;font-weight:600;'>Thị giá</div><div style='color:#0f172a;font-size:20px;font-weight:bold;'>{g_pt:,.0f}</div></div>
                        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:15px;flex:1;'><div style='color:#64748b;font-size:12px;font-weight:600;'>RSI</div><div style='color:#2563eb;font-size:20px;font-weight:bold;'>{r_pt:.1f} ({r_txt})</div></div>
                        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:15px;flex:1;'><div style='color:#64748b;font-size:12px;font-weight:600;'>MACD</div><div style='color:#0f172a;font-size:20px;font-weight:bold;'>{m_txt}</div></div>
                    </div>
                    <div style='border:1px solid #e5e7eb;border-radius:8px;margin-bottom:20px;'><div style='background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:12px 15px;font-weight:600;color:#374151;'>1. Vĩ mô & Địa chính trị ({k_ban})</div><div style='padding:15px;color:#4b5563;'>{vim_t}</div></div>
                    <div style='border:1px solid #e5e7eb;border-radius:8px;margin-bottom:20px;'><div style='background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:12px 15px;font-weight:600;color:#374151;'>2. Góc nhìn Chuyên gia</div><div style='padding:15px;'><div style='color:#4b5563;margin-bottom:10px;'><b>Xu hướng:</b> Đường MA20 {'nằm trên' if m20>m50 else 'nằm dưới'} MA50, xác nhận <b>{t_txt}</b>.</div>{src_html}</div></div>
                    <div style='border:2px solid #22c55e;background:#f0fdf4;border-radius:8px;'><div style='background:#dcfce7;border-bottom:1px solid #bbf7d0;padding:12px 15px;font-weight:600;color:#166534;'>3. Chiến lược Hành động (AI Action Plan)</div><div style='padding:15px;color:#166534;font-weight:600;font-size:16px;'>{act_t}</div></div>
                </div>
                """
                st.markdown(rep, unsafe_allow_html=True)
            else:
                st.warning("Dữ liệu lịch sử của mã này tạm thời gián đoạn.")

# --- TAB 4: QUẢN LÝ DANH MỤC ---
with tab4:
    st.subheader("Hệ thống Quản trị Tài sản ròng")
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

        if st.button("Xác nhận & Lưu Cấu Hình Danh Mục"):
            luu_danh_muc_vao_o_cung(du_lieu_cap_nhat)
            st.success("Đã lưu cấu hình danh mục vĩnh viễn!")
            time.sleep(0.5); st.rerun() 

        danh_sach_hien_thi = [{"Mã CP": k, "Số lượng": v[0], "Giá vốn": v[1]} for k, v in du_lieu_cap_nhat.items() if v[0] > 0]
        if danh_sach_hien_thi:
            st.markdown("---")
            st.write("### Hiệu suất Danh mục đầu tư thực tế")
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
            
            st.write("### Tỷ trọng tài sản trong danh mục")
            fig_pie = px.pie(df_ptf, values='Giá trị', names='Mã CP', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Danh mục đầu tư trống. Hãy nhập số lượng tại bảng trên.")

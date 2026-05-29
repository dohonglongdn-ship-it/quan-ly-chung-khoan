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

# 2. KHU VỰC ĐIỀU KHIỂN ĐỘNG
st.sidebar.header("⚙️ Quản lý Mã Cổ Phiếu")
ma_moi = st.sidebar.text_input("Thêm mã mới (VD: FPT, HPG):").upper().strip()
if st.sidebar.button("➕ Thêm Mã"):
    if ma_moi and ma_moi not in DANH_MỤC_LIVE:
        DANH_MỤC_LIVE[ma_moi] = [0, 0]
        luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
        st.sidebar.success(f"Đã thêm {ma_moi}!")
        time.sleep(0.5); st.rerun()

st.sidebar.markdown("---")
ma_xoa = st.sidebar.selectbox("Chọn mã để xóa khỏi hệ thống:", [""] + DANH_SACH_MA)
if st.sidebar.button("🗑️ Xóa Mã"):
    if ma_xoa and ma_xoa in DANH_MỤC_LIVE:
        del DANH_MỤC_LIVE[ma_xoa]
        luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
        st.sidebar.success(f"Đã xóa {ma_xoa}!")
        time.sleep(0.5); st.rerun()

if not DANH_SACH_MA:
    st.warning("⚠️ Danh mục trống. Hãy thêm mã cổ phiếu.")
    st.stop()

st.sidebar.markdown("---")
ma_chon = st.sidebar.selectbox("Phân tích chuyên sâu:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ LIVE ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
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

# --- TOÁN HỌC & ĐỊNH DẠNG ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def tinh_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def format_metric(val, is_pct=False):
    if val in [None, 'N/A', '']: return "N/A"
    try:
        v = float(val)
        if is_pct: return f"{v*100:.2f}%" if abs(v) < 2 else f"{v:.2f}%"
        return f"{v:.2f}"
    except: return "N/A"

# 3. GIAO DIỆN CHÍNH (5 TABS)
tab0, tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Bảng Giá Điện Tử", "📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ", "📡 Radar Dòng tiền", "💼 Danh mục"])

# --- TAB 0: BẢNG GIÁ ĐIỆN TỬ PRO ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    
    # Ép HTML hiển thị thẳng một dòng để không bị dính lỗi Markdown Code Block
    css_bang_gia = "<style>.stock-board-container{width:100%;overflow-x:auto;background-color:#111;padding:10px;border-radius:8px;}.stock-board{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:14px;background-color:#111;color:#fff;}.stock-board th,.stock-board td{border:1px solid #333;padding:8px 12px;text-align:right;white-space:nowrap;}.stock-board th{background-color:#222;color:#ccc;text-align:center;font-weight:bold;}.col-ma{text-align:left!important;font-weight:bold;}.c-ref{color:#F2C94C!important;}.c-ceil{color:#E040FB!important;}.c-floor{color:#00E5FF!important;}.c-up{color:#00E676!important;}.c-down{color:#FF5252!important;}</style>"
    html_content = css_bang_gia + '<div class="stock-board-container"><table class="stock-board">'
    html_content += "<tr><th>Mã</th><th class='c-ref'>TC</th><th class='c-ceil'>Trần</th><th class='c-floor'>Sàn</th><th>Khớp Lệnh</th><th>+/-</th><th>%</th><th>Tổng KL</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th></tr>"
    
    with st.spinner("Đang kết nối trạm giao dịch..."):
        for ma in DANH_SACH_MA:
            df, _, _ = lay_du_lieu_bieu_do(ma)
            if df.empty or len(df) < 2: continue
                
            san = lay_ho_so_doanh_nghiep(ma).get('exchange', 'HOSE')
            bien_do = 0.15 if san == 'UPCOM' else (0.10 if san == 'HNX' else 0.07)
            
            tc = df['Close'].iloc[-2]
            gia_hien_tai = df['Close'].iloc[-1]
            mo_cua = df['Open'].iloc[-1]
            cao_nhat = df['High'].iloc[-1]
            thap_nhat = df['Low'].iloc[-1]
            tong_kl = df['Volume'].iloc[-1]
            
            tran = round(tc * (1 + bien_do) / 100) * 100
            san_gia = round(tc * (1 - bien_do) / 100) * 100
            
            thay_doi = gia_hien_tai - tc
            phan_tram = (thay_doi / tc) * 100 if tc > 0 else 0
            
            def xac_dinh_mau(gia):
                if gia >= tran: return "c-ceil"
                if gia <= san_gia: return "c-floor"
                if gia > tc: return "c-up"
                if gia < tc: return "c-down"
                return "c-ref"
                
            mau_gia = xac_dinh_mau(gia_hien_tai)
            mau_mo = xac_dinh_mau(mo_cua)
            mau_cao = xac_dinh_mau(cao_nhat)
            mau_thap = xac_dinh_mau(thap_nhat)
            dau_c = "+" if thay_doi > 0 else ""
            
            # Gắn HTML không có thụt dòng để chống lỗi
            html_content += f"<tr><td class='col-ma {mau_gia}'>{ma}</td><td class='c-ref'>{tc:,.0f}</td><td class='c-ceil'>{tran:,.0f}</td><td class='c-floor'>{san_gia:,.0f}</td><td class='{mau_gia}' style='font-weight:bold;'>{gia_hien_tai:,.0f}</td><td class='{mau_gia}'>{dau_c}{thay_doi:,.0f}</td><td class='{mau_gia}'>{dau_c}{phan_tram:.2f}%</td><td>{tong_kl:,.0f}</td><td class='{mau_mo}'>{mo_cua:,.0f}</td><td class='{mau_cao}'>{cao_nhat:,.0f}</td><td class='{mau_thap}'>{thap_nhat:,.0f}</td></tr>"
            
    html_content += "</table></div>"
    st.markdown(html_content, unsafe_allow_html=True)

# --- TAB 1: BIỂU ĐỒ KỸ THUẬT ---
with tab1:
    st.subheader(f"Trung tâm Phân tích Kỹ thuật - Mã: {ma_chon}")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    show_vol = col_t1.checkbox("📊 Bật Volume", value=True)
    show_ma20 = col_t2.checkbox("📈 Bật MA 20", value=True)
    show_ma50 = col_t3.checkbox("📉 Bật MA 50", value=False)
    show_bb = col_t4.checkbox("🌐 Bật Bollinger Bands", value=False)

    df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
    if not df.empty:
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['MA20'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['MA20'] - (df['BB_Std'] * 2)

        fig = make_subplots(rows=2 if show_vol else 1, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25] if show_vol else None)
        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá"), row=1, col=1)

        if show_ma20: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], mode='lines', name='MA 20', line=dict(color='#2962FF')), row=1, col=1)
        if show_ma50: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA50'], mode='lines', name='MA 50', line=dict(color='#FF6D00')), row=1, col=1)
        if show_bb:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='gray', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='gray', dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

        if show_vol:
            vol_colors = ['#26A69A' if row['Close'] >= row['Open'] else '#EF5350' for i, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color=vol_colors), row=2, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20), height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: HỒ SƠ DOANH NGHIỆP ---
with tab2:
    st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
    with st.spinner("Đang đồng bộ Dữ liệu..."):
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap')}**")
        
        pe_hien_thi = profile.get('pe')
        pb_hien_thi = profile.get('pb')
        von_hoa_ty = profile.get('marketCap', 0) / 1_000_000_000
        
        gia_hien_tai = 0
        klgd_20 = 0
        if 'df' in locals() and not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            if profile.get('nguon_cap') == 'TradingView + CSDL Nội bộ 🟢' and gia_hien_tai > 0:
                if profile['eps'] > 0: pe_hien_thi = gia_hien_tai / profile['eps']
                if profile['bvps'] > 0: pb_hien_thi = gia_hien_tai / profile['bvps']
                von_hoa_ty = (gia_hien_tai * profile['issueShare']) / 1_000_000_000

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        col2.metric("P/E (Định giá)", format_metric(pe_hien_thi))
        col3.metric("P/B (Giá/Sổ sách)", format_metric(pb_hien_thi))
        col4.metric("ROE (Biên LN)", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("📌 **Quy mô doanh nghiệp & Giao dịch:**")
        st.write(f"- **Thị giá hiện tại:** `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- **KLGD trung bình (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- **Tổng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR DÒNG TIỀN ---
with tab3:
    st.subheader("Radar Quét Khối lượng & Tín hiệu Đa biến")
    if st.button("🚀 Kích hoạt Radar Quét Toàn Thị Trường"):
        ket_qua = []
        with st.spinner("Đang phân tích tín hiệu dòng tiền..."):
            for ma in DANH_SACH_MA:
                df_scan, _, _ = lay_du_lieu_bieu_do(ma)
                if not df_scan.empty and len(df_scan) >= 50:
                    df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                    df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                    df_scan['MA50'] = df_scan['Close'].rolling(window=50).mean()
                    df_scan['Vol20'] = df_scan['Volume'].rolling(window=20).mean()
                    macd, signal = tinh_macd(df_scan['Close'])
                    
                    gia = df_scan['Close'].iloc[-1]
                    rsi = df_scan['RSI'].iloc[-1]
                    ma20 = df_scan['MA20'].iloc[-1]
                    ma50 = df_scan['MA50'].iloc[-1]
                    vol = df_scan['Volume'].iloc[-1]
                    vol_20 = df_scan['Vol20'].iloc[-1]
                    macd_cur = macd.iloc[-1]
                    sig_cur = signal.iloc[-1]
                    
                    diem_mua = 0
                    tin_hieu = []
                    
                    if rsi < 35: diem_mua += 1; tin_hieu.append("RSI vùng đáy")
                    elif rsi > 70: diem_mua -= 1; tin_hieu.append("RSI vùng đỉnh")
                        
                    if ma20 > ma50: diem_mua += 1; tin_hieu.append("MA Crossover")
                    if macd_cur > sig_cur: diem_mua += 1; tin_hieu.append("MACD Báo mua")
                        
                    dot_bien = "Bình thường"
                    if vol > (vol_20 * 1.5): 
                        diem_mua += 1
                        dot_bien = "⭐ NỔ VOL DÒNG TIỀN"
                        
                    if diem_mua >= 3: khuyen_nghi = "🟢 MUA MẠNH"
                    elif diem_mua >= 1: khuyen_nghi = "🟡 NẮM GIỮ"
                    else: khuyen_nghi = "🔴 RỦI RO / BÁN"
                        
                    ket_qua.append({"Mã CP": ma, "Giá": f"{gia:,.0f}", "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Hội tụ Kỹ thuật": ", ".join(tin_hieu) if tin_hieu else "Suy yếu", "Hành động": khuyen_nghi})
        
        if ket_qua:
            df_kq = pd.DataFrame(ket_qua)
            st.dataframe(df_kq, use_container_width=True, hide_index=True)

# --- TAB 4: QUẢN LÝ DANH MỤC TÍCH HỢP BỘ LƯU TRỮ ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng")
    st.markdown("Thay đổi khối lượng và giá vốn, sau đó bấm nút **Lưu** ở cuối bảng để hệ thống tự động tính toán.")

    du_lieu_cap_nhat = {}
    col_h1, col_h2, col_h3 = st.columns([2, 3, 3])
    col_h1.write("**Mã CP**")
    col_h2.write("**Số lượng nắm giữ**")
    col_h3.write("**Giá vốn (VNĐ)**")
    
    for ma in DANH_SACH_MA:
        c1, c2, c3 = st.columns([2, 3, 3])
        c1.write(f"### {ma}")
        sl_mac_dinh = DANH_MỤC_LIVE.get(ma, [0, 0])[0]
        gia_mac_dinh = DANH_MỤC_LIVE.get(ma, [0, 0])[1]
        
        sl = c2.number_input(f"SL {ma}", min_value=0, step=100, value=sl_mac_dinh, label_visibility="collapsed", key=f"sl_{ma}")
        gia_v = c3.number_input(f"Giá {ma}", min_value=0, step=500, value=gia_mac_dinh, label_visibility="collapsed", key=f"gv_{ma}")
        du_lieu_cap_nhat[ma] = [sl, gia_v]

    if st.button("💾 Xác nhận & Lưu Cấu Hình Danh Mục"):
        luu_danh_muc_vao_o_cung(du_lieu_cap_nhat)
        st.success("✅ Đã lưu cấu hình danh mục vĩnh viễn!")
        time.sleep(1); st.rerun() 

    danh_sach_hien_thi = [{"Mã CP": k, "Số lượng": v[0], "Giá vốn": v[1]} for k, v in du_lieu_cap_nhat.items() if v[0] > 0]

    if danh_sach_hien_thi:
        st.markdown("---")
        st.write("### 📊 Hiệu suất Danh mục đầu tư thực tế")
        hang_danh_muc, tong_von, tong_gia_tri_hien_tai = [], 0, 0
        
        for item in danh_sach_hien_thi:
            ma = item["Mã CP"]; sl = item["Số lượng"]; gia_v = item["Giá vốn"]
            df_live, _, _ = lay_du_lieu_bieu_do(ma)
            gia_live = df_live['Close'].iloc[-1] if not df_live.empty else gia_v
            
            thanh_tien_von = sl * gia_v
            thanh_tien_live = sl * gia_live
            loi_nhuan = thanh_tien_live - thanh_tien_von
            phan_tram_lh = (loi_nhuan / thanh_tien_von * 100) if thanh_tien_von > 0 else 0
            
            tong_von += thanh_tien_von
            tong_gia_tri_hien_tai += thanh_tien_live
            
            hang_danh_muc.append({
                "Mã CP": ma, "Số lượng": f"{sl:,}", "Giá vốn": f"{gia_v:,.0f}", "Giá hiện tại": f"{gia_live:,.0f}",
                "Tổng vốn đầu tư": thanh_tien_von, "Giá trị hiện tại": thanh_tien_live, "Lời / Lỗ": loi_nhuan, "Hiệu suất": f"{phan_tram_lh:.2f}%"
            })
            
        df_portfolio = pd.DataFrame(hang_danh_muc)
        tong_loi_nhuan = tong_gia_tri_hien_tai - tong_von
        pct_tong = (tong_loi_nhuan / tong_von * 100) if tong_von > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng vốn đầu tư", f"{tong_von:,.0f} VNĐ")
        m2.metric("Tổng giá trị tài sản", f"{tong_gia_tri_hien_tai:,.0f} VNĐ")
        m3.metric("Tổng Lời / Lỗ", f"{tong_loi_nhuan:,.0f} VNĐ ({pct_tong:.2f}%)", delta=f"{tong_loi_nhuan:,.0f} VNĐ" if tong_loi_nhuan >= 0 else f"{tong_loi_nhuan:,.0f} VNĐ")
        
        df_hien_thi = df_portfolio.copy()
        df_hien_thi["Tổng vốn đầu tư"] = df_hien_thi["Tổng vốn đầu tư"].map("{:,.0f}".format)
        df_hien_thi["Giá trị hiện tại"] = df_hien_thi["Giá trị hiện tại"].map("{:,.0f}".format)
        df_hien_thi["Lời / Lỗ"] = df_hien_thi["Lời / Lỗ"].map("{:,.0f}".format)
        st.dataframe(df_hien_thi, use_container_width=True, hide_index=True)
        
        fig_pie = px.pie(df_portfolio, values='Giá trị hiện tại', names='Mã CP', hole=0.4)
        fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

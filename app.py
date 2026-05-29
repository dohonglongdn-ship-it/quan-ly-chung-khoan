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

# 3. GIAO DIỆN CHÍNH
tab0, tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Bảng Giá Điện Tử", "📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ", "📡 Radar Dòng tiền", "💼 Danh mục"])

# --- TAB 0: BẢNG GIÁ ĐIỆN TỬ ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    with st.expander("⚙️ Quản lý Mã Cổ Phiếu trên Bảng Giá", expanded=False):
        col_add1, col_add2, col_del1, col_del2 = st.columns([3, 2, 3, 2])
        with col_add1:
            ma_moi = st.text_input("Thêm mã", placeholder="Nhập mã (VD: FPT)...", label_visibility="collapsed").upper().strip()
        with col_add2:
            if st.button("➕ Thêm vào Bảng", use_container_width=True):
                if ma_moi and ma_moi not in DANH_MỤC_LIVE:
                    DANH_MỤC_LIVE[ma_moi] = [0, 0]
                    luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
                    st.rerun()
        with col_del1:
            ma_xoa = st.selectbox("Xóa mã", ["-- Chọn mã để xóa --"] + DANH_SACH_MA, label_visibility="collapsed")
        with col_del2:
            if st.button("🗑️ Loại khỏi Bảng", type="primary", use_container_width=True):
                if ma_xoa and ma_xoa != "-- Chọn mã để xóa --" and ma_xoa in DANH_MỤC_LIVE:
                    del DANH_MỤC_LIVE[ma_xoa]
                    luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
                    st.rerun()

    css_bang_gia = "<style>.stock-board-container{width:100%;overflow-x:auto;background-color:#111;padding:10px;border-radius:8px;}.stock-board{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:14px;background-color:#111;color:#fff;}.stock-board th,.stock-board td{border:1px solid #333;padding:8px 12px;text-align:right;white-space:nowrap;}.stock-board th{background-color:#222;color:#ccc;text-align:center;font-weight:bold;}.col-ma{text-align:left!important;font-weight:bold;}.c-ref{color:#F2C94C!important;}.c-ceil{color:#E040FB!important;}.c-floor{color:#00E5FF!important;}.c-up{color:#00E676!important;}.c-down{color:#FF5252!important;}</style>"
    html_content = css_bang_gia + '<div class="stock-board-container"><table class="stock-board"><tr><th>Mã</th><th class="c-ref">TC</th><th class="c-ceil">Trần</th><th class="c-floor">Sàn</th><th>Khớp Lệnh</th><th>+/-</th><th>%</th><th>Tổng KL</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th></tr>'
    
    with st.spinner("Đang cập nhật luồng giá..."):
        if DANH_SACH_MA:
            for ma in DANH_SACH_MA:
                df, _, _ = lay_du_lieu_bieu_do(ma)
                if df.empty or len(df) < 2: continue
                san = lay_ho_so_doanh_nghiep(ma).get('exchange', 'HOSE')
                bien_do = 0.15 if san == 'UPCOM' else (0.10 if san == 'HNX' else 0.07)
                tc, gia_hien_tai, mo_cua, cao_nhat, thap_nhat, tong_kl = df['Close'].iloc[-2], df['Close'].iloc[-1], df['Open'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1], df['Volume'].iloc[-1]
                tran, san_gia = round(tc * (1 + bien_do) / 100) * 100, round(tc * (1 - bien_do) / 100) * 100
                thay_doi, phan_tram = gia_hien_tai - tc, (gia_hien_tai - tc) / tc * 100 if tc > 0 else 0
                
                def xac_dinh_mau(gia): return "c-ceil" if gia >= tran else "c-floor" if gia <= san_gia else "c-up" if gia > tc else "c-down" if gia < tc else "c-ref"
                mau_gia, dau_c = xac_dinh_mau(gia_hien_tai), "+" if thay_doi > 0 else ""
                html_content += f"<tr><td class='col-ma {mau_gia}'>{ma}</td><td class='c-ref'>{tc:,.0f}</td><td class='c-ceil'>{tran:,.0f}</td><td class='c-floor'>{san_gia:,.0f}</td><td class='{mau_gia}' style='font-weight:bold;'>{gia_hien_tai:,.0f}</td><td class='{mau_gia}'>{dau_c}{thay_doi:,.0f}</td><td class='{mau_gia}'>{dau_c}{phan_tram:.2f}%</td><td>{tong_kl:,.0f}</td><td class='{xac_dinh_mau(mo_cua)}'>{mo_cua:,.0f}</td><td class='{xac_dinh_mau(cao_nhat)}'>{cao_nhat:,.0f}</td><td class='{xac_dinh_mau(thap_nhat)}'>{thap_nhat:,.0f}</td></tr>"
        else: html_content += "<tr><td colspan='11' style='text-align:center;'>Danh mục trống.</td></tr>"
    html_content += "</table></div>"
    st.markdown(html_content, unsafe_allow_html=True)

# --- TAB 1: BIỂU ĐỒ KỸ THUẬT ---
with tab1:
    if ma_chon:
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

# --- TAB 2: HỒ SƠ DOANH NGHIỆP (PHỤC HỒI HOÀN TOÀN) ---
with tab2:
    if ma_chon:
        st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
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

        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap', 'N/A')}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        c2.metric("P/E (Định giá)", format_metric(pe_hien_thi))
        c3.metric("P/B", format_metric(pb_hien_thi))
        c4.metric("ROE", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("📌 **Quy mô doanh nghiệp & Giao dịch:**")
        st.write(f"- **Thị giá hiện tại:** `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- **KLGD trung bình (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- **Tổng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR & BÁO CÁO PHÂN TÍCH CHUYÊN SÂU ---
with tab3:
    st.subheader("📡 Radar Quét Khối lượng & Tín hiệu Đa biến")
    if DANH_SACH_MA:
        if st.button("🚀 Kích hoạt Radar Quét Toàn Thị Trường"):
            ket_qua = []
            with st.spinner("Đang phân tích tín hiệu..."):
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
                        
                        if rsi < 35: diem_mua += 1; tin_hieu.append("RSI đáy")
                        elif rsi > 70: diem_mua -= 1; tin_hieu.append("RSI đỉnh")
                        if df_scan['MA20'].iloc[-1] > df_scan['MA50'].iloc[-1]: diem_mua += 1; tin_hieu.append("MA Crossover")
                        if macd.iloc[-1] > signal.iloc[-1]: diem_mua += 1; tin_hieu.append("MACD Báo mua")
                            
                        dot_bien = "Bình thường"
                        if df_scan['Volume'].iloc[-1] > (df_scan['Vol20'].iloc[-1] * 1.5): 
                            diem_mua += 1; dot_bien = "⭐ NỔ VOL"
                            
                        if diem_mua >= 3: khuyen_nghi = "🟢 MUA MẠNH"
                        elif diem_mua >= 1: khuyen_nghi = "🟡 NẮM GIỮ"
                        else: khuyen_nghi = "🔴 RỦI RO"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia:,.0f}", "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Tín hiệu": ", ".join(tin_hieu) if tin_hieu else "Suy yếu", "Khuyến nghị": khuyen_nghi})
                    time.sleep(0.1) 
            
            if ket_qua: st.dataframe(pd.DataFrame(ket_qua), use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.subheader("🤖 Trợ lý Phân tích Chuyên sâu (AI Advisor)")
        ma_phan_tich = st.selectbox("Chọn mã từ Radar để đọc báo cáo chi tiết:", ["-- Chọn mã --"] + DANH_SACH_MA)
        
        if ma_phan_tich != "-- Chọn mã --":
            with st.spinner(f"Đang tổng hợp dữ liệu Phân tích Kỹ thuật, Cơ bản và Đánh giá chuyên gia cho {ma_phan_tich}..."):
                df_pt, _, _ = lay_du_lieu_bieu_do(ma_phan_tich)
                if not df_pt.empty and len(df_pt) >= 50:
                    df_pt['RSI'] = tinh_rsi(df_pt['Close'])
                    df_pt['MA20'] = df_pt['Close'].rolling(window=20).mean()
                    df_pt['MA50'] = df_pt['Close'].rolling(window=50).mean()
                    macd_pt, signal_pt = tinh_macd(df_pt['Close'])
                    
                    gia_pt = df_pt['Close'].iloc[-1]
                    rsi_pt = df_pt['RSI'].iloc[-1]
                    ma20_pt = df_pt['MA20'].iloc[-1]
                    ma50_pt = df_pt['MA50'].iloc[-1]
                    macd_cur = macd_pt.iloc[-1]
                    sig_cur = signal_pt.iloc[-1]
                    
                    ho_so_pt = lay_ho_so_doanh_nghiep(ma_phan_tich)
                    pe_pt = ho_so_pt.get('pe', 'N/A')
                    
                    diem_tcbs = lay_danh_gia_tcbs(ma_phan_tich)
                    danh_gia_chuyen_gia = f"**{diem_tcbs}/5.0 Sao** (Nguồn: TCBS API)" if diem_tcbs > 0 else "Chưa có báo cáo định giá cập nhật."
                    
                    if rsi_pt < 30: rsi_text = f"RSI đang ở mức **{rsi_pt:.1f}** (Vùng quá bán). Cổ phiếu đã bị bán tháo quá mức, đây là cơ hội tốt để bắt đáy ngắn hạn."
                    elif rsi_pt > 70: rsi_text = f"RSI đang ở mức **{rsi_pt:.1f}** (Vùng quá mua). Giá đã tăng nóng, lực cầu đang hưng phấn thái quá, rủi ro điều chỉnh (đạp giá) là rất cao."
                    else: rsi_text = f"RSI đang ở mức **{rsi_pt:.1f}**. Động lượng giá đang ở trạng thái cân bằng, chưa có dấu hiệu kéo xả rõ rệt."
                    
                    if ma20_pt > ma50_pt: xu_huong_text = "Đường MA20 nằm trên MA50, xác nhận cổ phiếu đang duy trì **Xu hướng Tăng (Uptrend)** tích cực."
                    else: xu_huong_text = "Đường MA20 cắt xuống dưới MA50, cảnh báo cổ phiếu đang rơi vào **Xu hướng Giảm (Downtrend)** hoặc tái tích lũy."
                    
                    if pe_pt != 'N/A':
                        try:
                            pe_val = float(pe_pt)
                            if pe_val < 10: pe_text = f"Chỉ số P/E đạt **{pe_val:.2f}**. Mức định giá này đang khá **rẻ** so với mặt bằng chung thị trường, thích hợp cho đầu tư giá trị dài hạn."
                            elif pe_val > 20: pe_text = f"Chỉ số P/E đạt **{pe_val:.2f}**. Mức định giá hiện tại khá **cao**, phần lớn kỳ vọng lợi nhuận tương lai đã phản ánh vào giá."
                            else: pe_text = f"Chỉ số P/E đạt **{pe_val:.2f}**. Mức định giá đang ở mức **hợp lý (Fair Value)**."
                        except: pe_text = "Dữ liệu P/E đang được cập nhật."
                    else: pe_text = "Chưa có đủ số liệu Báo cáo tài chính để tính toán P/E."

                    st.info(f"""
                    ### 📊 Báo Cáo Cố Vấn Đầu Tư: {ma_phan_tich}
                    **Thị giá hiện tại:** `{gia_pt:,.0f} VNĐ`
                    
                    #### 1. Góc nhìn Phân tích Kỹ thuật (Ngắn hạn)
                    * {rsi_text}
                    * {xu_huong_text}
                    * **Tín hiệu MACD:** {"Dòng tiền đang **bơm mạnh** vào cổ phiếu (MACD cắt lên Signal)." if macd_cur > sig_cur else "Dòng tiền có dấu hiệu **rút ra** hoặc suy yếu (MACD cắt xuống Signal)."}

                    #### 2. Góc nhìn Cơ bản & Chuyên gia (Trung - Dài hạn)
                    * **Định giá Doanh nghiệp:** {pe_text}
                    * **Tín nhiệm từ Chuyên gia:** Cổ phiếu đạt mức đánh giá {danh_gia_chuyen_gia}

                    #### 💡 Xây dựng Chiến lược (Action Plan)
                    > {
                    "✅ **KIẾN NGHỊ MUA GOM:** Động lượng kỹ thuật đang nén chặt ở vùng giá thấp kết hợp với định giá cơ bản tốt. Có thể rải lệnh mua thăm dò 30% tỷ trọng tại vùng giá hiện tại." if (rsi_pt < 45 and (isinstance(pe_pt, float) and pe_pt < 15) and macd_cur > sig_cur)
                    else "⚠️ **KIẾN NGHỊ CHỐT LỜI / ĐỨNG NGOÀI:** Cổ phiếu đang có dấu hiệu căng cứng về giá hoặc dòng tiền đang rút ra. Nếu đang có lãi, cân nhắc hạ 50% tỷ trọng để bảo toàn vốn. Tuyệt đối không mua đuổi (Fomo) lúc này." if (rsi_pt > 65 or macd_cur < sig_cur)
                    else "⚖️ **KIẾN NGHỊ NẮM GIỮ:** Cổ phiếu đang vận động tích lũy chặt chẽ, chưa có tín hiệu bùng nổ nhưng cũng không có rủi ro sập gãy. Tiếp tục nắm giữ và quan sát biến động khối lượng ở các phiên tới."
                    }
                    """)
                else:
                    st.warning("Dữ liệu không đủ để tạo báo cáo. Vui lòng kiểm tra lại kết nối mạng.")

# --- TAB 4: QUẢN LÝ DANH MỤC ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng")
    if DANH_SACH_MA:
        du_lieu_cap_nhat = {}
        col_h1, col_h2, col_h3 = st.columns([2, 3, 3])
        col_h1.write("**Mã CP**"); col_h2.write("**Số lượng**"); col_h3.write("**Giá vốn (VNĐ)**")
        
        for ma in DANH_SACH_MA:
            c1, c2, c3 = st.columns([2, 3, 3])
            c1.write(f"### {ma}")
            sl = c2.number_input(f"SL {ma}", min_value=0, step=100, value=DANH_MỤC_LIVE[ma][0], label_visibility="collapsed", key=f"sl_{ma}")
            gia_v = c3.number_input(f"Giá {ma}", min_value=0, step=500, value=DANH_MỤC_LIVE[ma][1], label_visibility="collapsed", key=f"gv_{ma}")
            du_lieu_cap_nhat[ma] = [sl, gia_v]

        if st.button("💾 Xác nhận & Lưu Cấu Hình"):
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
            m1.metric("Tổng vốn", f"{tong_von:,.0f} VNĐ")
            m2.metric("Tổng giá trị (NAV)", f"{tong_gt:,.0f} VNĐ")
            m3.metric("Lời / Lỗ", f"{tong_loi_nhuan:,.0f} VNĐ ({pct_tong:.2f}%)", delta=f"{tong_loi_nhuan:,.0f} VNĐ" if tong_loi_nhuan >= 0 else f"{tong_loi_nhuan:,.0f} VNĐ")
            
            df_disp = df_ptf.copy()
            df_disp["Tổng vốn"] = df_disp["Tổng vốn"].map("{:,.0f}".format)
            df_disp["Giá trị"] = df_disp["Giá trị"].map("{:,.0f}".format)
            df_disp["Lời / Lỗ"] = df_disp["Lời / Lỗ"].map("{:,.0f}".format)
            st.dataframe(df_disp.drop(columns=["Tổng vốn", "Giá trị"]), use_container_width=True, hide_index=True)
            
            st.write("### 🍕 Tỷ trọng tài sản")
            fig_pie = px.pie(df_ptf, values='Giá trị', names='Mã CP', hole=0.4)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

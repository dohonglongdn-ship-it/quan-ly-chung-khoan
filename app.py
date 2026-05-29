import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import urllib.parse
import yfinance as yf # GỌI LẠI VIỆN BINH YAHOO
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Ultimate Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ (VNDIRECT DCHART) ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
    loi_chi_tiet = []
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())

    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url_vnd, headers=headers, timeout=7)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * 1000
                return df.tail(180).reset_index(drop=True), "VNDirect DChart 🟢", ""
            else:
                loi_chi_tiet.append("VNDirect: Không tìm thấy dữ liệu.")
    except Exception as e:
        loi_chi_tiet.append(f"VNDirect lỗi mạng.")

    return pd.DataFrame(), "Thất bại 🔴", " | ".join(loi_chi_tiet)

# --- MODULE 2 (TỐI THƯỢNG): TRADINGVIEW + YAHOO FINANCE FALLBACK ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    profile = {
        'industry': 'N/A', 'pe': 'N/A', 'pb': 'N/A', 'roe': 'N/A', 
        'exchange': 'N/A', 'issueShare': 0, 'marketCap': 0, 
        'nguon_cap': 'Đang kết nối...'
    }
    
    # ƯU TIÊN 1: Lấy dữ liệu siêu nhanh từ TradingView
    url_tv = "https://scanner.tradingview.com/vietnam/scan"
    payload = {
        "symbols": {"tickers": [f"HOSE:{ma}", f"HNX:{ma}", f"UPCOM:{ma}"]},
        "columns": ["price_earnings_ttm", "price_book_ratio", "return_on_equity", "total_shares_outstanding", "market_cap_basic", "sector"]
    }
    try:
        res = requests.post(url_tv, json=payload, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data and len(data) > 0:
                item = data[0]
                san_ma = item.get('s', '') 
                profile['exchange'] = san_ma.split(':')[0] if ':' in san_ma else 'N/A'
                d = item.get('d', [])
                if len(d) >= 6:
                    profile['pe'] = d[0] if d[0] is not None else 'N/A'
                    profile['pb'] = d[1] if d[1] is not None else 'N/A'
                    profile['roe'] = d[2] if d[2] is not None else 'N/A'
                    profile['issueShare'] = d[3] if d[3] else 0
                    profile['marketCap'] = d[4] if d[4] else 0
                    profile['industry'] = d[5] if d[5] else 'N/A'
                    profile['nguon_cap'] = 'Máy chủ TradingView (Mỹ) 🟢'
    except:
        pass

    # ƯU TIÊN 2: Bù đắp khuyết điểm bằng Yahoo Finance (Dành cho mã UPCOM như OIL, ACV)
    # Kích hoạt khi TradingView không có dữ liệu Vốn hóa hoặc P/E
    if profile['marketCap'] == 0 or profile['pe'] == 'N/A':
        hnx_tickers = ["PVC", "PVS", "SHS", "CEO", "MBS", "IDC", "TNG"]
        symbol = f"{ma}.HN" if ma in hnx_tickers else f"{ma}.VN" # Gắn đuôi .VN cho HOSE và UPCOM
        
        try:
            tk = yf.Ticker(symbol)
            info = tk.info
            if info:
                profile['pe'] = info.get('trailingPE', profile['pe'])
                profile['pb'] = info.get('priceToBook', profile['pb'])
                
                # Đồng bộ định dạng phần trăm của Yahoo với hệ thống
                roe_raw = info.get('returnOnEquity')
                if roe_raw is not None:
                    profile['roe'] = roe_raw * 100 
                    
                profile['issueShare'] = info.get('sharesOutstanding', profile['issueShare'])
                profile['marketCap'] = info.get('marketCap', profile['marketCap'])
                
                if profile['industry'] == 'N/A': profile['industry'] = info.get('industry', 'N/A')
                if profile['exchange'] == 'N/A': profile['exchange'] = 'HOSE/UPCOM' if '.VN' in symbol else 'HNX'
                
                profile['nguon_cap'] = 'TradingView + Viện binh Yahoo 🟡'
        except:
            pass

    return profile

# --- CÁC HÀM TOÁN HỌC & FORMAT ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def format_metric(val, is_pct=False):
    if val in [None, 'N/A', '']: return "N/A"
    try:
        v = float(val)
        if is_pct: return f"{v:.2f}%"
        return f"{v:.2f}"
    except:
        return "N/A"

# 3. GIAO DIỆN CHÍNH (3 TABS)
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# TAB 1: BIỂU ĐỒ
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    with st.spinner("Đang lấy dữ liệu thời gian thực..."):
        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}**")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Không thể lấy dữ liệu biểu đồ.")

# TAB 2: HỒ SƠ DOANH NGHIỆP
with tab2:
    st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
    with st.spinner("Đang kết nối trạm vệ tinh và quét bổ sung dữ liệu bị khuyết..."):
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap')}**")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        col2.metric("P/E (Định giá)", format_metric(profile.get('pe')))
        col3.metric("P/B (Giá/Sổ sách)", format_metric(profile.get('pb')))
        col4.metric("ROE (Biên LN)", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("📌 **Quy mô doanh nghiệp & Giao dịch:**")
        
        issue_share = profile.get('issueShare', 0)
        market_cap_vnd = profile.get('marketCap', 0)
        von_hoa = market_cap_vnd / 1_000_000_000 if market_cap_vnd else 0
        klgd_20 = 0
        gia_hien_tai = 0
        
        if 'df' in locals() and not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            
        st.write(f"- **Thị giá hiện tại:** `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa:,.0f}` tỷ VNĐ")
        st.write(f"- **KLGD trung bình (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- **Tổng cổ phiếu lưu hành:** `{issue_share:,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# TAB 3: KHUYẾN NGHỊ RSI
with tab3:
    st.subheader("Bảng quét chỉ số RSI toàn thị trường")
    if st.button("🚀 Bắt đầu Quét dữ liệu"):
        ket_qua = []
        with st.spinner("Đang quét siêu tốc..."):
            for ma in DANH_SACH_MA:
                df_scan, nguon_scan, _ = lay_du_lieu_bieu_do(ma)
                if not df_scan.empty:
                    df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                    gia_hien_tai = df_scan['Close'].iloc[-1]
                    rsi_hien_tai = df_scan['RSI'].iloc[-1]
                    
                    if rsi_hien_tai <= 30: trang_thai = "🟢 MUA (Quá bán)"
                    elif rsi_hien_tai >= 70: trang_thai = "🔴 BÁN (Quá mua)"
                    else: trang_thai = "🔵 Giữ"
                        
                    ket_qua.append({"Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai})
                time.sleep(0.5)
        if ket_qua: st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)

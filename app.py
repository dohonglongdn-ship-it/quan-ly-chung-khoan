import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Hybrid Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- VŨ KHÍ MỚI: BỘ NHỚ ĐỆM (CACHE) ---
# Lưu trữ dữ liệu trong 15 phút (900 giây) để chống Spam API
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_lai(ma):
    loi_chi_tiet = []
    
    # Ưu tiên 1: Lấy từ Yahoo Finance
    try:
        ma_yf = f"{ma}.VN" 
        stock = yf.Ticker(ma_yf)
        df_yf = stock.history(period="6mo")
        if not df_yf.empty and 'Close' in df_yf.columns:
            df_yf = df_yf.reset_index()
            df_yf = df_yf.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
            return df_yf, "Yahoo Finance 🟢", ""
    except Exception as e:
        loi_chi_tiet.append(f"Yahoo lỗi: {str(e)}")

    # Ưu tiên 2: Dự phòng bằng DNSE
    try:
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=180)).timestamp())
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ma}&from={start_ts}&to={end_ts}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and data.get('t'):
                df_dnse = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                return df_dnse, "DNSE 🟡", ""
            else:
                loi_chi_tiet.append("DNSE: Bị chặn IP đám mây.")
    except Exception as e:
        loi_chi_tiet.append(f"DNSE lỗi: {str(e)}")
        
    return pd.DataFrame(), "Thất bại 🔴", " | ".join(loi_chi_tiet)

# --- HÀM TÍNH RSI ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# 3. GIAO DIỆN CHÍNH
tab1, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "💡 Khuyến nghị Tự động"])

with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    with st.spinner("Đang trích xuất dữ liệu..."):
        df, nguon, loi = lay_du_lieu_lai(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}** (Đã lưu Cache)")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Tất cả các nguồn dữ liệu đều quá tải.")
            st.write(f"Chi tiết kỹ thuật: {loi}")

with tab3:
    st.subheader("Bảng quét chỉ số RSI toàn thị trường")
    
    if st.button("🚀 Bắt đầu Quét dữ liệu"):
        ket_qua = []
        with st.spinner("Đang quét dữ liệu (Các mã đã lưu Cache sẽ hiện ra ngay lập tức)..."):
            for ma in DANH_SACH_MA:
                df_scan, nguon_scan, _ = lay_du_lieu_lai(ma)
                
                if not df_scan.empty:
                    df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                    gia_hien_tai = df_scan['Close'].iloc[-1]
                    rsi_hien_tai = df_scan['RSI'].iloc[-1]
                    
                    if rsi_hien_tai <= 30: trang_thai = "🟢 MUA (Quá bán)"
                    elif rsi_hien_tai >= 70: trang_thai = "🔴 BÁN (Quá mua)"
                    else: trang_thai = "🔵 Giữ"
                        
                    ket_qua.append({
                        "Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", 
                        "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai, "Nguồn": nguon_scan
                    })
                
                # Nghỉ 1 giây để an toàn cho các mã chưa có trong Cache
                time.sleep(1)
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)

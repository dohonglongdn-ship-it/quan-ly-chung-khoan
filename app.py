import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (DNSE/TCBS Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- VŨ KHÍ MỚI: ÉP KHUNG THỜI GIAN TĨNH (CHỐNG LỖI LỆCH MÚI GIỜ TƯƠNG LAI) ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu(ma):
    loi_chi_tiet = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # Khóa mốc thời gian từ năm 2020 đến 2033 (Đảm bảo quét sạch dữ liệu thực tế hiện tại)
    start_ts = 1600000000 
    end_ts = 2000000000

    # Ưu tiên 1: Cổng DNSE (Nhanh nhất, bao trọn HOSE, HNX, UPCOM)
    try:
        url_dnse = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ma}&from={start_ts}&to={end_ts}"
        res = requests.get(url_dnse, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                # Chỉ cắt lấy 180 phiên giao dịch có thực gần nhất
                return df.tail(180).reset_index(drop=True), "Máy chủ DNSE 🟢", ""
            else:
                loi_chi_tiet.append("DNSE: Không tìm thấy dữ liệu.")
    except Exception as e:
        loi_chi_tiet.append(f"DNSE lỗi mạng: {str(e)}")

    # Ưu tiên 2: Cổng TCBS (Dự phòng siêu mạnh)
    try:
        url_tcbs = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={ma}&type=stock&resolution=D&from={start_ts}&to={end_ts}"
        res = requests.get(url_tcbs, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and data.get('data'):
                df = pd.DataFrame(data['data'])
                df['Date'] = pd.to_datetime(df['tradingDate'])
                df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                return df.tail(180).reset_index(drop=True), "Máy chủ TCBS 🟡", ""
    except Exception as e:
        loi_chi_tiet.append(f"TCBS lỗi: {str(e)}")

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
    with st.spinner("Đang trích xuất dữ liệu vượt thời gian..."):
        df, nguon, loi = lay_du_lieu(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}** (Đã khử nhiễu thời gian)")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Tất cả các nguồn dữ liệu đều từ chối kết nối.")
            st.write(f"Chi tiết kỹ thuật: {loi}")

with tab3:
    st.subheader("Bảng quét chỉ số RSI toàn thị trường")
    
    if st.button("🚀 Bắt đầu Quét dữ liệu"):
        ket_qua = []
        with st.spinner("Đang quét siêu tốc..."):
            for ma in DANH_SACH_MA:
                df_scan, nguon_scan, _ = lay_du_lieu(ma)
                
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
                time.sleep(0.5)
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (VPS/SSI Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- VŨ KHÍ MỚI: CỔNG DỮ LIỆU CHUYÊN DỤNG (KHÔNG CHẶN IP, ĐỦ MỌI SÀN) ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu(ma):
    loi_chi_tiet = []
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=180)).timestamp())
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Ưu tiên 1: Cổng dữ liệu VPS (Nhanh, không chặn IP, đủ UPCOM/HNX)
    try:
        url_vps = f"https://bgapidata.vps.com.vn/api/History?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        res = requests.get(url_vps, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                return df, "Máy chủ VPS 🟢", ""
            else:
                loi_chi_tiet.append("VPS: Bị khuyết dữ liệu.")
    except Exception as e:
        loi_chi_tiet.append(f"VPS lỗi mạng: {str(e)}")

    # Ưu tiên 2: Dự phòng bằng cổng SSI
    try:
        url_ssi = f"https://iboard-query.ssi.com.vn/v1/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        res = requests.get(url_ssi, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                return df, "Máy chủ SSI 🟡", ""
            else:
                loi_chi_tiet.append("SSI: Bị khuyết dữ liệu.")
    except Exception as e:
        loi_chi_tiet.append(f"SSI lỗi mạng: {str(e)}")

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
    with st.spinner("Đang kết nối thẳng vào máy chủ chứng khoán nội địa..."):
        df, nguon, loi = lay_du_lieu(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}** (Tích hợp Bộ nhớ đệm)")
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
                time.sleep(0.5) # Chỉ cần nghỉ nhe nửa giây là đủ
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)

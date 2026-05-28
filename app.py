import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Stealth Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- VŨ KHÍ MỚI: NGỤY TRANG TOÀN DIỆN VƯỢT TƯỜNG LỬA ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu(ma):
    loi_chi_tiet = []
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())

    # Ưu tiên 1: Cổng SSI (Đóng giả người dùng đang mở iBoard)
    try:
        url_ssi = f"https://iboard-query.ssi.com.vn/v1/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        headers_ssi = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://iboard.ssi.com.vn',
            'Referer': 'https://iboard.ssi.com.vn/'
        }
        res = requests.get(url_ssi, headers=headers_ssi, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('t') and len(data['t']) > 0:
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                return df.tail(180).reset_index(drop=True), "SSI iBoard 🟢", ""
            else:
                loi_chi_tiet.append("SSI: Trả về dữ liệu rỗng.")
        else:
            loi_chi_tiet.append(f"SSI từ chối (Mã lỗi HTTP: {res.status_code})")
    except Exception as e:
        loi_chi_tiet.append(f"SSI lỗi mạng: {str(e)}")

    # Ưu tiên 2: Cổng TCBS (Đóng giả người dùng TCInvest)
    try:
        url_tcbs = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={ma}&type=stock&resolution=D&from={start_ts}&to={end_ts}"
        headers_tcbs = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://tcinvest.tcbs.com.vn',
            'Referer': 'https://tcinvest.tcbs.com.vn/'
        }
        res = requests.get(url_tcbs, headers=headers_tcbs, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and data.get('data'):
                df = pd.DataFrame(data['data'])
                df['Date'] = pd.to_datetime(df['tradingDate'])
                df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                return df.tail(180).reset_index(drop=True), "TCBS 🟡", ""
            else:
                loi_chi_tiet.append("TCBS: Trả về dữ liệu rỗng.")
        else:
            loi_chi_tiet.append(f"TCBS từ chối (Mã lỗi HTTP: {res.status_code})")
    except Exception as e:
        loi_chi_tiet.append(f"TCBS lỗi mạng: {str(e)}")

    # Ưu tiên 3: Cổng DNSE (Đóng giả người dùng Entrade)
    try:
        url_dnse = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ma}&from={start_ts}&to={end_ts}"
        headers_dnse = {
            'User-Agent': 'Mozilla/5.0',
            'Origin': 'https://banggia.dnse.com.vn',
            'Referer': 'https://banggia.dnse.com.vn/'
        }
        res = requests.get(url_dnse, headers=headers_dnse, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                return df.tail(180).reset_index(drop=True), "DNSE 🟠", ""
            else:
                loi_chi_tiet.append("DNSE: Trả về dữ liệu rỗng.")
        else:
            loi_chi_tiet.append(f"DNSE từ chối (Mã lỗi HTTP: {res.status_code})")
    except Exception as e:
        loi_chi_tiet.append(f"DNSE lỗi mạng: {str(e)}")

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
    with st.spinner("Đang ngụy trang kết nối để vượt tường lửa..."):
        df, nguon, loi = lay_du_lieu(ma_chon)
        
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}**")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Tất cả các nguồn dữ liệu đều chặn IP đám mây.")
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

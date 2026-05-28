import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Giai đoạn 1)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ (VNDIRECT) ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
    loi_chi_tiet = []
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())

    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url_vnd, headers=headers, timeout=7)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * 1000
                return df.tail(180).reset_index(drop=True), "Máy chủ VNDirect 🟢", ""
            else:
                loi_chi_tiet.append("VNDirect: Không tìm thấy dữ liệu.")
        else:
            loi_chi_tiet.append(f"VNDirect từ chối (Lỗi HTTP: {res.status_code})")
    except Exception as e:
        loi_chi_tiet.append(f"VNDirect lỗi mạng: {str(e)}")

    return pd.DataFrame(), "Thất bại 🔴", " | ".join(loi_chi_tiet)

# --- MODULE 2 (MỚI): KẾT NỐI HỒ SƠ DOANH NGHIỆP (TCBS - VNSTOCK CORE) ---
# Dữ liệu tài chính chỉ cần cập nhật 1 lần/ngày (86400 giây) để tiết kiệm băng thông
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    # Đây chính là đường dẫn API lõi mà vnstock sử dụng
    url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{ma}/overview"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

# --- HÀM TÍNH RSI ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# 3. GIAO DIỆN CHÍNH (3 TABS)
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# TAB 1: BIỂU ĐỒ
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    with st.spinner("Đang lấy dữ liệu thời gian thực..."):
        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}** (Cập nhật: {datetime.now().strftime('%d/%m/%Y')})")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Không thể lấy dữ liệu biểu đồ.")
            st.write(f"Chi tiết kỹ thuật: {loi}")

# TAB 2 (MỚI KÍCH HOẠT): HỒ SƠ DOANH NGHIỆP
with tab2:
    st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
    with st.spinner("Đang trích xuất dữ liệu từ máy chủ TCBS..."):
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        if profile:
            # Hàng 1: Các chỉ số định giá
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
            
            pe = profile.get('pe')
            col2.metric("P/E (Định giá)", f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A")
            
            pb = profile.get('pb')
            col3.metric("P/B (Giá/Sổ sách)", f"{pb:.2f}" if isinstance(pb, (int, float)) else "N/A")
            
            roe = profile.get('roe')
            col4.metric("ROE (Biên LN)", f"{roe*100:.2f}%" if isinstance(roe, (int, float)) else "N/A")

            # Hàng 2: Thông tin quy mô
            st.markdown("---")
            st.write("📌 **Quy mô doanh nghiệp:**")
            mc = profile.get('marketCap', 0)
            st.write(f"- **Vốn hóa thị trường:** `{mc:,.0f}` tỷ VNĐ")
            st.write(f"- **KLGD trung bình:** `{profile.get('volume', 0):,.0f}` cổ phiếu")
            st.write(f"- **Tổng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
            st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")
        else:
            st.warning("⚠️ Không thể tải hồ sơ doanh nghiệp. Tường lửa TCBS có thể đang tạm chặn IP.")

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
                        
                    ket_qua.append({
                        "Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", 
                        "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai, "Nguồn": nguon_scan
                    })
                time.sleep(0.5)
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)

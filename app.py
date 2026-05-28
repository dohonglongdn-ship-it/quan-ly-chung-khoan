import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG TỔNG QUAN
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Dữ liệu DNSE)")

# 2. KHU VỰC ĐIỀU KHIỂN (SIDEBAR)
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- HÀM LẤY DỮ LIỆU TỪ DNSE (CÓ KHIÊN CHỐNG LỖI NONETYPE) ---
def lay_du_lieu_dnse(ma):
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=180)).timestamp())
    url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ma}&from={start_ts}&to={end_ts}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    loi_chi_tiet = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # BỘ LỌC MỚI: Kiểm tra hộp dữ liệu có rỗng không trước khi đọc
            if isinstance(data, dict) and data.get('t') is not None and len(data['t']) > 0:
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'],
                    'High': data['h'],
                    'Low': data['l'],
                    'Close': data['c'],
                    'Volume': data['v']
                })
                return df, loi_chi_tiet
            else:
                loi_chi_tiet = "Truy cập thành công nhưng DNSE từ chối trả dữ liệu (Có thể IP đám mây bị hạn chế ngầm)."
        else:
            loi_chi_tiet = f"Bị chặn bởi tường lửa DNSE (Mã lỗi HTTP: {res.status_code})"
    except Exception as e:
        loi_chi_tiet = f"Mất kết nối hoàn toàn tới máy chủ: {str(e)}"
        
    return pd.DataFrame(), loi_chi_tiet

# --- HÀM TÍNH RSI ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# 3. CHIA GIAO DIỆN THÀNH 3 TAB
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# ----------------- TAB 1: BIỂU ĐỒ KỸ THUẬT -----------------
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    with st.spinner("Đang đóng giả trình duyệt web để kéo dữ liệu từ máy chủ DNSE..."):
        df, loi = lay_du_lieu_dnse(ma_chon)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"⚠️ Không thể tải dữ liệu biểu đồ. Nguyên nhân thực sự: {loi}")

# ----------------- TAB 2: HỒ SƠ DOANH NGHIỆP -----------------
with tab2:
    st.subheader("Hồ sơ tài chính (Đang nâng cấp)")
    st.info("Vì máy chủ đang đặt tại quốc tế, tính năng cào dữ liệu Báo cáo tài chính nội bộ đang được cấu hình lại để vượt tường lửa. Chúng ta sẽ ưu tiên cho Phân tích kỹ thuật và Khuyến nghị (Tab 1 & 3) chạy mượt mà trước nhé!")

# ----------------- TAB 3: KHUYẾN NGHỊ TỰ ĐỘNG -----------------
with tab3:
    st.subheader("Bảng quét chỉ số RSI toàn thị trường")
    
    if st.button("🚀 Quét dữ liệu tự động ngay bây giờ"):
        ket_qua = []
        danh_sach_loi = []
        with st.spinner("Đang quét siêu tốc toàn bộ danh sách..."):
            for ma in DANH_SACH_MA:
                df_scan, loi_scan = lay_du_lieu_dnse(ma)
                
                if not df_scan.empty:
                    df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                    gia_hien_tai = df_scan['Close'].iloc[-1]
                    rsi_hien_tai = df_scan['RSI'].iloc[-1]
                    
                    if rsi_hien_tai <= 30:
                        trang_thai = "🟢 MUA (Quá bán)"
                    elif rsi_hien_tai >= 70:
                        trang_thai = "🔴 BÁN (Quá mua)"
                    else:
                        trang_thai = "🔵 Giữ"
                        
                    ket_qua.append({"Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai})
                else:
                    danh_sach_loi.append(f"Mã {ma}: {loi_scan}")
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)
        
        if danh_sach_loi:
            st.warning("⚠️ Báo cáo lỗi chi tiết cho các mã không tải được:")
            for l in danh_sach_loi:
                st.write(l)

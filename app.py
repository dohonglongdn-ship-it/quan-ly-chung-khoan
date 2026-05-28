import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán", layout="wide")
st.title("📈 Hệ thống Theo dõi & Khuyến cáo Chứng khoán Việt Nam")
st.write("Ứng dụng kết nối dữ liệu API trực tiếp & tự động phân tích kỹ thuật")

DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ket_qua = []

# 1. Thuật toán tự tính RSI siêu nhẹ (Không cần cài thư viện ngoài)
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# 2. Hàm kết nối thẳng vào trung tâm dữ liệu (Chống kẹt mạng)
def lay_du_lieu(ma):
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=180)).timestamp())
    url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={ma}&type=stock&resolution=D&from={start_time}&to={end_time}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
    return pd.DataFrame(res.json()['data'])

# 3. Chạy dữ liệu kèm hiệu ứng chờ (Để không bị trắng màn hình)
with st.spinner("Đang kéo dữ liệu từ hệ thống. Vui lòng đợi trong giây lát..."):
    for ma in DANH_SACH_MA:
        try:
            df = lay_du_lieu(ma)
            if not df.empty:
                df['RSI'] = tinh_rsi(df['close'])
                
                gia_hien_tai = df['close'].iloc[-1]
                rsi_hien_tai = df['RSI'].iloc[-1]
                
                if rsi_hien_tai <= 30:
                    trang_thai = "🟢 MUA (Quá bán)"
                elif rsi_hien_tai >= 70:
                    trang_thai = "🔴 BÁN (Quá mua)"
                else:
                    trang_thai = "🔵 Theo dõi (Bình thường)"
                    
                ket_qua.append({
                    "Mã CP": ma,
                    "Giá hiện tại (đ)": f"{gia_hien_tai:,.0f}",
                    "Chỉ số RSI": round(rsi_hien_tai, 2),
                    "Khuyến nghị": trang_thai
                })
        except Exception:
            pass # Bỏ qua mã lỗi để hệ thống chạy tiếp

# 4. Hiển thị bảng
if ket_qua:
    df_kq = pd.DataFrame(ket_qua)
    st.dataframe(df_kq, use_container_width=True)
else:
    st.error("⚠️ Không thể kết nối đến máy chủ. Vui lòng bấm F5 thử lại.")

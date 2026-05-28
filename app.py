import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán", layout="wide")
st.title("📈 Hệ thống Theo dõi & Khuyến cáo Chứng khoán Việt Nam")
st.write("Ứng dụng kết nối dữ liệu API trực tiếp & tự động phân tích kỹ thuật")

DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ket_qua = []
loi_chi_tiet = []

# Thuật toán tự tính RSI siêu nhẹ
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# Cổng API của VNDirect (Mở cửa cho IP Quốc tế)
def lay_du_lieu(ma):
    ngay_hom_nay = datetime.now().strftime('%Y-%m-%d')
    ngay_truoc_day = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}~date:gte:{ngay_truoc_day}~date:lte:{ngay_hom_nay}&size=1000"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        data = res.json().get('data', [])
        df = pd.DataFrame(data)
        if not df.empty:
            # Dữ liệu VNDirect trả về bị ngược thời gian, cần đảo lại để tính RSI cho đúng
            df = df.sort_values('date').reset_index(drop=True)
        return df
    else:
        raise Exception(f"Bị từ chối kết nối (Mã lỗi: {res.status_code})")

with st.spinner("Đang kéo dữ liệu từ hệ thống. Vui lòng đợi trong giây lát..."):
    for ma in DANH_SACH_MA:
        try:
            df = lay_du_lieu(ma)
            if not df.empty and 'close' in df.columns:
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
            else:
                loi_chi_tiet.append(f"Không lấy được lịch sử giá cho mã {ma}")
        except Exception as e:
            loi_chi_tiet.append(f"Lỗi mã {ma}: {str(e)}")

# Hiển thị bảng
if ket_qua:
    df_kq = pd.DataFrame(ket_qua)
    st.dataframe(df_kq, use_container_width=True)
else:
    st.error("⚠️ Vẫn không thể kết nối đến máy chủ dữ liệu.")
    if loi_chi_tiet:
        with st.expander("Bấm vào đây để xem Kỹ sư trưởng báo cáo lỗi chi tiết:"):
            for loi in loi_chi_tiet:
                st.write(loi)

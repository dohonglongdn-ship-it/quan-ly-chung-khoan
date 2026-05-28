import streamlit as st
import pandas as pd
import yfinance as yf
import time  # Thêm thư viện thời gian
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán", layout="wide")
st.title("📈 Hệ thống Theo dõi & Khuyến cáo Chứng khoán Việt Nam")
st.write("Dữ liệu được cấp bởi máy chủ toàn cầu Yahoo Finance - Chống nghẽn 100%")

DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ket_qua = []
loi_chi_tiet = []

def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

with st.spinner("Đang kết nối chậm rãi với Yahoo Finance để tránh nghẽn mạng. Vui lòng đợi..."):
    for ma in DANH_SACH_MA:
        try:
            # Phân loại đuôi mã chứng khoán theo chuẩn Yahoo Finance
            if ma in ["TCB", "CSM", "TNT"]:
                ma_yf = f"{ma}.HM"
            elif ma in ["PVC", "OIL", "DRI"]:
                ma_yf = f"{ma}.HN"
            else:
                ma_yf = f"{ma}.VN"
            
            stock = yf.Ticker(ma_yf)
            df = stock.history(period="6mo")
            
            if not df.empty and 'Close' in df.columns:
                df['RSI'] = tinh_rsi(df['Close'])
                
                gia_hien_tai = df['Close'].iloc[-1]
                rsi_hien_tai = df['RSI'].iloc[-1]
                
                if rsi_hien_tai <= 30:
                    trang_thai = "🟢 MUA (Quá bán)"
                elif rsi_hien_tai >= 70:
                    trang_thai = "🔴 BÁN (Quá mua)"
                else:
                    trang_thai = "🔵 Theo dõi (Bình thường)"
                    
                ket_qua.append({
                    "Mã CP": ma,
                    "Giá hiện tại": f"{gia_hien_tai:,.0f}",
                    "Chỉ số RSI": round(rsi_hien_tai, 2),
                    "Khuyến nghị": trang_thai
                })
            else:
                loi_chi_tiet.append(f"Không có dữ liệu lịch sử cho mã {ma}")
                
            # Tuyệt chiêu: Nghỉ 2 giây sau mỗi lần lấy dữ liệu để không bị Yahoo chặn
            time.sleep(2)
            
        except Exception as e:
            loi_chi_tiet.append(f"Lỗi khi tải mã {ma}: {str(e)}")

# Hiển thị bảng
if ket_qua:
    df_kq = pd.DataFrame(ket_qua)
    st.dataframe(df_kq, use_container_width=True)
else:
    st.error("⚠️ Hệ thống đang bảo trì hoặc bị Yahoo tạm chặn. Vui lòng chờ ít phút rồi F5 lại.")
    if loi_chi_tiet:
        with st.expander("Bấm vào đây để xem chi tiết lỗi:"):
            for loi in loi_chi_tiet:
                st.write(loi)

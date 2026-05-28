import streamlit as st
import pandas as pd
from vnstock import *
import ta  # Đã đổi sang thư viện tính toán hiện đại hơn
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán", layout="wide")
st.title("📈 Hệ thống Theo dõi & Khuyến cáo Chứng khoán Việt Nam")
st.write("Ứng dụng tự động phân tích kỹ thuật dựa trên chỉ báo RSI")

DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ket_qua = []

# Lấy dữ liệu 6 tháng gần nhất
ngay_hom_nay = datetime.now().strftime('%Y-%m-%d')
ngay_truoc_day = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

for ma in DANH_SACH_MA:
    try:
        df = stock_historical_data(symbol=ma, start_date=ngay_truoc_day, end_date=ngay_hom_nay, resolution="1D", type="stock")
        
        if df is not None and not df.empty:
            # Lệnh tính RSI của thư viện mới
            df['RSI'] = ta.momentum.rsi(df['close'], window=14)
            
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
    except Exception as e:
        pass

if ket_qua:
    df_kq = pd.DataFrame(ket_qua)
    st.dataframe(df_kq, use_container_width=True)
else:
    st.warning("⚠️ Nguồn dữ liệu từ bên thứ ba đang bận. Vui lòng tải lại trang sau ít phút.")

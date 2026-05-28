import streamlit as st
import pandas as pd
from vnstock import *
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG TỔNG QUAN
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Dữ liệu Vnstock)")

# 2. KHU VỰC ĐIỀU KHIỂN (SIDEBAR)
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

ngay_hom_nay = datetime.now().strftime('%Y-%m-%d')
ngay_truoc_day = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

# 3. CHIA GIAO DIỆN THÀNH 3 TAB
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# ----------------- TAB 1: BIỂU ĐỒ KỸ THUẬT -----------------
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    try:
        # Lấy dữ liệu từ Vnstock
        df = stock_historical_data(symbol=ma_chon, start_date=ngay_truoc_day, end_date=ngay_hom_nay, resolution="1D", type="stock", source='TCBS')
        
        if not df.empty:
            # Vẽ biểu đồ nến chuyên nghiệp bằng Plotly
            fig = go.Figure(data=[go.Candlestick(x=df['time'],
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Không có dữ liệu biểu đồ cho mã này.")
    except Exception as e:
        st.error(f"Lỗi tải biểu đồ: Dữ liệu từ Vnstock đang tạm nghẽn trên máy chủ đám mây.")

# ----------------- TAB 2: HỒ SƠ DOANH NGHIỆP -----------------
with tab2:
    st.subheader(f"Chỉ số định giá Cơ bản - Mã: {ma_chon}")
    try:
        # Sử dụng hàm lấy thông tin cơ bản của Vnstock
        df_profile = ticker_overview(ma_chon)
        if not df_profile.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Ngành nghề", df_profile['industryEn'].iloc[0][:15] + "...")
            col2.metric("P/E (Định giá)", df_profile['pe'].iloc[0])
            col3.metric("P/B (Giá/Sổ sách)", df_profile['pb'].iloc[0])
            col4.metric("ROE (Lợi nhuận/Vốn)", df_profile['roe'].iloc[0])
            
            st.write("📌 **Tóm tắt hoạt động:**")
            st.dataframe(df_profile[['shortName', 'volume', 'marketCap', 'issueShare']].style.format("{:,.0f}", subset=['volume', 'marketCap', 'issueShare']), use_container_width=True)
    except Exception as e:
        st.error("Không thể lấy dữ liệu cơ bản hiện tại.")

# ----------------- TAB 3: KHUYẾN NGHỊ TỰ ĐỘNG -----------------
with tab3:
    st.subheader("Bảng quét chỉ số RSI toàn thị trường")
    
    def tinh_rsi(series, period=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=period-1, adjust=False).mean()
        ema_down = down.ewm(com=period-1, adjust=False).mean()
        rs = ema_up / ema_down
        return 100 - (100 / (1 + rs))

    if st.button("🚀 Quét dữ liệu tự động ngay bây giờ"):
        ket_qua = []
        with st.spinner("Đang kết nối vào hệ thống Vnstock..."):
            for ma in DANH_SACH_MA:
                try:
                    df_scan = stock_historical_data(symbol=ma, start_date=ngay_truoc_day, end_date=ngay_hom_nay, resolution="1D", type="stock", source='TCBS')
                    if not df_scan.empty:
                        df_scan['RSI'] = tinh_rsi(df_scan['close'])
                        gia_hien_tai = df_scan['close'].iloc[-1]
                        rsi_hien_tai = df_scan['RSI'].iloc[-1]
                        
                        if rsi_hien_tai <= 30:
                            trang_thai = "🟢 MUA"
                        elif rsi_hien_tai >= 70:
                            trang_thai = "🔴 BÁN"
                        else:
                            trang_thai = "🔵 Giữ"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai})
                except:
                    pass
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)
        else:
            st.error("Hệ thống đám mây đang bị giới hạn truy cập API nội địa.")

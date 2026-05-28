import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG TỔNG QUAN
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Dữ liệu Quốc tế)")

# 2. KHU VỰC ĐIỀU KHIỂN (SIDEBAR)
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# Hàm định vị đuôi mã chuẩn Yahoo Finance
def lay_ma_yf(ma):
    if ma in ["TCB", "CSM", "TNT"]: return f"{ma}.HM"
    elif ma in ["PVC", "OIL", "DRI"]: return f"{ma}.HN"
    else: return f"{ma}.VN"

ma_yf_chon = lay_ma_yf(ma_chon)

# 3. CHIA GIAO DIỆN THÀNH 3 TAB
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# ----------------- TAB 1: BIỂU ĐỒ KỸ THUẬT -----------------
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    try:
        stock = yf.Ticker(ma_yf_chon)
        df = stock.history(period="6mo")
        
        if not df.empty:
            df.reset_index(inplace=True) # Reset để lấy cột Date vẽ biểu đồ
            # Vẽ biểu đồ nến tương tác chuyên nghiệp bằng Plotly
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Không có dữ liệu biểu đồ cho mã này.")
    except Exception as e:
        st.error("Lỗi kết nối biểu đồ.")

# ----------------- TAB 2: HỒ SƠ DOANH NGHIỆP -----------------
with tab2:
    st.subheader(f"Chỉ số định giá Cơ bản - Mã: {ma_chon}")
    try:
        stock = yf.Ticker(ma_yf_chon)
        info = stock.info
        if info:
            col1, col2, col3, col4 = st.columns(4)
            # Tự động trích xuất dữ liệu tài chính từ Yahoo
            col1.metric("Ngành nghề", str(info.get('industry', 'Đang cập nhật'))[:20])
            pe = info.get('trailingPE', 'N/A')
            col2.metric("P/E (Định giá)", round(pe, 2) if isinstance(pe, (int, float)) else pe)
            pb = info.get('priceToBook', 'N/A')
            col3.metric("P/B (Giá/Sổ sách)", round(pb, 2) if isinstance(pb, (int, float)) else pb)
            roe = info.get('returnOnEquity', 'N/A')
            col4.metric("ROE (Biên LN)", f"{round(roe*100, 2)}%" if isinstance(roe, (int, float)) else roe)
    except Exception as e:
        st.error("Hệ thống đang cập nhật hồ sơ doanh nghiệp này.")

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
        with st.spinner("Đang kết nối chậm rãi vào hệ thống toàn cầu để chống nghẽn..."):
            for ma in DANH_SACH_MA:
                try:
                    ma_yf = lay_ma_yf(ma)
                    stock_scan = yf.Ticker(ma_yf)
                    df_scan = stock_scan.history(period="6mo")
                    
                    if not df_scan.empty and 'Close' in df_scan.columns:
                        df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                        gia_hien_tai = df_scan['Close'].iloc[-1]
                        rsi_hien_tai = df_scan['RSI'].iloc[-1]
                        
                        if rsi_hien_tai <= 30:
                            trang_thai = "🟢 MUA"
                        elif rsi_hien_tai >= 70:
                            trang_thai = "🔴 BÁN"
                        else:
                            trang_thai = "🔵 Giữ"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia_hien_tai:,.0f}", "RSI": round(rsi_hien_tai, 2), "Khuyến nghị": trang_thai})
                    
                    # Cực kỳ quan trọng: Nghỉ 1.5 giây để tránh bị Yahoo khóa IP
                    time.sleep(1.5)
                except:
                    pass
        
        if ket_qua:
            st.dataframe(pd.DataFrame(ket_qua), use_container_width=True)
        else:
            st.error("Không lấy được dữ liệu, vui lòng chờ ít phút và thử lại.")

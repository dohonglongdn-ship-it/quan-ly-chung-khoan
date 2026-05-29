import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import urllib.parse
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích Chứng khoán Pro (Multi-Source Engine)")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ (VNDIRECT DCHART) ---
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

# --- MODULE 2 (HYBRID): HỒ SƠ DOANH NGHIỆP TỪ 3 NGUỒN ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    profile = {'industry': 'N/A', 'pe': 'N/A', 'pb': 'N/A', 'roe': 'N/A', 'exchange': 'N/A', 'issueShare': 0, 'nguon_cap': 'Đang kết nối...'}

    # ƯU TIÊN 1: Cổng FireAnt (Siêu tốc, thân thiện với máy chủ đám mây)
    try:
        url_fa_fi = f"https://svr1.fireant.vn/api/Data/Finance/LastestFinancialInfo?symbol={ma}"
        url_fa_pr = f"https://svr1.fireant.vn/api/Data/Companies/CompanyInfo?symbol={ma}"
        
        res_fi = requests.get(url_fa_fi, headers=headers, timeout=5)
        res_pr = requests.get(url_fa_pr, headers=headers, timeout=5)
        
        if res_fi.status_code == 200 and res_pr.status_code == 200:
            data_fi = res_fi.json()
            data_pr = res_pr.json()
            
            if isinstance(data_fi, list) and len(data_fi) > 0:
                item = data_fi[0]
                profile['pe'] = item.get('PE')
                profile['pb'] = item.get('PB')
                profile['roe'] = item.get('ROE')
                profile['issueShare'] = item.get('OutstandingShare', 0)
            
            if isinstance(data_pr, dict):
                profile['industry'] = data_pr.get('IndustryName', 'N/A')
                profile['exchange'] = data_pr.get('Exchange', 'N/A')
            
            if profile['pe'] is not None:
                profile['nguon_cap'] = 'Hệ thống FireAnt 🟢'
                return profile
    except:
        pass

    # ƯU TIÊN 2: Cổng TCBS thông qua CorsProxy (Công nghệ vượt tường lửa mạnh nhất)
    try:
        url_tcbs = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{ma}/overview"
        url_proxy = f"https://corsproxy.io/?{urllib.parse.quote(url_tcbs)}"
        res = requests.get(url_proxy, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if 'pe' in data:
                profile['pe'] = data.get('pe')
                profile['pb'] = data.get('pb')
                profile['roe'] = data.get('roe')
                profile['industry'] = data.get('industryEn', data.get('industry', 'N/A'))
                profile['exchange'] = data.get('exchange', 'N/A')
                profile['issueShare'] = data.get('issueShare', 0)
                profile['nguon_cap'] = 'Máy chủ TCBS (CorsProxy) 🟡'
                return profile
    except:
        pass

    # ƯU TIÊN 3: Cổng SSI FiinTrade
    try:
        url_ssi = f"https://fiin-fundamental.ssi.com.vn/StockInfor/StockOverview/{ma}"
        res = requests.get(url_ssi, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            item = data.get('item', data)
            if 'pe' in item or 'priceToEarning' in item:
                profile['pe'] = item.get('priceToEarning', item.get('pe'))
                profile['pb'] = item.get('priceToBook', item.get('pb'))
                profile['roe'] = item.get('roe')
                profile['industry'] = item.get('icbName', 'N/A')
                profile['exchange'] = item.get('comGroupCode', 'N/A')
                profile['issueShare'] = item.get('outstandingShare', 0)
                profile['nguon_cap'] = 'Máy chủ SSI 🟠'
                return profile
    except:
        pass
        
    return profile

# --- CÁC HÀM TOÁN HỌC & FORMAT ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

# Hàm bộ lọc định dạng tránh lỗi N/A
def format_metric(val, is_pct=False):
    if val in [None, 'N/A', '']: return "N/A"
    try:
        v = float(val)
        if is_pct:
            return f"{v*100:.2f}%" if abs(v) < 2 else f"{v:.2f}%"
        return f"{v:.2f}"
    except:
        return "N/A"

# 3. GIAO DIỆN CHÍNH (3 TABS)
tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "💡 Khuyến nghị Tự động"])

# TAB 1: BIỂU ĐỒ
with tab1:
    st.subheader(f"Biểu đồ biến động giá - Mã: {ma_chon}")
    with st.spinner("Đang lấy dữ liệu thời gian thực..."):
        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            st.caption(f"Trạng thái kết nối: Dữ liệu được cấp bởi **{nguon}**")
            fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá")])
            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Không thể lấy dữ liệu biểu đồ.")
            st.write(f"Chi tiết kỹ thuật: {loi}")

# TAB 2: HỒ SƠ DOANH NGHIỆP
with tab2:
    st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
    with st.spinner("Đang kích hoạt Động cơ Đa luồng để tìm kiếm hồ sơ..."):
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap')}**")
        
        # Hàng 1: Các chỉ số định giá
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        col2.metric("P/E (Định giá)", format_metric(profile.get('pe')))
        col3.metric("P/B (Giá/Sổ sách)", format_metric(profile.get('pb')))
        col4.metric("ROE (Biên LN)", format_metric(profile.get('roe'), is_pct=True))

        # Hàng 2: Tính toán Quy mô & Khối lượng động
        st.markdown("---")
        st.write("📌 **Quy mô doanh nghiệp & Giao dịch:**")
        
        issue_share = profile.get('issueShare', 0)
        try:
            issue_share = float(issue_share)
        except:
            issue_share = 0
            
        von_hoa = 0
        klgd_20 = 0
        
        if 'df' in locals() and not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean() # Trung bình thanh khoản 20 phiên
            von_hoa = (gia_hien_tai * issue_share) / 1_000_000_000 # Công thức Vốn hóa
            
            st.write(f"- **Thị giá hiện tại:** `{gia_hien_tai:,.0f}` VNĐ")
            st.write(f"- **Vốn hóa thị trường:** `{von_hoa:,.0f}` tỷ VNĐ")
            st.write(f"- **KLGD trung bình (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
            st.write(f"- **Tổng cổ phiếu lưu hành:** `{issue_share:,.0f}`")
            st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

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

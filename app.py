import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px # THƯ VIỆN MỚI: VẼ BIỂU ĐỒ BÁNH DANH MỤC
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro")

# 2. KHU VỰC ĐIỀU KHIỂN
st.sidebar.header("⚙️ Bảng Điều Khiển")
DANH_SACH_MA = ["TCB", "ACV", "OIL", "PVC", "DRI", "CSM", "TNT"]
ma_chon = st.sidebar.selectbox("Chọn mã cổ phiếu phân tích chuyên sâu:", DANH_SACH_MA)

# --- CƠ SỞ DỮ LIỆU NỘI BỘ (LOCAL DATA LAKE) ---
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "PVC": {"name": "Tổng công ty Hóa chất Dầu khí", "industry": "Hóa chất Dầu khí", "exchange": "HNX", "issueShare": 50000000, "eps": 550, "bvps": 11800, "roe": 0.04},
    "DRI": {"name": "Công ty cổ phần Cao su Đắk Lắk", "industry": "Cao su công nghiệp", "exchange": "UPCOM", "issueShare": 73200000, "eps": 950, "bvps": 12500, "roe": 0.08},
    "CSM": {"name": "Công ty Công nghiệp Cao su Miền Nam", "industry": "Săm lốp & Phụ tùng", "exchange": "HOSE", "issueShare": 133637422, "eps": 420, "bvps": 14500, "roe": 0.03},
    "TNT": {"name": "Công ty Tài nguyên và Tài chính Việt Nam", "industry": "Bất động sản", "exchange": "HOSE", "issueShare": 51000000, "eps": 150, "bvps": 10200, "roe": 0.01},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ LIVE ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
    loi_chi_tiet = []
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())

    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url_vnd, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s'),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * 1000
                return df.tail(180).reset_index(drop=True), "VNDirect DChart 🟢", ""
    except Exception:
        loi_chi_tiet.append("VNDirect lỗi mạng.")
    return pd.DataFrame(), "Thất bại 🔴", " | ".join(loi_chi_tiet)

# --- MODULE 2: HỒ SƠ DOANH NGHIỆP ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    profile = {
        'industry': 'N/A', 'pe': 'N/A', 'pb': 'N/A', 'roe': 'N/A', 
        'exchange': 'N/A', 'issueShare': 0, 'marketCap': 0, 'eps': 0, 'bvps': 0,
        'nguon_cap': 'Đang kết nối...'
    }
    try:
        url_tv = "https://scanner.tradingview.com/vietnam/scan"
        payload = {"symbols": {"tickers": [f"HOSE:{ma}", f"HNX:{ma}", f"UPCOM:{ma}"]},
                   "columns": ["price_earnings_ttm", "price_book_ratio", "return_on_equity", "total_shares_outstanding", "market_cap_basic", "sector"]}
        res_tv = requests.post(url_tv, json=payload, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res_tv.status_code == 200:
            data = res_tv.json().get('data', [])
            if data and len(data) > 0:
                item = data[0]
                d = item.get('d', [])
                if len(d) >= 6:
                    profile['pe'] = d[0] if d[0] is not None else 'N/A'
                    profile['pb'] = d[1] if d[1] is not None else 'N/A'
                    profile['roe'] = d[2] if d[2] is not None else 'N/A'
                    profile['issueShare'] = d[3] if d[3] else 0
                    profile['marketCap'] = d[4] if d[4] else 0
                    profile['industry'] = d[5] if d[5] else 'N/A'
                    san_ma = item.get('s', '') 
                    profile['exchange'] = san_ma.split(':')[0] if ':' in san_ma else 'N/A'
                    profile['nguon_cap'] = 'Máy chủ TradingView (Mỹ) 🟢'
    except:
        pass

    if profile['pe'] == 'N/A' or profile['issueShare'] == 0:
        if ma in LOCAL_DB:
            db = LOCAL_DB[ma]
            profile['industry'] = db['industry']
            profile['exchange'] = db['exchange']
            profile['issueShare'] = db['issueShare']
            profile['roe'] = db['roe']
            profile['eps'] = db['eps']
            profile['bvps'] = db['bvps']
            profile['nguon_cap'] = 'TradingView + CSDL Nội bộ 🟢'
    return profile

# --- CÁC HÀM TOÁN HỌC & CHỈ BÁO KỸ THUẬT ---
def tinh_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def tinh_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def format_metric(val, is_pct=False):
    if val in [None, 'N/A', '']: return "N/A"
    try:
        v = float(val)
        if is_pct: return f"{v*100:.2f}%" if abs(v) < 2 else f"{v:.2f}%"
        return f"{v:.2f}"
    except:
        return "N/A"

# 3. GIAO DIỆN CHÍNH (4 TABS)
tab1, tab2, tab3, tab4 = st.tabs(["📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "📡 Radar Dòng tiền (Screener)", "💼 Quản lý Danh mục"])

# --- TAB 1: BIỂU ĐỒ & XUẤT DỮ LIỆU ---
with tab1:
    st.subheader(f"Trung tâm Phân tích Kỹ thuật - Mã: {ma_chon}")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    show_vol = col_t1.checkbox("📊 Bật Volume", value=True)
    show_ma20 = col_t2.checkbox("📈 Bật MA 20", value=True)
    show_ma50 = col_t3.checkbox("📉 Bật MA 50", value=False)
    show_bb = col_t4.checkbox("🌐 Bật Bollinger Bands", value=False)

    with st.spinner("Đang vẽ biểu đồ kỹ thuật đa lớp..."):
        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['BB_Std'] = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['MA20'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['MA20'] - (df['BB_Std'] * 2)

            if show_vol:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
            else:
                fig = make_subplots(rows=1, cols=1)

            fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Nến giá"), row=1, col=1)

            if show_ma20: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], mode='lines', name='MA 20', line=dict(color='#2962FF', width=1.5)), row=1, col=1)
            if show_ma50: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA50'], mode='lines', name='MA 50', line=dict(color='#FF6D00', width=1.5)), row=1, col=1)
            if show_bb:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='gray', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128, 128, 128, 0.1)'), row=1, col=1)

            if show_vol:
                vol_colors = ['#26A69A' if row['Close'] >= row['Open'] else '#EF5350' for index, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color=vol_colors), row=2, col=1)

            fig.update_layout(xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20), height=600, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # TÍNH NĂNG GIAI ĐOẠN 4: XUẤT LỊCH SỬ GIÁ SANG CSV
            csv_price = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Xuất lịch sử giá 180 phiên (CSV)", data=csv_price, file_name=f"lich_su_gia_{ma_chon}.csv", mime="text/csv")
        else:
            st.error("Không thể lấy dữ liệu biểu đồ.")

# --- TAB 2: HỒ SƠ DOANH NGHIỆP ---
with tab2:
    st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
    with st.spinner("Đang đồng bộ Dữ liệu..."):
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap')}**")
        
        pe_hien_thi = profile.get('pe')
        pb_hien_thi = profile.get('pb')
        von_hoa_ty = profile.get('marketCap', 0) / 1_000_000_000
        
        gia_hien_tai = 0
        klgd_20 = 0
        if 'df' in locals() and not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            if profile.get('nguon_cap') == 'TradingView + CSDL Nội bộ 🟢' and gia_hien_tai > 0:
                if profile['eps'] > 0: pe_hien_thi = gia_hien_tai / profile['eps']
                if profile['bvps'] > 0: pb_hien_thi = gia_hien_tai / profile['bvps']
                von_hoa_ty = (gia_hien_tai * profile['issueShare']) / 1_000_000_000

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        col2.metric("P/E (Định giá)", format_metric(pe_hien_thi))
        col3.metric("P/B (Giá/Sổ sách)", format_metric(pb_hien_thi))
        col4.metric("ROE (Biên LN)", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write("📌 **Quy mô doanh nghiệp & Giao dịch:**")
        st.write(f"- **Tên doanh nghiệp:** `{LOCAL_DB.get(ma_chon, {}).get('name', 'N/A')}`")
        st.write(f"- **Thị giá hiện tại:** `{gia_hien_tai:,.0f}` VNĐ")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- **KLGD trung bình (20 phiên):** `{klgd_20:,.0f}` cổ phiếu")
        st.write(f"- **Tổng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR DÒNG TIỀN VÀ XUẤT BÁO CÁO ---
with tab3:
    st.subheader("Radar Quét Khối lượng & Tín hiệu Đa biến")
    
    if st.button("🚀 Kích hoạt Radar Quét Toàn Thị Trường"):
        ket_qua = []
        with st.spinner("Đang phân tích tín hiệu dòng tiền..."):
            for ma in DANH_SACH_MA:
                df_scan, _, _ = lay_du_lieu_bieu_do(ma)
                if not df_scan.empty and len(df_scan) >= 50:
                    df_scan['RSI'] = tinh_rsi(df_scan['Close'])
                    df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                    df_scan['MA50'] = df_scan['Close'].rolling(window=50).mean()
                    df_scan['Vol20'] = df_scan['Volume'].rolling(window=20).mean()
                    macd, signal = tinh_macd(df_scan['Close'])
                    
                    gia = df_scan['Close'].iloc[-1]
                    rsi = df_scan['RSI'].iloc[-1]
                    ma20 = df_scan['MA20'].iloc[-1]
                    ma50 = df_scan['MA50'].iloc[-1]
                    vol = df_scan['Volume'].iloc[-1]
                    vol_20 = df_scan['Vol20'].iloc[-1]
                    macd_cur = macd.iloc[-1]
                    sig_cur = signal.iloc[-1]
                    
                    diem_mua = 0
                    tin_hieu = []
                    
                    if rsi < 35:
                        diem_mua += 1
                        tin_hieu.append("RSI vùng đáy")
                    elif rsi > 70:
                        diem_mua -= 1
                        tin_hieu.append("RSI vùng đỉnh")
                        
                    if ma20 > ma50:
                        diem_mua += 1
                        tin_hieu.append("MA20 Cắt lên MA50")
                        
                    if macd_cur > sig_cur:
                        diem_mua += 1
                        tin_hieu.append("MACD Báo mua")
                        
                    dot_bien = "Bình thường"
                    if vol > (vol_20 * 1.5): 
                        diem_mua += 1
                        dot_bien = "⭐ NỔ VOL DÒNG TIỀN"
                        
                    if diem_mua >= 3: khuyen_nghi = "🟢 MUA MẠNH"
                    elif diem_mua >= 1: khuyen_nghi = "🟡 NẮM GIỮ"
                    else: khuyen_nghi = "🔴 RỦI RO / BÁN"
                        
                    ket_qua.append({"Mã CP": ma, "Giá": gia, "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Hội tụ Kỹ thuật": ", ".join(tin_hieu) if tin_hieu else "Suy yếu", "Hành động": khuyen_nghi})
                time.sleep(0.1) 
        
        if ket_qua:
            df_kq = pd.DataFrame(ket_qua)
            st.dataframe(df_kq, use_container_width=True, hide_index=True)
            
            # TÍNH NĂNG GIAI ĐOẠN 4: XUẤT BẢNG BÁO CÁO RADAR SANG CSV
            csv_radar = df_kq.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Xuất báo cáo Radar Dòng tiền (CSV)", data=csv_radar, file_name="bao_cao_radar_live.csv", mime="text/csv")

# --- TAB 4 (MỚI KÍCH HOẠT): QUẢN LÝ DANH MỤC ĐẦU TƯ ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng & Tỷ trọng vốn")
    st.markdown("Thay đổi **Số lượng** và **Giá mua** dưới đây để hệ thống tự động định giá lại tài sản theo thời gian thực.")

    # Tạo bảng nhập liệu động cho 7 mã
    danh_sach_nhap = []
    
    col_h1, col_h2, col_h3 = st.columns([2, 3, 3])
    col_h1.write("**Mã CP**")
    col_h2.write("**Số lượng nắm giữ (Cổ phiếu)**")
    col_h3.write("**Giá mua trung bình (VNĐ)**")
    
    # Thiết lập form nhập liệu nhanh với các mốc mặc định ban đầu
    defaults = {"TCB": (1000, 32000), "ACV": (500, 43000), "OIL": (2000, 14000), "PVC": (0, 0), "DRI": (0, 0), "CSM": (0, 0), "TNT": (0, 0)}
    
    for ma in DANH_SACH_MA:
        c1, c2, c3 = st.columns([2, 3, 3])
        c1.write(f"### {ma}")
        sl = c2.number_input(f"Số lượng {ma}", min_value=0, step=100, value=defaults[ma][0], label_visibility="collapsed")
        gia_v = c3.number_input(f"Giá vốn {ma}", min_value=0, step=500, value=defaults[ma][1], label_visibility="collapsed")
        if sl > 0:
            danh_sach_nhap.append({"Mã CP": ma, "Số lượng": sl, "Giá vốn": gia_v})

    # Tính toán hiệu năng danh mục
    if danh_sach_nhap:
        st.markdown("---")
        st.write("### 📊 Hiệu suất Danh mục đầu tư thực tế")
        
        hang_danh_muc = []
        tong_von = 0
        tong_gia_tri_hien_tai = 0
        
        for item in danh_sach_nhap:
            ma = item["Mã CP"]
            sl = item["Số lượng"]
            gia_v = item["Giá vốn"]
            
            # Lấy giá live từ VNDirect
            df_live, _, _ = lay_du_lieu_bieu_do(ma)
            gia_live = df_live['Close'].iloc[-1] if not df_live.empty else gia_v
            
            thanh_tien_von = sl * gia_v
            thanh_tien_live = sl * gia_live
            loi_nhuan = thanh_tien_live - thanh_tien_von
            phan_tram_lh = (loi_nhuan / thanh_tien_von * 100) if thanh_tien_von > 0 else 0
            
            tong_von += thanh_tien_von
            tong_gia_tri_hien_tai += thanh_tien_live
            
            hang_danh_muc.append({
                "Mã CP": ma,
                "Số lượng": f"{sl:,}",
                "Giá mua": f"{gia_v:,.0f}",
                "Giá hiện tại": f"{gia_live:,.0f}",
                "Tổng vốn đầu tư": thanh_tien_von,
                "Giá trị hiện tại": thanh_tien_live,
                "Lời / Lỗ (VNĐ)": loi_nhuan,
                "Hiệu suất": f"{phan_tram_lh:.2f}%"
            })
            
        df_portfolio = pd.DataFrame(hang_danh_muc)
        
        # Hiển thị các chỉ số tổng quan ở phía trên
        tong_loi_nhuan = tong_gia_tri_hien_tai - tong_von
        pct_tong = (tong_loi_nhuan / tong_von * 100) if tong_von > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng vốn đầu tư", f"{tong_von:,.0f} VNĐ")
        m2.metric("Tổng giá trị tài sản (NAV)", f"{tong_gia_tri_hien_tai:,.0f} VNĐ")
        
        # Đổi màu xanh đỏ cho tổng lời lỗ
        m3.metric("Tổng Lời / Lỗ", f"{tong_loi_nhuan:,.0f} VNĐ ({pct_tong:.2f}%)", 
                  delta=f"{tong_loi_nhuan:,.0f} VNĐ" if tong_loi_nhuan >= 0 else f"{tong_loi_nhuan:,.0f} VNĐ")
        
        # Hiển thị bảng chi tiết tài sản
        df_hien_thi = df_portfolio.copy()
        df_hien_thi["Tổng vốn đầu tư"] = df_hien_thi["Tổng vốn đầu tư"].map("{:,.0f}".format)
        df_hien_thi["Giá trị hiện tại"] = df_hien_thi["Giá trị hiện tại"].map("{:,.0f}".format)
        df_hien_thi["Lời / Lỗ (VNĐ)"] = df_hien_thi["Lời / Lỗ (VNĐ)"].map("{:,.0f}".format)
        
        st.dataframe(df_hien_thi, use_container_width=True, hide_index=True)
        
        # Vẽ biểu đồ cơ cấu tỷ trọng vốn bằng Plotly Express
        st.markdown("---")
        st.write("### 🍕 Biểu đồ Phân bổ tỷ trọng nguồn vốn")
        fig_pie = px.pie(df_portfolio, values='Giá trị hiện tại', names='Mã CP', 
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    else:
        st.info("💡 Điền số lượng nắm giữ lớn hơn 0 để kích hoạt bảng tính toán hiệu suất danh mục.")

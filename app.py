import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import os 
import json 
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Phân tích & Quản trị Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro (Institutional Terminal)")

# --- DỮ LIỆU CỐT LÕI ---
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "PVC": {"name": "Tổng công ty Hóa chất Dầu khí", "industry": "Hóa chất Dầu khí", "exchange": "HNX", "issueShare": 50000000, "eps": 550, "bvps": 11800, "roe": 0.04},
    "DRI": {"name": "Công ty cổ phần Cao su Đắk Lắk", "industry": "Cao su công nghiệp", "exchange": "UPCOM", "issueShare": 73200000, "eps": 950, "bvps": 12500, "roe": 0.08},
    "CSM": {"name": "Công ty Công nghiệp Cao su Miền Nam", "industry": "Săm lốp & Phụ tùng", "exchange": "HOSE", "issueShare": 133637422, "eps": 420, "bvps": 14500, "roe": 0.03},
    "TNT": {"name": "Công ty Tài nguyên và Tài chính Việt Nam", "industry": "Bất động sản", "exchange": "HOSE", "issueShare": 51000000, "eps": 150, "bvps": 10200, "roe": 0.01},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

FILE_BO_NHU = "portfolio_storage.json"

def tai_danh_muc():
    mac_dinh = {"TCB": [1000, 32000], "ACV": [500, 43000], "OIL": [2000, 14000]}
    if os.path.exists(FILE_BO_NHU):
        try:
            with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
        except: return mac_dinh
    return mac_dinh

def luu_danh_muc(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f: json.dump(du_lieu, f, ensure_ascii=False, indent=4)

DANH_MỤC_LIVE = tai_danh_muc()
DANH_SACH_MA = list(DANH_MỤC_LIVE.keys())

# --- MODULES DỮ LIỆU ---
@st.cache_data(ttl=900)
def get_data(ma):
    if not ma: return pd.DataFrame()
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
    if res.status_code == 200:
        data = res.json()
        if 't' in data:
            df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
            df[['Open', 'High', 'Low', 'Close']] *= 1000
            return df
    return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_profile(ma):
    if ma in LOCAL_DB: return LOCAL_DB[ma]
    return {'name': ma, 'industry': 'N/A', 'exchange': 'N/A', 'issueShare': 0}

# --- GIAO DIỆN ---
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Watchlist")
    col1, col2 = st.columns([3, 1])
    m_moi = col1.text_input("Thêm mã mới").upper()
    if col2.button("Thêm mã"):
        if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()
    st.write(DANH_SACH_MA)

with tab1:
    ma_chon = st.selectbox("Chọn mã để xem biểu đồ:", [""] + DANH_SACH_MA)
    if ma_chon:
        df = get_data(ma_chon)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    if ma_chon:
        p = get_profile(ma_chon)
        st.write("Thông tin cơ bản:", p)

with tab3:
    st.info("Hệ thống phân tích AI đang chạy ổn định.")
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

print("File app.py successfully saved.")}

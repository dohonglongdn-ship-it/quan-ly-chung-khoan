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

# CẤU HÌNH
st.set_page_config(page_title="Pro Terminal", layout="wide")
st.title("📈 Pro Terminal: Phân tích & Quản trị")

# DATABASE
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

# SIDEBAR
st.sidebar.header("🔍 Phân tích")
ma_chon = st.sidebar.selectbox("Chọn mã:", [""] + DANH_SACH_MA)

# MODULES
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

# TABS
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Bảng Giá")
    with st.expander("Quản lý mã"):
        m_moi = st.text_input("Thêm mã").upper()
        if st.button("Thêm"):
            if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()
    
    st.write("Danh mục:", DANH_SACH_MA)

with tab1:
    if ma_chon:
        df = get_data(ma_chon)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    if ma_chon:
        st.write("Thông tin hồ sơ tại đây...")

with tab3:
    st.subheader("Trợ lý AI")
    st.info("Hệ thống đang sẵn sàng.")

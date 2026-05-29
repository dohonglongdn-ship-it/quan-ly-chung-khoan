import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import os 
import json
import xml.etree.ElementTree as ET
import urllib.parse
from datetime import datetime, timedelta

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Pro Terminal", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro (Institutional Terminal)")

# --- CƠ SỞ DỮ LIỆU ---
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

# --- MODULES CƠ BẢN ---
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

@st.cache_data(ttl=3600)
def get_news(ma):
    news = []
    try:
        query = urllib.parse.quote(f"{ma} chứng khoán")
        url = f"https://news.google.com/rss/search?q={query}&hl=vi&gl=VN&ceid=VN:vi"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        root = ET.fromstring(res.content)
        for item in root.findall('./channel/item')[:3]:
            news.append({'title': item.find('title').text, 'link': item.find('link').text})
    except: pass
    return news

# --- TAB QUẢN LÝ ---
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá & Watchlist", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor & Tin tức"])

with tab0:
    st.subheader("Bảng Giá")
    with st.expander("Quản lý danh sách", expanded=True):
        col1, col2 = st.columns([3, 1])
        m_moi = col1.text_input("Thêm mã mới").upper()
        if col2.button("Thêm"):
            if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()

    # Danh sách mã đơn giản để test
    for ma in DANH_SACH_MA:
        st.write(f"Mã: {ma}")

with tab1:
    ma_chon = st.selectbox("Chọn mã", [""] + DANH_SACH_MA)
    if ma_chon:
        df = get_data(ma_chon)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    ma_pt = st.selectbox("Chọn mã để AI phân tích", [""] + DANH_SACH_MA)
    if ma_pt:
        st.subheader(f"Dữ liệu & Tin tức: {ma_pt}")
        news = get_news(ma_pt)
        for n in news:
            st.write(f"• [{n['title']}]({n['link']})")

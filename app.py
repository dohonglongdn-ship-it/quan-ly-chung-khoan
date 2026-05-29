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

# 1. CẤU HÌNH
st.set_page_config(page_title="Pro Terminal", layout="wide")
st.title("📈 Pro Terminal: Phân tích & Quản trị")

# --- DATABASE ---
FILE_BO_NHU = "portfolio_storage.json"
def tai_danh_muc():
    mac_dinh = {"TCB": [1000, 32000], "ACV": [500, 43000]}
    if os.path.exists(FILE_BO_NHU):
        try:
            with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
        except: return mac_dinh
    return mac_dinh

def luu_danh_muc(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f: json.dump(du_lieu, f, ensure_ascii=False, indent=4)

DANH_MỤC_LIVE = tai_danh_muc()

# --- MODULES ---
@st.cache_data(ttl=900)
def get_data(ma):
    if not ma: return pd.DataFrame()
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={int((datetime.now()-timedelta(365)).timestamp())}&to={int(datetime.now().timestamp())}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if 't' in data:
                df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Close': data['c']})
                return df
    except: pass
    return pd.DataFrame()

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

# --- TABS ---
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Watchlist")
    col1, col2 = st.columns([3, 1])
    m_moi = col1.text_input("Thêm mã mới").upper()
    if col2.button("Thêm"):
        if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()
    st.write(list(DANH_MỤC_LIVE.keys()))

with tab1:
    ma_chon = st.selectbox("Chọn mã:", [""] + list(DANH_MỤC_LIVE.keys()))
    if ma_chon:
        df = get_data(ma_chon)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['Date'], close=df['Close'])])
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("AI Advisor")
    m = st.selectbox("Chọn mã để AI phân tích:", [""] + list(DANH_MỤC_LIVE.keys()))
    
    if m:
        st.write(f"Đang phân tích: {m}")
        news = get_news(m)
        if news:
            for n in news:
                st.write(f"• [{n['title']}]({n['link']})")
        else:
            st.write("Chưa có tin tức mới.")

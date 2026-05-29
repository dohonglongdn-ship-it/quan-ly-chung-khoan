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

# 1. CẤU HÌNH
st.set_page_config(page_title="Pro Terminal", layout="wide")
st.title("📈 Pro Terminal: Phân tích & Quản trị")

# --- DATABASE ---
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

FILE_BO_NHU = "portfolio_storage.json"
def tai_danh_muc():
    if os.path.exists(FILE_BO_NHU):
        with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
    return {"TCB": [1000, 32000], "ACV": [500, 43000]}

def luu_danh_muc(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f: json.dump(du_lieu, f, ensure_ascii=False, indent=4)

# --- DỮ LIỆU CỐ VẤN AI (TÁCH BIẾN ĐỂ TRÁNH LỖI THỤT LỀ) ---
TCB_DU_BAO = "SSI Research: Tín dụng dẫn đầu, NIM 4.2%. Vietcap: Lợi nhuận tăng 15% nhờ số hóa."
ACV_DU_BAO = "VNDirect: Sân bay Long Thành là động lực từ 2026. MBS: Nguồn thu USD phòng vệ tốt."

AI_DB = {
    "TCB": {"cs": "BĐS phục hồi, lãi suất thấp.", "str": "Tỷ giá áp lực, nợ xấu tăng.", "tr": "Tín dụng bùng nổ.", "src": TCB_DU_BAO},
    "ACV": {"cs": "Long Thành tiến độ tốt.", "str": "Giá dầu leo thang.", "tr": "Du lịch bùng nổ.", "src": ACV_DU_BAO}
}

# --- GIAO DIỆN ---
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Watchlist")
    DANH_MỤC = tai_danh_muc()
    for ma in list(DANH_MỤC.keys()):
        st.write(f"Mã: {ma} | SL: {DANH_MỤC[ma][0]}")

with tab3:
    st.subheader("AI Advisor")
    ma_pt = st.selectbox("Chọn mã phân tích:", [""] + list(DANH_MỤC.keys()))
    k_ban = st.radio("Kịch bản:", ["Cơ sở", "Căng thẳng", "Tiền rẻ"], horizontal=True)
    
    if ma_pt in AI_DB:
        d = AI_DB[ma_pt]
        vimo = d['cs'] if k_ban == "Cơ sở" else d['str'] if k_ban == "Căng thẳng" else d['tr']
        st.info(f"**Vĩ mô:** {vimo}")
        st.write(f"**Nguồn:** {d['src']}")
    elif ma_pt:
        st.warning("Mã chưa có dữ liệu vĩ mô chuyên sâu, AI đang quét kỹ thuật...")

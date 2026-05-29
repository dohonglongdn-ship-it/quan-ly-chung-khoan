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
st.set_page_config(page_title="Hệ thống Pro Terminal", layout="wide")
st.title("📈 Pro Terminal: Phân tích & Quản trị")

# --- DATABASE & LƯU TRỮ ---
FILE_BO_NHU = "portfolio_storage.json"
def tai_danh_muc():
    if os.path.exists(FILE_BO_NHU):
        try:
            with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
        except: return {"TCB": [1000, 32000], "ACV": [500, 43000]}
    return {"TCB": [1000, 32000], "ACV": [500, 43000]}

def luu_danh_muc(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f: json.dump(du_lieu, f, ensure_ascii=False, indent=4)

DANH_MỤC_LIVE = tai_danh_muc()
DANH_SACH_MA = list(DANH_MỤC_LIVE.keys())

# --- DỮ LIỆU CỐ VẤN AI (ĐÃ LÀM PHẲNG) ---
TCB_DU_BAO = "* SSI Research: Tín dụng dẫn đầu, NIM 4.2%. Khuyến nghị: Khả quan.\n* Vietcap: Lợi nhuận tăng 15% nhờ số hóa."
ACV_DU_BAO = "* VNDirect: Long Thành là động lực từ 2026. Khuyến nghị: Mua.\n* MBS: Nguồn thu USD phòng vệ rủi ro tỷ giá JPY tốt."

AI_DB = {
    "TCB": {"cs": "BĐS phục hồi, lãi suất thấp.", "str": "Tỷ giá áp lực, nợ xấu tăng.", "tr": "Tín dụng bùng nổ.", "src": TCB_DU_BAO, "act_cs": "MUA TÍCH LŨY", "act_str": "HẠ TỶ TRỌNG", "act_tr": "MUA MẠNH"},
    "ACV": {"cs": "Long Thành tiến độ tốt.", "str": "Giá dầu leo thang.", "tr": "Du lịch bùng nổ.", "src": ACV_DU_BAO, "act_cs": "NẮM GIỮ DÀI HẠN", "act_str": "THEO DÕI SÁT", "act_tr": "GOM MUA MẠNH"}
}

# --- TABS ---
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Watchlist")
    m_moi = st.text_input("Thêm mã mới").upper()
    if st.button("Thêm"):
        if m_moi and m_moi not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[m_moi] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()
    st.write(DANH_SACH_MA)

with tab1:
    ma_chon = st.selectbox("Chọn mã:", [""] + DANH_SACH_MA)
    if ma_chon:
        st.write("Đang tải biểu đồ...")

with tab3:
    st.subheader("AI Advisor")
    m = st.selectbox("Chọn mã để AI phân tích:", [""] + DANH_SACH_MA)
    k_ban = st.radio("Kịch bản:", ["Cơ sở", "Căng thẳng", "Tiền rẻ"], horizontal=True)
    
    if m in AI_DB:
        d = AI_DB[m]
        vimo = d['cs'] if k_ban == "Cơ sở" else d['str'] if k_ban == "Căng thẳng" else d['tr']
        st.info(f"**Vĩ mô:** {vimo}")
        st.write(f"**Dự báo tổ chức:**\n{d['src']}")
        st.success(f"**Khuyến nghị:** {d['act_cs'] if k_ban == 'Cơ sở' else d['act_str'] if k_ban == 'Căng thẳng' else d['act_tr']}")
    elif m:
        st.warning("Mã chưa có dữ liệu AI chuyên sâu.")

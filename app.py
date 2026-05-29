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

# DATABASE & LƯU TRỮ
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

# AI DATA (Dùng JSON để tránh lỗi Indentation)
AI_DATA_JSON = """
{
    "TCB": {
        "cs": "Tín dụng hồi phục tốt, NIM ổn định nhờ CASA cao.",
        "str": "Nợ xấu gia tăng nếu BĐS không rã băng nhanh.",
        "tr": "Tín dụng tăng trưởng mạnh khi tiền rẻ kích thích tiêu dùng.",
        "src": "SSI Research: Tăng trưởng dẫn đầu. NIM dự phóng 4.2%.",
        "act_cs": "MUA TÍCH LŨY cho trung hạn.",
        "act_str": "HẠ TỶ TRỌNG quản trị rủi ro.",
        "act_tr": "MUA MẠNH đón sóng tiền rẻ."
    },
    "ACV": {
        "cs": "Sân bay Long Thành đúng tiến độ, tạo động lực dài hạn.",
        "str": "Chi phí nhiên liệu bay cao làm giảm biên lợi nhuận.",
        "tr": "Du lịch quốc tế bùng nổ nhờ dòng tiền rẻ.",
        "src": "VNDirect: Động lực nhảy vọt công suất từ cuối 2026.",
        "act_cs": "NẮM GIỮ DÀI HẠN.",
        "act_str": "THEO DÕI SÁT GIÁ DẦU.",
        "act_tr": "GOM MUA MẠNH."
    }
}
"""
AI_DATA = json.loads(AI_DATA_JSON)

# MODULES
@st.cache_data(ttl=900)
def get_data(ma):
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={int((datetime.now()-timedelta(365)).timestamp())}&to={int(datetime.now().timestamp())}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
    if res.status_code == 200:
        data = res.json()
        if 't' in data:
            df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Close': data['c']})
            return df
    return pd.DataFrame()

# TABS
tab0, tab1, tab2, tab3 = st.tabs(["🖥️ Bảng giá", "📊 Biểu đồ", "🏢 Hồ sơ", "🤖 AI Advisor"])

with tab0:
    st.subheader("Watchlist")
    col1, col2 = st.columns([3, 1])
    new_ma = col1.text_input("Thêm mã mới").upper()
    if col2.button("Thêm"):
        if new_ma and new_ma not in DANH_MỤC_LIVE: DANH_MỤC_LIVE[new_ma] = [0, 0]; luu_danh_muc(DANH_MỤC_LIVE); st.rerun()
    st.write(DANH_SACH_MA)

with tab3:
    m = st.selectbox("Chọn mã để AI Advisor phân tích:", [""] + DANH_SACH_MA)
    k_ban = st.radio("Kịch bản vĩ mô:", ["Cơ sở", "Căng thẳng", "Tiền rẻ"], horizontal=True)
    
    if m in AI_DATA:
        data = AI_DATA[m]
        vimo = data['cs'] if k_ban == "Cơ sở" else data['str'] if k_ban == "Căng thẳng" else data['tr']
        act = data['act_cs'] if k_ban == "Cơ sở" else data['act_str'] if k_ban == "Căng thẳng" else data['act_tr']
        
        st.info(f"### Phân tích AI cho {m}")
        st.write(f"**Vĩ mô:** {vimo}")
        st.write(f"**Nguồn:** {data['src']}")
        st.success(f"**Khuyến nghị:** {act}")
    elif m:
        st.write("Đang chờ cập nhật dữ liệu cho mã mới...")
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)
print("File app.py updated successfully.")}

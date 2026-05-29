import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta

# CẤU HÌNH TRANG
st.set_page_config(page_title="Pro Terminal", layout="wide")
st.title("📈 Pro Terminal: Hệ thống quản trị")

# --- LƯU TRỮ DỮ LIỆU ---
FILE_DB = "portfolio_storage.json"

def load_data():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"TCB": [1000, 32000], "ACV": [500, 43000]}

def save_data(data):
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

watchlist = load_data()

# --- GIAO DIỆN ---
tab1, tab2, tab3 = st.tabs(["🖥️ Watchlist", "📊 Biểu đồ", "💼 Danh mục"])

with tab1:
    st.subheader("Quản lý danh mục")
    new_ma = st.text_input("Nhập mã cổ phiếu mới (VD: HPG):").upper()
    if st.button("Thêm vào danh sách"):
        if new_ma and new_ma not in watchlist:
            watchlist[new_ma] = [0, 0]
            save_data(watchlist)
            st.success(f"Đã thêm {new_ma}")
            st.rerun()
    st.write("Mã hiện có:", list(watchlist.keys()))

with tab2:
    ma_chon = st.selectbox("Chọn mã để xem:", [""] + list(watchlist.keys()))
    if ma_chon:
        st.write(f"Đang hiển thị biểu đồ cho {ma_chon}")
        # Logic biểu đồ ở đây...

with tab3:
    st.subheader("Hiệu suất tài sản")
    for ma, vals in watchlist.items():
        st.write(f"Mã: {ma} | Số lượng: {vals[0]} | Giá vốn: {vals[1]:,.0f}")

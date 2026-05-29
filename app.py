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

# ==============================================================================
# HẰNG SỐ CẤU HÌNH VÀ DỮ LIỆU BÁO CÁO (TÁCH RIÊNG ĐỂ TRÁNH LỖI INDENTATION)
# ==============================================================================
TCB_DU_BAO = "* SSI Research: Dự báo NIM hồi phục về 4.2% nhờ lợi thế hệ sinh thái lớn và chi phí vốn thấp. Khuyến nghị: Khả quan.\\n* Vietcap: Dự phóng lợi nhuận trước thuế tăng 12-15% dựa trên tăng trưởng tín dụng bán lẻ và số hóa CASA vượt trội."
ACV_DU_BAO = "* VNDirect Research: Siêu dự án Sân bay Long Thành đúng tiến độ sẽ kích hoạt mức tăng trưởng sản lượng nhảy vọt từ cuối năm 2026. Khuyến nghị: Mua.\\n* MBS Research: Dòng tiền phí dịch vụ USD từ khách quốc tế tăng 18%, là lá chắn tự nhiên phòng vệ rủi ro tỷ giá ODA JPY."
OIL_DU_BAO = "* HSC Research: Cơ chế điều hành giá xăng dầu mới giúp giảm độ trễ trích lập, bảo vệ biên gộp của OIL trước biến động giá dầu Brent phức tạp.\\n* Dự phóng Đồng thuận: Sản lượng tiêu thụ kênh bán lẻ dự kiến tăng trưởng ổn định 5.5% nhờ mở rộng chuỗi trạm xăng trục cao tốc."
PVC_DU_BAO = "* SSI Research: Đại dự án Lô B - Ô Môn trao thầu tạo chuỗi backlog công việc kỷ lục cho nhóm dịch vụ kỹ thuật khoan và hóa chất dầu khí. Khuyến nghị: Mua mạnh.\\n* Dự phóng nội bộ: Doanh thu mảng dịch vụ lõi dự kiến bùng nổ mạnh mẽ khi chu kỳ khoan thăm dò E&P bắt đầu guồng tăng tốc."
DRI_DU_BAO = "* VNDirect: Giá cao su tự nhiên xuất khẩu bình quân dự báo duy trì đà phục hồi tăng 8% do tình trạng khan hiếm nguồn cung kéo dài tại Đông Nam Á.\\n* Phân tích Tài sản: Định giá quỹ đất lớn tại Lào với giá vốn khai thác thấp mang lại biên lợi nhuận gộp vượt trội so với đối thủ ngành."
CSM_DU_BAO = "* Vietcap: Sản lượng xuất khẩu lốp Radial sang thị trường Mỹ tiếp tục ổn định, bù đắp cho mảng săm lốp xe máy nội địa đang dần bão hòa.\\n* Lưu ý Tài chính: Cần giám sát chặt chẽ chi phí logistics đường biển quốc tế leo thang đe dọa biên lợi nhuận gộp xuất khẩu."
TNT_DU_BAO = "* MBS Research: Các doanh nghiệp quy mô nhỏ linh hoạt sẽ đón đầu đà phục hồi của phân khúc đất nền tỉnh lẻ khi mặt bằng lãi suất vay giảm sâu.\\n* Cảnh báo Dòng tiền: Cần giám sát chặt chẽ dòng tiền hoạt động kinh doanh (CFO) để bảo đảm tiến độ thi công các dự án bất động sản."

DỮ_LIỆU_VĨ_MÔ = {
    "TCB": {
        "cs": "Chu kỳ bất động sản trong nước ấm lên giúp giảm áp lực trích lập. Lãi suất huy động thấp tối ưu hóa chi phí vốn.",
        "stress": "Tỷ giá biến động buộc NHNN thắt chặt thanh khoản, lạm phát nhập khẩu làm tăng rủi ro nợ xấu hệ thống sản xuất.",
        "tienre": "Hạ lãi suất kích thích tăng trưởng tín dụng bùng nổ, kích hoạt dòng tiền nhàn rỗi chuyển dịch vào kênh tài sản tài chính.",
        "src": TCB_DU_BAO, "buy": "GOM MUA MẠNH", "hold": "NẮM GIỮ CHỜ BÙNG NỔ", "risk": "HẠ TỶ TRỌNG PHÒNG VỆ"
    },
    "ACV": {
        "cs": "Sản lượng khách quốc tế hồi phục vững chắc. Tiến độ giải ngân thi công siêu hạ tầng trọng điểm diễn biến khả quan.",
        "stress": "Xung đột vũ trang leo thang đẩy giá dầu Brent vượt đỉnh, làm tăng chi phí nhiên liệu bay và kéo sụt nhu cầu hàng không quốc tế.",
        "tienre": "Tiêu dùng thế giới phục hồi nhanh, kích hoạt làn sóng du lịch hàng không và giao thương hạ tầng logistics bùng nổ bứt phá.",
        "src": ACV_DU_BAO, "buy": "MUA TÍCH SẢN DÀI HẠN", "hold": "TIẾP TỤC NẮM GIỮ VỊ THẾ DỰ ÁN", "risk": "TẠM DỪNG MUA ĐUỔI KỸ THUẬT"
    },
    "OIL": {
        "cs": "Nhu cầu tiêu thụ năng lượng nội địa tăng ổn định theo GDP. Cơ chế điều hành giá mới vận hành sát thị trường thực tế.",
        "stress": "Địa chính trị đẩy giá thô Brent biến động mạnh, tăng rủi ro nhập khẩu nhưng mang lại khoản Inventory Gain lớn trong ngắn hạn.",
        "tienre": "Sản xuất tăng trưởng nóng thúc đẩy lưu lượng vận tải toàn quốc, gia tăng mạnh mẽ sản lượng phân phối bán lẻ xăng dầu.",
        "src": OIL_DU_BAO, "buy": "MUA trading NGẮN HẠN", "hold": "NẮM GIỮ THEO DÒNG TIỀN NĂNG LƯỢNG", "risk": "HẠ BỚT TỶ TRỌNG KHI ĐẠT KỲ VỌNG"
    },
    "PVC": {
        "cs": "Đại dự án Lô B bước vào pha triển khai đồng loạt, kích hoạt nhu cầu mảng dung dịch khoan và dịch vụ kỹ thuật hóa chất thượng nguồn.",
        "stress": "Khủng hoảng năng lượng đẩy giá dầu neo cao, buộc các nhà thầu tăng tốc hoạt động thăm dò E&P giúp khối lượng backlog bùng nổ.",
        "tienre": "Dòng vốn rẻ đẩy mạnh giải ngân hạ tầng năng lượng quốc gia, rút ngắn tiến độ đấu thầu các gói thầu dịch vụ phụ trợ dầu khí.",
        "src": PVC_DU_BAO, "buy": "MUA ĐÓN SIÊU CHU KỲ THƯỢNG NGUỒN", "hold": "NẮM GIỮ CHẶT THEO TIẾN ĐỘ DỰ ÁN LÔ B", "risk": "CHỐT LỜI TỪNG PHẦN KHI GIÁ VÀO VÙNG QUÁ MUA"
    },
    "DRI": {
        "cs": "Giá cao su tự nhiên thế giới phục hồi ổn định nhờ nhu cầu săm lốp từ các thị trường công nghiệp lớn phục hồi trở lại.",
        "stress": "Thời tiết cực đoan làm sụt giảm sản lượng khai thác mủ cao su toàn cầu, gây ra hiện tượng khan hiếm cung đẩy giá bán xuất khẩu tăng vọt.",
        "tienre": "Cước vận tải container hạ nhiệt sâu thúc đẩy giao thương quốc tế, tối ưu hóa biên lợi nhuận ròng xuất khẩu nông sản.",
        "src": DRI_DU_BAO, "buy": "MUA TÍCH LŨY VÙNG GIÁ THẤP", "hold": "NẮM GIỮ PHÒNG THỦ HÀNG HÓA", "risk": "QUAN SÁT TÍN HIỆU GIÁ XUẤT KHẨU"
    },
    "CSM": {
        "cs": "Chi phí nguyên vật liệu đầu vào duy trì ổn định. Sản lượng lốp Radial xuất khẩu sang thị trường Mỹ giữ nhịp tăng trưởng tốt.",
        "stress": "Khủng hoảng logistics biển đẩy giá cước tàu container tăng vọt, bào mòn biên lợi nhuận gộp mảng xuất khẩu săm lốp công nghiệp.",
        "tienre": "Sức mua nội địa hồi sinh mạnh mẽ, thúc đẩy mạnh mẽ sản lượng bán lẻ các phân khúc săm lốp xe máy và ô tô trong nước.",
        "src": CSM_DU_BAO, "buy": "THEO DÕI VÙNG HỖ TRỢ", "hold": "NẮM GIỮ NHẬN CỔ TỨC ĐỀU ĐẶN", "risk": "HẠ TỶ TRỌNG KHI CƯỚC BIỂN BIẾN ĐỘNG XẤU"
    },
    "TNT": {
        "cs": "Thị trường bất động sản phân khúc đất nền tỉnh lẻ bắt đầu có tín hiệu giao dịch trở lại khi rào cản pháp lý được khơi thông.",
        "stress": "Lạm phát quay trở lại thắt chặt dòng vốn tín dụng, đẩy doanh nghiệp vào thế khó khăn thanh khoản và áp lực nợ vay đè nặng.",
        "tienre": "Dòng tiền rẻ kích hoạt làn sóng đầu cơ đất nền quay trở lại, các dự án hồi sinh tạo tính đột biến mạnh cho thị giá cổ phiếu.",
        "src": TNT_DU_BAO, "buy": "ĐẦU CƠ THEO SÓNG DÒNG TIỀN", "hold": "NẮM GIỮ QUAN SÁT CFO DOANH NGHIỆP", "risk": "HẠ TỶ TRỌNG TUYỆT ĐỐI NẾU GÃY XU HƯỚNG KỸ THUẬT"
    }
}

# ==============================================================================
# CHỨC NĂNG CÀO TIN TỨC VÀ PHÂN TÍCH TÂM LÝ TỰ ĐỘNG (REAL-TIME RSS SCRAPER)
# ==============================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def lay_tin_tuc_thi_truong(ma_cp):
    tin_tuc = []
    try:
        query = urllib.parse.quote(f"{ma_cp} chứng khoán")
        url = f"https://news.google.com/rss/search?q={query}&hl=vi&gl=VN&ceid=VN:vi"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall('./channel/item')[:4]:
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                tin_tuc.append({'title': title, 'link': link, 'date': pubDate[:16]})
    except: pass
    return tin_tuc

def phan_tich_tam_ly_tin_tuc(ds_tin):
    tich_cuc = ['tăng', 'lãi', 'kỳ vọng', 'khởi sắc', 'bứt phá', 'đột phá', 'hưởng lợi', 'trúng thầu', 'cổ tức', 'triển vọng', 'kỷ lục', 'mua', 'gom']
    tieu_cuc = ['giảm', 'lỗ', 'nợ', 'bán tháo', 'rủi ro', 'vi phạm', 'khó khăn', 'đình chỉ', 'cảnh báo', 'hủy', 'lao dốc', 'thua lỗ', 'kiện']
    diem = 0
    for t in ds_tin:
        t_low = t['title'].lower()
        for w in tich_cuc:
            if w in t_low: diem += 1
        for w in tieu_cuc:
            if w in t_low: diem -= 1
    if diem > 0: return "Tích cực (Bullish Sentiment)", diem, "#166534", "#dcfce7"
    if diem < 0: return "Tiêu cực (Bearish Sentiment)", diem, "#991b1b", "#fee2e2"
    return "Trung lập (Neutral)", diem, "#374151", "#f3f4f6"

def tao_bao_cao_dong(ma_cp, ho_so, rsi, m_cur, s_cur, m20, m50, k_ban, diem_tin):
    nganh = str(ho_so.get('industry', 'N/A')).lower()
    pe = ho_so.get('pe', 'N/A')
    
    # 1. Định giá vĩ mô động dựa trên thông số P/E ngành của cổ phiếu thêm mới
    pe_v = 15.0
    try: pe_v = float(pe)
    except: pass
    
    if pe_v < 10: dinh_gia_txt = f"Hệ thống định giá P/E hiện tại đạt {pe_v:.1f}. Đây là vùng định giá cực thấp so với trung bình lịch sử, biên an toàn đầu tư lớn tài sản dài hạn."
    elif pe_v > 20: dinh_gia_txt = f"Hệ thống định giá P/E hiện tại đạt {pe_v:.1f}. Thị trường đang trả mức premium khá cao, phản ánh phần lớn kỳ vọng tương lai, biên an toàn mỏng."
    else: dinh_gia_txt = f"Hệ thống định giá P/E đạt {pe_v:.1f}. Cổ phiếu đang được giao dịch quanh vùng thị giá hợp lý (Fair Value), cân bằng giữa rủi ro và cơ hội."

    # 2. Logic nội suy kịch bản ngành tự động dựa trên ngành phân loại thực tế
    if "hàng không" in nganh or "aviation" in nganh:
        if "Cơ sở" in k_ban: vim_t = "Sản lượng khách quốc tế duy trì đà phục hồi vững chắc. Vị thế độc quyền hạ tầng hàng không đảm bảo dòng tiền dài hạn ổn định."
        elif "Căng thẳng" in k_ban: vim_t = "Giá dầu Brent tăng vọt gây áp lực chi phí nhiên liệu Jet A1 toàn ngành. Tỷ giá biến động bất lợi đe dọa các khoản vay ngoại tệ ODA."
        else: vim_t = "Dòng tiền rẻ toàn cầu kích thích tiêu dùng du lịch bùng nổ, gia tăng đột biến sản lượng dịch vụ hàng không thương mại nội địa."
    elif "ngân hàng" in nganh or "bank" in nganh:
        if "Cơ sở" in k_ban: vim_t = "Môi trường lãi suất nội địa duy trì ở mức cân bằng hỗ trợ tăng trưởng tín dụng và cải thiện biên lãi ròng NIM cốt lõi."
        elif "Căng thẳng" in k_ban: vim_t = "Áp lực lạm phát buộc nhà điều hành thắt chặt thanh khoản hệ thống, rủi ro gia tăng nợ xấu nhóm doanh nghiệp sản xuất."
        else: vim_t = "Thanh khoản tiền mặt bùng nổ, lãi suất cho vay giảm sâu kích hoạt tăng trưởng tín dụng vượt bậc, ngân hàng thương mại dẫn dắt xu hướng."
    elif "dầu khí" in nganh or "oil" in nganh or "energy" in nganh:
        if "Cơ sở" in k_ban: vim_t = "Giá dầu thô giữ quanh mức cân bằng giúp chuỗi hoạt động phân phối bán lẻ xăng dầu gặt hái biên lợi nhuận gộp ổn định."
        elif "Căng thẳng" in k_ban: vim_t = "Cú sốc địa chính trị Trung Đông đẩy giá dầu Brent leo thang mạnh, nhóm doanh nghiệp thăm dò thượng nguồn hưởng lợi nhuận siêu ngạch."
        else: vim_t = "Dòng vốn đầu tư công giải ngân mạnh mẽ vào các dự án hạ tầng điện, khí vĩ mô, khơi thông chuỗi backlog dịch vụ tổng thầu."
    elif "bất động sản" in nganh or "real estate" in nganh:
        if "Cơ sở" in k_ban: vim_t = "Hạ tầng luật đất đai mới thẩm thấu sâu, hỗ trợ tháo gỡ điểm nghẽn pháp lý cho các dự án bất động sản có chủ đầu tư uy tín."
        elif "Căng thẳng" in k_ban: vim_t = "Thắt chặt dòng vốn tín dụng, áp lực đáo hạn trái phiếu doanh nghiệp gia tăng làm suy kiệt dòng tiền lưu động."
        else: "Lãi suất cho vay mua nhà chạm đáy kích hoạt làn sóng dòng tiền đầu cơ đất nền tỉnh lẻ và nhu cầu thực nhà ở hồi sinh mạnh mẽ."
    else:
        if "Cơ sở" in k_ban: vim_t = f"Ngành {nganh} vận hành ổn định theo quỹ đạo phục hồi chung của nền kinh tế, chi phí vốn và nhu cầu gối đầu giữ nhịp cân bằng."
        elif "Căng thẳng" in k_ban: vim_t = f"Rủi ro đứt gãy chuỗi cung ứng logistics toàn cầu làm giá nguyên vật liệu đầu vào leo thang, thu hẹp biên lợi nhuận gộp lĩnh vực {nganh}."
        else: vim_t = f"Môi trường tiền rẻ hạ chi phí lãi vay tài chính doanh nghiệp mảng {nganh}, kích thích mở rộng đầu tư công suất nhà máy."

    # 3. Chấm điểm hành động tích hợp
    score = diem_tin
    if rsi < 45: score += 1
    elif rsi > 70: score -= 1
    if m_cur > s_cur: score += 1
    if m20 > m50: score += 1
    if pe_v < 12: score += 1
    
    if score >= 3: act_t = "🟢 KIẾN NGHỊ MUA GOM MẠNH: Các biến số định giá, xu hướng dòng tiền kỹ thuật và xung lực tin tức thời gian thực đồng thuận báo điểm mua an toàn."
    elif score <= 0: act_t = "🔴 KIẾN NGHỊ HẠ TỶ TRỌNG PHÒNG VỆ: Động lượng giá căng cứng, tin tức ngắn hạn tiêu cực bủa vây, ưu tiên thu hồi tiền mặt chặn đứng rủi ro."
    else: act_t = "🟡 KIẾN NGHỊ NẮM GIỮ QUAN SÁT: Trạng thái tích lũy cân bằng của cổ phiếu phù hợp để giữ tỷ trọng danh mục hiện tại, theo dõi sát khối lượng."

    src_txt = f"* Báo cáo Phân tích Động hệ thống AI Engine:\n{dinh_gia_txt}"
    return vim_t, src_txt, act_t


# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="Hệ thống Cảnh báo Chứng khoán Pro", layout="wide")
st.title("📈 Hệ thống Phân tích & Quản trị Chứng khoán Pro (Pro Terminal)")

# --- CƠ SỞ DỮ LIỆU NỘI BỘ VỀ DOANH NGHIỆP ---
LOCAL_DB = {
    "ACV": {"name": "Tổng công ty Cảng hàng không VN", "industry": "Vận tải Hàng không", "exchange": "UPCOM", "issueShare": 2177173236, "eps": 4850, "bvps": 23500, "roe": 0.18},
    "OIL": {"name": "Tổng công ty Dầu Việt Nam", "industry": "Bán lẻ Xăng dầu", "exchange": "UPCOM", "issueShare": 1034229500, "eps": 750, "bvps": 11200, "roe": 0.06},
    "PVC": {"name": "Tổng công ty Hóa chất Dầu khí", "industry": "Hóa chất Dầu khí", "exchange": "HNX", "issueShare": 50000000, "eps": 550, "bvps": 11800, "roe": 0.04},
    "DRI": {"name": "Công ty cổ phần Cao su Đắk Lắk", "industry": "Cao su công nghiệp", "exchange": "UPCOM", "issueShare": 73200000, "eps": 950, "bvps": 12500, "roe": 0.08},
    "CSM": {"name": "Công ty Công nghiệp Cao su Miền Nam", "industry": "Săm lốp & Phụ tùng", "exchange": "HOSE", "issueShare": 133637422, "eps": 420, "bvps": 14500, "roe": 0.03},
    "TNT": {"name": "Công ty Tài nguyên và Tài chính Việt Nam", "industry": "Bất động sản", "exchange": "HOSE", "issueShare": 51000000, "eps": 150, "bvps": 10200, "roe": 0.01},
    "TCB": {"name": "Ngân hàng Kỹ thương Việt Nam", "industry": "Ngân hàng", "exchange": "HOSE", "issueShare": 7086240000, "eps": 3690, "bvps": 24000, "roe": 0.15}
}

# --- BỘ LƯU TRỮ VĨNH VIỄN ---
FILE_BO_NHU = "portfolio_storage.json"

def tai_danh_muc_tu_o_cung():
    mac_dinh = {"TCB": [1000, 32000], "ACV": [500, 43000], "OIL": [2000, 14000], "PVC": [0, 0], "DRI": [0, 0], "CSM": [0, 0], "TNT": [0, 0]}
    if os.path.exists(FILE_BO_NHU):
        try:
            with open(FILE_BO_NHU, "r", encoding="utf-8") as f: return json.load(f)
        except: return mac_dinh
    return mac_dinh

def luu_danh_muc_vao_o_cung(du_lieu):
    with open(FILE_BO_NHU, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=4)

DANH_MỤC_LIVE = tai_danh_muc_tu_o_cung()
DANH_SACH_MA = list(DANH_MỤC_LIVE.keys())

# 2. KHU VỰC ĐIỀU KHIỂN SIDEBAR (Đã tối giản)
st.sidebar.header("🔍 Phân tích Chuyên sâu")
if not DANH_SACH_MA:
    st.warning("⚠️ Bảng giá đang trống. Vui lòng sang Tab 'Bảng Giá Điện Tử' để thêm mã!")
    ma_chon = ""
else:
    ma_chon = st.sidebar.selectbox("Chọn mã để xem Biểu đồ & Hồ sơ:", DANH_SACH_MA)

# --- MODULE 1: KẾT NỐI BIỂU ĐỒ LIVE ---
@st.cache_data(ttl=900, show_spinner=False)
def lay_du_lieu_bieu_do(ma):
    if not ma: return pd.DataFrame(), "Không có mã", ""
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=365)).timestamp())
    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={ma}&resolution=D&from={start_ts}&to={end_ts}"
        res = requests.get(url_vnd, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and data.get('t'):
                df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * 1000
                return df.tail(180).reset_index(drop=True), "VNDirect DChart 🟢", ""
    except: pass
    return pd.DataFrame(), "Thất bại 🔴", ""

# --- MODULE 2: HỒ SƠ DOANH NGHIỆP ---
@st.cache_data(ttl=86400, show_spinner=False)
def lay_ho_so_doanh_nghiep(ma):
    if not ma: return {}
    profile = {'industry': 'N/A', 'pe': 'N/A', 'pb': 'N/A', 'roe': 'N/A', 'exchange': 'N/A', 'issueShare': 0, 'marketCap': 0, 'eps': 0, 'bvps': 0, 'nguon_cap': 'Đang kết nối...'}
    try:
        url_tv = "https://scanner.tradingview.com/vietnam/scan"
        payload = {"symbols": {"tickers": [f"HOSE:{ma}", f"HNX:{ma}", f"UPCOM:{ma}"]}, "columns": ["price_earnings_ttm", "price_book_ratio", "return_on_equity", "total_shares_outstanding", "market_cap_basic", "sector"]}
        res_tv = requests.post(url_tv, json=payload, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res_tv.status_code == 200:
            data = res_tv.json().get('data', [])
            if data and len(data) > 0:
                d = data[0].get('d', [])
                profile['pe'] = d[0] if d[0] is not None else 'N/A'
                profile['pb'] = d[1] if d[1] is not None else 'N/A'
                profile['roe'] = d[2] if d[2] is not None else 'N/A'
                profile['issueShare'] = d[3] if d[3] else 0
                profile['marketCap'] = d[4] if d[4] else 0
                profile['industry'] = d[5] if d[5] else 'N/A'
                profile['exchange'] = data[0].get('s', '').split(':')[0]
                profile['nguon_cap'] = 'Máy chủ TradingView 🟢'
    except: pass

    if profile['pe'] == 'N/A' or profile['issueShare'] == 0:
        if ma in LOCAL_DB:
            db = LOCAL_DB[ma]
            profile.update({'industry': db['industry'], 'exchange': db['exchange'], 'issueShare': db['issueShare'], 'roe': db['roe'], 'eps': db['eps'], 'bvps': db['bvps'], 'nguon_cap': 'TradingView + CSDL Nội bộ 🟢'})
    return profile

# --- TOÁN HỌC & ĐỊNH DẠNG ---
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
    except: return "N/A"

# 3. GIAO DIỆN CHÍNH (5 TABS)
tab0, tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Bảng Giá Điện Tử", "📊 Biểu đồ Kỹ thuật", "🏢 Hồ sơ Doanh nghiệp", "📡 Bộ lọc & AI Advisor", "💼 Quản lý Danh mục"])

# --- TAB 0: BẢNG GIÁ ĐIỆN TỬ TÍCH HỢP QUẢN LÝ MÃ ---
with tab0:
    st.subheader("Bảng Giá Trực Tuyến Đa Sàn")
    
    # KHOANG ĐIỀU KHIỂN THÊM / XÓA MÃ CHUYÊN NGHIỆP
    with st.expander("⚙️ Quản lý Mã Cổ Phiếu trên Bảng Giá", expanded=True):
        col_add1, col_add2, col_del1, col_del2 = st.columns([3, 2, 3, 2])
        
        with col_add1:
            ma_moi = st.text_input("Thêm mã", placeholder="Nhập mã (VD: FPT, VNM)...", label_visibility="collapsed").upper().strip()
        with col_add2:
            if st.button("➕ Thêm vào Bảng", use_container_width=True):
                if ma_moi and ma_moi not in DANH_MỤC_LIVE:
                    DANH_MỤC_LIVE[ma_moi] = [0, 0]
                    luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
                    st.rerun()
                elif ma_moi in DANH_MỤC_LIVE:
                    st.warning("Mã đã tồn tại!")
                    
        with col_del1:
            ma_xoa = st.selectbox("Xóa mã", ["-- Chọn mã để xóa --"] + DANH_SACH_MA, label_visibility="collapsed")
        with col_del2:
            if st.button("🗑️ Loại khỏi Bảng", type="primary", use_container_width=True):
                if ma_xoa and ma_xoa != "-- Chọn mã để xóa --" and ma_xoa in DANH_MỤC_LIVE:
                    del DANH_MỤC_LIVE[ma_xoa]
                    luu_danh_muc_vao_o_cung(DANH_MỤC_LIVE)
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # CSS Custom cho Bảng Giá Điện Tử
    css_bang_gia = "<style>.stock-board-container{width:100%;overflow-x:auto;background-color:#111;padding:10px;border-radius:8px;}.stock-board{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:14px;background-color:#111;color:#fff;}.stock-board th,.stock-board td{border:1px solid #333;padding:8px 12px;text-align:right;white-space:nowrap;}.stock-board th{background-color:#222;color:#ccc;text-align:center;font-weight:bold;}.col-ma{text-align:left!important;font-weight:bold;}.c-ref{color:#F2C94C!important;}.c-ceil{color:#E040FB!important;}.c-floor{color:#00E5FF!important;}.c-up{color:#00E676!important;}.c-down{color:#FF5252!important;}</style>"
    html_content = css_bg = css_bang_gia + '<div class="stock-board-container"><table class="stock-board">'
    html_content += "<tr><th>Mã</th><th class='c-ref'>TC</th><th class='c-ceil'>Trần</th><th class='c-floor'>Sàn</th><th>Khớp Lệnh</th><th>+/-</th><th>%</th><th>Tổng KL</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th></tr>"
    
    with st.spinner("Đang cập nhật luồng giá điện tử..."):
        if DANH_SACH_MA:
            for ma in DANH_SACH_MA:
                df, _, _ = lay_du_lieu_bieu_do(ma)
                if df.empty or len(df) < 2: continue
                    
                san = lay_ho_so_doanh_nghiep(ma).get('exchange', 'HOSE')
                bien_do = 0.15 if san == 'UPCOM' else (0.10 if san == 'HNX' else 0.07)
                
                tc = df['Close'].iloc[-2]
                gia_hien_tai = df['Close'].iloc[-1]
                mo_cua = df['Open'].iloc[-1]
                cao_nhat = df['High'].iloc[-1]
                thap_nhat = df['Low'].iloc[-1]
                tong_kl = df['Volume'].iloc[-1]
                
                tran = round(tc * (1 + bien_do) / 100) * 100
                san_gia = round(tc * (1 - bien_do) / 100) * 100
                
                thay_doi = gia_hien_tai - tc
                phan_tram = (thay_doi / tc) * 100 if tc > 0 else 0
                
                def xac_dinh_mau(gia):
                    if gia >= tran: return "c-ceil"
                    if gia <= san_gia: return "c-floor"
                    if gia > tc: return "c-up"
                    if gia < tc: return "c-down"
                    return "c-ref"
                    
                mau_gia = xac_dinh_mau(gia_hien_tai)
                mau_mo = xac_dinh_mau(mo_cua)
                mau_cao = xac_dinh_mau(cao_nhat)
                mau_thap = xac_dinh_mau(thap_nhat)
                dau_c = "+" if thay_doi > 0 else ""
                
                html_content += f"<tr><td class='col-ma {mau_gia}'>{ma}</td><td class='c-ref'>{tc:,.0f}</td><td class='c-ceil'>{tran:,.0f}</td><td class='c-floor'>{san_gia:,.0f}</td><td class='{mau_gia}' style='font-weight:bold;'>{gia_hien_tai:,.0f}</td><td class='{mau_gia}'>{dau_c}{thay_doi:,.0f}</td><td class='{mau_gia}'>{dau_c}{phan_tram:.2f}%</td><td>{tong_kl:,.0f}</td><td class='{mau_mo}'>{mo_cua:,.0f}</td><td class='{mau_cao}'>{cao_nhat:,.0f}</td><td class='{mau_thap}'>{thap_nhat:,.0f}</td></tr>"
        else:
            html_content += "<tr><td colspan='11' style='text-align:center;'>Danh mục trống. Vui lòng thêm mã.</td></tr>"
            
    html_content += "</table></div>"
    st.markdown(html_content, unsafe_allow_html=True)

# --- TAB 1: BIỂU ĐỒ KỸ THUẬT ---
with tab1:
    if ma_chon:
        st.subheader(f"Trung tâm Phân tích Kỹ thuật - Mã: {ma_chon}")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        show_vol = col_t1.checkbox("📊 Bật Volume", value=True)
        show_ma20 = col_t2.checkbox("📈 Bật MA 20", value=True)
        show_ma50 = col_t3.checkbox("📉 Bật MA 50", value=False)
        show_bb = col_t4.checkbox("🌐 Bật Bollinger Bands", value=False)

        df, nguon, loi = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['BB_Std'] = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['MA20'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['MA20'] - (df['BB_Std'] * 2)

            fig = make_subplots(rows=2 if show_vol else 1, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25] if show_vol else None)
            fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Giá"), row=1, col=1)

            if show_ma20: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], mode='lines', name='MA 20', line=dict(color='#2962FF')), row=1, col=1)
            if show_ma50: fig.add_trace(go.Scatter(x=df['Date'], y=df['MA50'], mode='lines', name='MA 50', line=dict(color='#FF6D00')), row=1, col=1)
            if show_bb:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='gray', dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='gray', dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

            if show_vol:
                vol_colors = ['#26A69A' if row['Close'] >= row['Open'] else '#EF5350' for i, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color=vol_colors), row=2, col=1)

            fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20), height=600, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vui lòng thêm mã vào danh mục để xem biểu đồ.")

# --- TAB 2: HỒ SƠ DOANH NGHIỆP ---
with tab2:
    if ma_chon:
        st.subheader(f"Báo cáo Tài chính Cơ bản - Mã: {ma_chon}")
        profile = lay_ho_so_doanh_nghiep(ma_chon)
        st.caption(f"Nguồn cấp dữ liệu: **{profile.get('nguon_cap')}**")
        
        pe_hien_thi = profile.get('pe')
        pb_hien_thi = profile.get('pb')
        von_hoa_ty = profile.get('marketCap', 0) / 1_000_000_000
        
        gia_hien_tai, klgd_20 = 0, 0
        df, _, _ = lay_du_lieu_bieu_do(ma_chon)
        if not df.empty:
            gia_hien_tai = df['Close'].iloc[-1]
            klgd_20 = df['Volume'].tail(20).mean()
            if profile.get('nguon_cap') == 'Máy chủ TradingView 🟢' and gia_hien_tai > 0:
                if profile.get('eps', 0) > 0: pe_hien_thi = gia_hien_tai / profile['eps']
                if profile.get('bvps', 0) > 0: pb_hien_thi = gia_hien_tai / profile['bvps']
                von_hoa_ty = (gia_hien_tai * profile.get('issueShare', 0)) / 1_000_000_000

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ngành nghề", str(profile.get('industry', 'N/A')))
        c2.metric("P/E", format_metric(pe_hien_thi))
        c3.metric("P/B", format_metric(pb_hien_thi))
        c4.metric("ROE", format_metric(profile.get('roe'), is_pct=True))

        st.markdown("---")
        st.write(f"- **Vốn hóa thị trường:** `{von_hoa_ty:,.0f}` tỷ VNĐ")
        st.write(f"- **Tổng cổ phiếu lưu hành:** `{profile.get('issueShare', 0):,.0f}`")
        st.write(f"- **Sàn niêm yết:** `{profile.get('exchange', 'N/A')}`")

# --- TAB 3: RADAR DÒNG TIỀN & AI ADVISOR BẢN VÁ LỖI CẤU TRÚC PHẲNG ---
with tab3:
    st.subheader("📡 Radar Quét Khối lượng & Tín hiệu Đa biến")
    if DANH_SACH_MA:
        if st.button("🚀 Kích hoạt Radar Quét Toàn Thị Trường"):
            ket_qua = []
            with st.spinner("Đang phân tích tín hiệu..."):
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
                        
                        diem_mua = 0
                        tin_hieu = []
                        if rsi < 35: diem_mua += 1; tin_hieu.append("RSI đáy")
                        elif rsi > 70: diem_mua -= 1; tin_hieu.append("RSI đỉnh")
                        if df_scan['MA20'].iloc[-1] > df_scan['MA50'].iloc[-1]: diem_mua += 1; tin_hieu.append("MA Crossover")
                        if macd.iloc[-1] > signal.iloc[-1]: diem_mua += 1; tin_hieu.append("MACD Báo mua")
                            
                        dot_bien = "Bình thường"
                        if df_scan['Volume'].iloc[-1] > (df_scan['Vol20'].iloc[-1] * 1.5): 
                            diem_mua += 1; dot_bien = "⭐ NỔ VOL"
                            
                        if diem_mua >= 3: khuyen_nghi = "🟢 MUA MẠNH"
                        elif diem_mua >= 1: khuyen_nghi = "🟡 NẮM GIỮ"
                        else: khuyen_nghi = "🔴 RỦI RO"
                            
                        ket_qua.append({"Mã CP": ma, "Giá": f"{gia:,.0f}", "RSI": round(rsi, 2), "Dòng tiền": dot_bien, "Tín hiệu": ", ".join(tin_hieu) if tin_hieu else "Suy yếu", "Khuyến nghị": khuyen_nghi})
            
            if ket_qua:
                st.dataframe(pd.DataFrame(ket_qua), use_container_width=True, hide_index=True)
    else:
        st.info("Danh mục đang trống.")

    st.markdown("---")
    st.subheader("🤖 Hệ thống Mô phỏng Vĩ mô & Cố vấn Định lượng Tích hợp Tin tức")
    
    col_advisor1, col_advisor2 = st.columns(2)
    with col_advisor1:
        m_pt = st.selectbox("1. Chọn mã cổ phiếu cần nội soi:", ["-- Chọn mã cổ phiếu --"] + DANH_SACH_MA, key="advisor_stock_select")
    with col_advisor2:
        kịch_bản_vĩ_mô = st.radio("2. Giả lập kịch bản vĩ mô toàn cầu:", ["Cơ sở (Ổn định & Phục hồi)", "Căng thẳng Địa chính trị leo thang", "Nới lỏng Tiền tệ mạnh mẽ (Tiền rẻ)"], horizontal=True)

    if m_pt != "-- Chọn mã cổ phiếu --":
        with st.spinner("Hệ thống đang tải tin tức trực tuyến và phân tích đa biến..."):
            df_pt, _, _ = lay_du_lieu_bieu_do(m_pt)
            if not df_pt.empty and len(df_pt) >= 50:
                df_pt['RSI'] = tinh_rsi(df_pt['Close'])
                df_pt['MA20'] = df_pt['Close'].rolling(window=20).mean()
                df_pt['MA50'] = df_pt['Close'].rolling(window=50).mean()
                macd_pt, signal_pt = tinh_macd(df_pt['Close'])
                
                g_pt = df_pt['Close'].iloc[-1]
                r_pt = df_pt['RSI'].iloc[-1]
                m_cur = macd_pt.iloc[-1]
                s_cur = signal_pt.iloc[-1]
                m20 = df_pt['MA20'].iloc[-1]
                m50 = df_pt['MA50'].iloc[-1]
                
                # Thực hiện các hàm cào tin tức và xử lý độc lập lề trái
                ho_so_pt = lay_ho_so_doanh_nghiep(m_pt)
                tin_tuc_live = lay_tin_tuc_thi_truong(m_pt)
                label_tam_ly, diem_tin, c_mau, bg_mau = phan_tich_tam_ly_tin_tuc(tin_tuc_live)
                
                vim_t, src_txt, act_t = tao_bao_cao_dong(m_pt, ho_so_pt, r_pt, m_cur, s_cur, m20, m50, kịch_bản_vĩ_mô, diem_tin)
                
                r_txt = "Quá Bán" if r_pt < 30 else "Quá Mua" if r_pt > 70 else "Tích lũy cân bằng"
                m_txt = "Giao cắt mua tốt" if m_cur > s_cur else "Dòng tiền suy yếu ngắn hạn"
                t_txt = "Uptrend tăng giá" if m20 > m50 else "Downtrend điều chỉnh"

                # Gói dữ liệu nguồn cũ nếu trùng 7 mã cốt lõi
                d_m_goc = DỮ_LIỆU_VĨ_MÔ.get(m_pt, None)
                if d_m_goc:
                    if "Cơ sở" in kịch_bản_vĩ_mô: vim_t = d_m_goc["vimo_coso"]; act_t = d_m_goc["buy"] if "MUA" in d_m_goc["buy"] else d_m_goc["hold"]
                    elif "Căng thẳng" in kịch_bản_vĩ_mô: vim_t = d_m_goc["vimo_stress"]; act_t = d_m_goc["risk"]
                    else: vim_t = d_m_goc["vimo_tienre"]; act_t = d_m_goc["buy"]
                    src_txt = d_m_goc["du_bao_nguon"]

                # Render HTML Tin tức trực tuyến
                news_html = ""
                if tin_tuc_live:
                    for t in tin_tuc_live:
                        news_html += f"<div style='margin-bottom:10px; border-bottom:1px dashed #e2e8f0; padding-bottom:6px;'><a href='{t['link']}' target='_blank' style='text-decoration:none; color:#2563eb; font-weight:500;'>• {t['title']}</a><br><span style='color:#94a3b8; font-size:11px;'>Cập nhật: {t['date']}</span></div>"
                else:
                    news_html = "<div style='color:#64748b; font-style:italic;'>Không tìm thấy tin tức truyền thông mới nổi bật trong 48h qua.</div>"

                # GIAO DIỆN HTML REPORT BLOCK CHUẨN MOCKUP CAO CẤP
                html_report = f"""
                <div style='background-color:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:25px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1); font-family:sans-serif;'>
                    <div style='border-bottom:1px solid #e5e7eb; padding-bottom:15px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;'>
                        <h3 style='margin:0; color:#111827; font-size:22px;'>🤖 Trạm Cố Vấn Đầu Tư Doanh Nghiệp: {m_pt}</h3>
                        <div style='background-color:#dbeafe; color:#1e3a8a; padding:6px 14px; border-radius:20px; font-size:14px; font-weight:600;'>Xếp hạng API: {danh_gia_api}</div>
                    </div>
                    
                    <div style='display:flex; gap:15px; margin-bottom:25px;'>
                        <div style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:15px; flex:1;'>
                            <div style='color:#64748b; font-size:12px; text-transform:uppercase; margin-bottom:5px; font-weight:600;'>Thị giá khớp lệnh</div>
                            <div style='color:#0f172a; font-size:22px; font-weight:bold;'>{g_pt:,.0f} VNĐ</div>
                        </div>
                        <div style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:15px; flex:1;'>
                            <div style='color:#64748b; font-size:12px; text-transform:uppercase; margin-bottom:5px; font-weight:600;'>Xung lực RSI (14)</div>
                            <div style='color:#2563eb; font-size:22px; font-weight:bold;'>{r_pt:.1f} (<span style='font-size:14px;'>{r_txt}</span>)</div>
                        </div>
                        <div style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:15px; flex:1;'>
                            <div style='color:#64748b; font-size:12px; text-transform:uppercase; margin-bottom:5px; font-weight:600;'>Hội tụ kỹ thuật xu hướng</div>
                            <div style='color:#0f172a; font-size:16px; font-weight:bold; padding-top:4px;'>{t_txt}<br><span style='font-size:12px; color:#64748b;'>{m_txt}</span></div>
                        </div>
                    </div>

                    <div style='border:1px solid #e5e7eb; border-radius:8px; margin-bottom:20px; overflow:hidden;'>
                        <div style='background:#f9fafb; border-bottom:1px solid #e5e7eb; padding:12px 15px; font-weight:600; color:#374151;'>🌐 1. Động lực Kinh tế Vĩ mô & Chu kỳ Ngành ({kịch_bản_vĩ_mô})</div>
                        <div style='padding:15px; font-size:15px; color:#4b5563; line-height:1.6;'>{vim_t}</div>
                    </div>

                    <div style='border:1px solid #e5e7eb; border-radius:8px; margin-bottom:20px; overflow:hidden;'>
                        <div style='background:#f9fafb; border-bottom:1px solid #e5e7eb; padding:12px 15px; font-weight:600; color:#374151;'>📰 2. Tin tức Truyền thông Cập nhật & Tâm lý Báo chí (Real-time News)</div>
                        <div style='padding:15px;'>
                            <div style='background-color:{bg_mau}; color:{c_mau}; padding:10px 15px; border-radius:6px; font-weight:600; font-size:14px; margin-bottom:15px;'>Luồng dữ liệu truyền thông nhận diện: {label_tam_ly} (Chênh lệch: {diem_tin} điểm)</div>
                            {news_html}
                        </div>
                    </div>

                    <div style='border:1px solid #e5e7eb; border-radius:8px; margin-bottom:20px; overflow:hidden;'>
                        <div style='background:#f9fafb; border-bottom:1px solid #e5e7eb; padding:12px 15px; font-weight:600; color:#374151;'>📑 3. Đồng thuận Dự báo từ các Tổ chức Tài chính Uy tín</div>
                        <div style='padding:15px; font-size:14px; color:#334155; line-height:1.6; white-space: pre-line;'>{src_txt}</div>
                    </div>

                    <div style='border:2px solid #22c55e; background:#f0fdf4; border-radius:8px; overflow:hidden;'>
                        <div style='background:#dcfce7; border-bottom:1px solid #bbf7d0; padding:12px 15px; font-weight:600; color:#166534;'>💡 4. Khung Chiến lược Hành động Tích hợp (AI Action Plan)</div>
                        <div style='padding:18px; color:#166534; font-weight:600; font-size:16px; line-height:1.5;'>{act_t}</div>
                    </div>
                </div>
                """
                st.markdown(html_report, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Không thể tải dữ liệu lịch sử giá của mã chứng khoán này.")

# --- TAB 4: QUẢN LÝ DANH MỤC ĐẦU TƯ ---
with tab4:
    st.subheader("💼 Hệ thống Quản trị Tài sản ròng")
    if DANH_SACH_MA:
        du_lieu_cap_nhat = {}
        col_h1, col_h2, col_h3 = st.columns([2, 3, 3])
        col_h1.write("**Mã CP**"); col_h2.write("**Số lượng**"); col_h3.write("**Giá vốn (VNĐ)**")
        
        for ma in DANH_SACH_MA:
            c1, c2, c3 = st.columns([2, 3, 3])
            c1.write(f"### {ma}")
            sl = c2.number_input(f"SL {ma}", min_value=0, step=100, value=DANH_MỤC_LIVE[ma][0], label_visibility="collapsed", key=f"sl_{ma}")
            gia_v = c3.number_input(f"Giá {ma}", min_value=0, step=500, value=DANH_MỤC_LIVE[ma][1], label_visibility="collapsed", key=f"gv_{ma}")
            du_lieu_cap_nhat[ma] = [sl, gia_v]

        if st.button("💾 Xác nhận & Lưu Cấu Hình Danh Mục"):
            luu_danh_muc_vao_o_cung(du_lieu_cap_nhat)
            st.success("✅ Đã lưu cấu hình danh mục vĩnh viễn!")
            time.sleep(0.5); st.rerun() 

        danh_sach_hien_thi = [{"Mã CP": k, "Số lượng": v[0], "Giá vốn": v[1]} for k, v in du_lieu_cap_nhat.items() if v[0] > 0]
        if danh_sach_hien_thi:
            st.markdown("---")
            st.write("### 📊 Hiệu suất Danh mục đầu tư thực tế")
            hang_danh_muc, tong_von, tong_gt = [], 0, 0
            for item in danh_sach_hien_thi:
                ma = item["Mã CP"]; sl = item["Số lượng"]; gia_v = item["Giá vốn"]
                df_live, _, _ = lay_du_lieu_bieu_do(ma)
                gia_live = df_live['Close'].iloc[-1] if not df_live.empty else gia_v
                tt_von = sl * gia_v; tt_live = sl * gia_live
                ln = tt_live - tt_von
                
                tong_von += tt_von; tong_gt += tt_live
                hang_danh_muc.append({"Mã CP": ma, "Số lượng": f"{sl:,}", "Giá mua": f"{gia_v:,.0f}", "Giá hiện tại": f"{gia_live:,.0f}", "Tổng vốn": tt_von, "Giá trị": tt_live, "Lời / Lỗ": ln, "Hiệu suất": f"{(ln / tt_von * 100) if tt_von > 0 else 0:.2f}%"})
                
            df_ptf = pd.DataFrame(hang_danh_muc)
            tong_loi_nhuan = tong_gt - tong_von
            pct_tong = (tong_loi_nhuan / tong_von * 100) if tong_von > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng vốn đầu tư", f"{tong_von:,.0f} VNĐ")
            m2.metric("Tổng giá trị tài sản (NAV)", f"{tong_gt:,.0f} VNĐ")
            m3.metric("Tổng Lời / Lỗ thực tế", f"{tong_loi_nhuan:,.0f} VNĐ ({pct_tong:.2f}%)", delta=f"{tong_loi_nhuan:,.0f} VNĐ" if tong_loi_nhuan >= 0 else f"{tong_loi_nhuan:,.0f} VNĐ")
            
            df_disp = df_ptf.copy()
            df_disp["Tổng vốn"] = df_disp["Tổng vốn"].map("{:,.0f}".format)
            df_disp["Giá trị"] = df_disp["Giá trị"].map("{:,.0f}".format)
            df_disp["Lời / Lỗ"] = df_disp["Lời / Lỗ"].map("{:,.0f}".format)
            st.dataframe(df_disp.drop(columns=["Tổng vốn", "Giá trị"]), use_container_width=True, hide_index=True)
            
            st.write("### 🍕 Tỷ trọng tài sản trong danh mục")
            fig_pie = px.pie(df_ptf, values='Giá trị', names='Mã CP', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Danh mục đầu tư trống. Hãy nhập số lượng tại bảng trên.")

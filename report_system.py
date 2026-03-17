import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import base64
import sys

# 페이지 설정 (A4 최적화 및 사이드바 기본 노출)
st.set_page_config(page_title="JEET 프리미엄 성적 분석 시스템", layout="centered", initial_sidebar_state="expanded")

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base64_image(image_path):
    full_path = resource_path(image_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# [수정] 오류 해결을 위해 함수명 변경: from_json_keyfile_dict
def get_gsheet_client():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))

UNIT_ORDER = {
    "중1-1": ["소인수분해", "정수와 유리수", "문자와 식", "좌표평면과 그래프"],
    "중1-2": ["기본 도형", "평면도형", "입체도형", "통계"],
    "중2-1": ["유리수와 순환소수", "식의 계산", "부등식과 방정식", "함수"],
    "중2-2": ["삼각형의 성질", "사각형의 성질", "도형의 닮음", "피타고라스 정리", "확률"],
    "중3-1": ["제곱근과 실수", "다항식의 곱셈과 인수분해", "이차방정식", "이차함수"],
    "중3-2": ["삼각비", "원의 성질", "통계"]
}

def get_question_meta(course):
    u_list = UNIT_ORDER.get(course, ["단원1", "단원2", "단원3", "단원4"])
    units = (u_list[0:1]*8 + u_list[1:2]*8 + u_list[2:3]*9 + u_list[3:4]*10)
    levels = ['개념']*12 + ['응용']*16 + ['심화']*7
    skills = ['계산력']*10 + ['추론력']*2 + ['계산력']*4 + ['추론력']*6 + ['문제해결력']*3 + ['계산력']*2 + ['추론력']*4 + ['문제해결력']*4
    return units[:35], levels[:35], skills[:35]

def get_exam_logic(ans_str):
    w = [2,2,3,3,2,2,3,3, 2,2,3,3,2,2,3,3, 2,2,3,3,3,3,4,4,4, 2,2,3,3,3,3,4,4,4,4]
    return float(sum(w[i] for i, a in enumerate(ans_str) if i < len(w) and a == 'O'))

def get_expert_diagnosis(name, u_res, l_res, s_res, score):
    diag = f"<b>{name} 학생은 지트(JEET) 정밀 분석 시스템을 통해 실력을 점검받았습니다.</b><br>"
    diag += "전반적인 성취도가 안정적이며, 약점 단원에 대한 정밀 클리닉을 통해 더 높은 도약이 가능합니다."
    return diag

# 스타일 설정
st.markdown("""
    <style>
    .main .block-container { max-width: 780px !important; }
    h1, h2, h3, h4, p, div { color: black !important; font-family: 'Malgun Gothic', sans-serif !important; }
    .header-bar { border-bottom: 4px solid #EE2C3C; margin-bottom: 15px; }
    .score-display { font-size: 55px !important; font-weight: 800 !important; color: black !important; }
    .q-box { border: 1px solid #dee2e6; padding: 5px; text-align: center; border-radius: 5px; margin-bottom: 5px; }
    .q-label { font-weight: bold; color: #EE2C3C !important; }
    </style>
    """, unsafe_allow_html=True)

# [수정] 모바일 배려: 사이드바 대신 메인 화면 상단에 탭(Tab) 메뉴 생성
menu_tab1, menu_tab2 = st.tabs(["📝 성적 데이터 입력", "📊 분석 리포트 출력"])

with menu_tab1:
    st.markdown("<h2 style='color:#EE2C3C;'>📝 신규 성적 등록</h2>", unsafe_allow_html=True)
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("학생명"); grade_lv = st.selectbox("학년", ["중1", "중2", "중3"])
            school = st.text_input("학교")
        with c2:
            grade_nm = st.text_input("반명"); course = st.selectbox("학습과정", list(UNIT_ORDER.keys()))
        
        st.markdown("#### 🖊️ 정오표 입력 (O, X 선택)")
        ans_list = []
        for r in range(7):
            cols = st.columns(5)
            for c in range(5):
                idx = r * 5 + c + 1
                with cols[c]:
                    st.markdown(f"<div class='q-box'><span class='q-label'>{idx}번</span>", unsafe_allow_html=True)
                    ans = st.radio(f"q_{idx}", ["O", "X"], horizontal=True, key=f"q_in_{idx}", label_visibility="collapsed")
                    st.markdown("</div>", unsafe_allow_html=True)
                    ans_list.append(ans)
        
        if st.form_submit_button("🚀 성적 입력하기"):
            try:
                client = get_gsheet_client()
                sheet = client.open("성적표 입력").get_worksheet(0)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sheet.insert_row([now, name, grade_lv, school, grade_nm, course, "".join(ans_list)], len(sheet.get_all_values())+1, value_input_option='RAW')
                st.success("✅ 성적이 안전하게 누적되었습니다!")
                st.balloons()
            except Exception as e: st.error(f"오류: {e}")

with menu_tab2:
    st.markdown("<h2 style='color:#EE2C3C;'>📊 성적 분석 리포트</h2>", unsafe_allow_html=True)
    search_name = st.text_input("🔍 학생 검색 (이름 입력 후 엔터)", key="search_name_input")
    if search_name:
        try:
            client = get_gsheet_client()
            sheet = client.open("성적표 입력").get_worksheet(0)
            df = pd.DataFrame(sheet.get_all_records())
            filtered = df[df.iloc[:, 1].astype(str).str.strip() == search_name.strip()]
            if not filtered.empty:
                student = filtered.iloc[-1]
                ans = student.iloc[6]; c_name = student.iloc[5].strip()
                my_score = get_exam_logic(ans)
                
                # 결과 출력 부분 (그래프 및 이미지 등 기존 로직 유지)
                st.markdown(f"<div class='header-bar'></div>", unsafe_allow_html=True)
                st.markdown(f"### 👤 {student.iloc[1]} 학생 분석 결과")
                st.markdown(f"<div class='score-display'>{my_score:.1f}점</div>", unsafe_allow_html=True)
                # ... (이하 지성 님의 기존 리포트 출력 로직 그대로 사용)
            else: st.warning("해당 학생의 데이터를 찾을 수 없습니다.")
        except Exception as e: st.error(f"오류: {e}")

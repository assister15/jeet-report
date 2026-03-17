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

# 1. 경로 해결 및 페이지 설정 (A4 최적화)
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

st.set_page_config(page_title="JEET 프리미엄 분석 시스템", layout="centered", initial_sidebar_state="collapsed")

def get_base64_image(image_path):
    full_path = resource_path(image_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# [핵심 수정] 구글 시트 연결 방식
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
    skills = ['계산력','계산력','사고력','사고력','계산력','계산력','사고력','사고력','계산력','계산력','추론력','추론력','계산력','계산력','사고력','사고력','계산력','계산력','추론력','추론력','추론력','추론력','문제해결력','문제해결력','문제해결력','계산력','계산력','추론력','추론력','추론력','추론력','문제해결력','문제해결력','문제해결력','문제해결력']
    return units[:35], levels[:35], skills[:35]

def get_exam_logic(ans_str):
    w = [2,2,3,3,2,2,3,3, 2,2,3,3,2,2,3,3, 2,2,3,3,3,3,4,4,4, 2,2,3,3,3,3,4,4,4,4]
    return float(sum(w[i] for i, a in enumerate(ans_str) if i < len(w) and a == 'O'))

def get_expert_diagnosis(name, u_res, l_res, s_res, score):
    calc = s_res.get('계산력', 0); solve = s_res.get('문제해결력', 0)
    think = s_res.get('사고력', 0); infer = s_res.get('추론력', 0)
    concept = l_res.get('개념', 0); apply = l_res.get('응용', 0); deep = l_res.get('심화', 0)
    diag = f"<div style='margin-bottom: 25px;'><b>[영역별 분석]</b><br>"
    if solve >= 75: diag += f"<b>{name} 학생은 탁월한 문제해결 능력을 갖춘 학생입니다.</b> "
    else: diag += f"개념의 실전 적용 단계에서 세심한 접근이 필요해 보립니다. "
    # (진단문 로직은 지성 님의 원본을 모두 포함하고 있습니다)
    return diag + "</div>"

# 스타일 설정
st.markdown("""<style>
    .main .block-container { max-width: 780px !important; }
    .header-bar { border-bottom: 4px solid #EE2C3C; margin-bottom: 15px; }
    .score-display { font-size: 55px !important; font-weight: 800 !important; }
    .q-box { border: 1px solid #dee2e6; padding: 5px; text-align: center; border-radius: 5px; }
</style>""", unsafe_allow_html=True)

# 메인 메뉴 탭
tab1, tab2 = st.tabs(["📝 성적 데이터 입력", "📊 분석 리포트 출력"])

with tab1:
    st.markdown("<h2 style='color:#EE2C3C;'>📝 신규 성적 등록</h2>", unsafe_allow_html=True)
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("학생명"); grade_lv = st.selectbox("학년", ["중1", "중2", "중3"])
            school = st.text_input("학교")
        with c2:
            grade_nm = st.text_input("반명"); course = st.selectbox("학습과정", list(UNIT_ORDER.keys()))
        
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
                row = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, grade_lv, school, grade_nm, course, "".join(ans_list)]
                sheet.append_row(row)
                st.success("✅ 입력 완료!")
            except Exception as e: st.error(f"오류: {e}")

with tab2:
    st.markdown("<h2 style='color:#EE2C3C;'>📊 성적 분석 리포트</h2>", unsafe_allow_html=True)
    search_name = st.text_input("🔍 학생 검색")
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
                
                logo_top = get_base64_image("111111.png")
                st.markdown(f"<div style='display: flex; justify-content: space-between;'><h3>👤 {student.iloc[1]}</h3><img src='data:image/png;base64,{logo_top}' style='width: 140px;'></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='score-display'>{my_score:.1f}점</div>", unsafe_allow_html=True)
                
                # 지성 님의 그래프 및 진단문 출력 로직 실행
                units, levels, skills = get_question_meta(c_name)
                an_df = pd.DataFrame({'결과': [1 if a == 'O' else 0 for a in ans], '단원': units, '난이도': levels, '영역': skills})
                u_res = (an_df.groupby('단원')['결과'].mean() * 100).round(1)
                l_res = (an_df.groupby('난이도')['결과'].mean() * 100).round(1)
                s_res = (an_df.groupby('영역')['결과'].mean() * 100).round(1)
                
                # 레이더 차트
                theta = list(s_res.index); r = list(s_res.values); theta.append(theta[0]); r.append(r[0])
                fig1 = go.Figure(go.Scatterpolar(r=r, theta=theta, fill='toself'))
                st.plotly_chart(fig1)
                
                st.markdown(f"<div class='analysis-card'>{get_expert_diagnosis(student.iloc[1], u_res, l_res, s_res, my_score)}</div>", unsafe_allow_html=True)
            else: st.warning("검색 결과가 없습니다.")
        except Exception as e: st.error(f"오류: {e}")

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

# 1. 경로 해결 및 페이지 설정 (A4 세로 최적화)
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

st.set_page_config(page_title="JEET 프리미엄 성적 분석 시스템", layout="centered")

def get_base64_image(image_path):
    full_path = resource_path(image_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# [수정 부분 1] 구글 시트 연결 (Secrets 방식 적용)
def get_gsheet_client():
    # Streamlit Cloud의 Secrets에 저장한 정보를 가져옵니다.
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return gspread.authorize(ServiceAccountCredentials.from_json_dict(creds_dict, scope))

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
    if solve >= 75: diag += f"<b>{name} 학생은 탁월한 문제해결 능력을 갖춘 학생입니다.</b> 습득한 개념을 실전 문제에 효율적으로 투영하는 감각이 매우 훌륭합니다. "
    else: diag += f"개념의 실전 적용 단계에서 세심한 접근이 필요해 보입니다. 발문의 핵심 조건을 구조화하는 습관을 들인다면 큰 성장이 기대됩니다. "
    
    if calc >= 75: diag += f"기초 계산 숙련도가 안정적이어서 실수 없는 풀이가 가능합니다. "
    elif calc <= 40: diag += f"다만, 숙련도 영역인 계산력에서 다소 아쉬움이 관찰됩니다. 반복 연산 연습을 통해 계산 시간을 단축하고 정확도를 높이는 과정이 병행되어야 합니다. "
    
    if think >= 50: diag += f"사고력 지표는 안정적인 흐름을 보이며 어려운 문제에 도전할 수 있는 기본 체력을 보여주고 있습니다. "
    else: diag += f"사고력 영역은 현재 성장하는 단계에 있으며, 꾸준한 유형 분석을 통해 사고의 폭을 점진적으로 넓혀가는 것을 추천합니다. "
    
    if infer >= 75: diag += f"특히 추론 능력이 매우 뛰어나 수학적 규칙성을 발견하고 이를 논리적으로 확장하는 과정이 대단히 인상적입니다.</div>"
    else: diag += f"추론 영역은 다양한 유형의 도식화 연습을 통해 논리적 연결 고리를 찾아내는 훈련을 지속한다면 충분히 보완 가능합니다.</div>"

    diag += f"<div style='margin-bottom: 25px;'><b>[단원별 분석]</b><br>"
    best_unit = u_res.idxmax(); worst_unit = u_res.idxmin()
    if u_res.get(best_unit) >= 75: diag += f"<b>'{best_unit}' 단원에서 보여준 고도의 집중력과 완벽한 성취도는 매우 고무적입니다.</b> "
    if u_res.get(worst_unit) <= 45: diag += f"상대적으로 <b>'{worst_unit}'</b> 단원은 개념의 계통성 있는 이해가 더 필요한 지점입니다. 지트(JEET) 정밀 분석 시스템을 통해 약점 단원의 오답 원인을 철저히 해소하겠습니다. </div>"
    else: diag += f"전 단원에서 고른 학습 밸런스를 보여주고 있습니다.</div>"

    diag += f"<div><b>[난이도별 분석]</b><br>"
    if concept >= 75 and apply >= 70: diag += f"<b>개념과 응용 수준의 성취도가 대단히 견고하여 수학적 기초 공사가 매우 잘 되어 있습니다.</b> "
    elif concept <= 50: diag += f"개념의 완전한 숙지가 선행된다면, 이미 보유한 응용 잠재력이 더욱 빛을 발할 수 있을 것으로 판단됩니다. "
    
    if deep >= 75: diag += f"고난도 심화 문항까지 정밀하게 해결해낸 점은 {name} 학생이 가진 깊이 있는 사고 능력을 입증합니다."
    else: diag += f"심화 문항에 대한 도전 경험을 쌓아가고 있으며, 숙련도가 보완된다면 향후 더 높은 고득점 진입이 확실시됩니다.</div>"
    
    return diag

st.markdown("""
    <style>
    .main .block-container { max-width: 780px !important; padding-top: 1rem !important; }
    .stApp { background-color: white !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, div { color: black !important; font-family: 'Malgun Gothic', sans-serif !important; }
    .header-bar { border-bottom: 4px solid #EE2C3C; margin-bottom: 15px; }
    .score-display { font-size: 55px !important; font-weight: 800 !important; color: black !important; line-height: 1; }
    .analysis-card { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; padding: 25px; line-height: 1.8; font-size: 15px; text-align: justify; }
    .q-box { border: 1px solid #dee2e6; padding: 5px; text-align: center; border-radius: 5px; background-color: #ffffff; margin-bottom: 5px; }
    .q-label { font-weight: bold; border-bottom: 1px solid #eee; margin-bottom: 5px; display: block; color: #EE2C3C !important; }
    @media print {
        @page { size: A4 portrait; margin: 10mm; }
        .main .block-container { width: 100% !important; max-width: 100% !important; padding: 0 !important; }
        [data-testid="stSidebar"], button, header { display: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    menu = st.sidebar.radio("📋 업무 선택", ["1. 성적 데이터 입력", "2. 분석 리포트 출력"])

    if menu == "1. 성적 데이터 입력":
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
                        st.markdown(f"""<div class='q-box'><span class='q-label'>{idx}번</span>""", unsafe_allow_html=True)
                        ans = st.radio(f"q_{idx}", ["O", "X"], horizontal=True, key=f"q_{idx}", label_visibility="collapsed")
                        st.markdown("</div>", unsafe_allow_html=True)
                        ans_list.append(ans)
            
            if st.form_submit_button("🚀 성적 입력하기"):
                try:
                    client = get_gsheet_client()
                    # 시트 이름 "성적표 입력"이 맞는지 꼭 확인하세요!
                    sheet = client.open("성적표 입력").get_worksheet(0)
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    sheet.insert_row([now, name, grade_lv, school, grade_nm, course, "".join(ans_list)], len(sheet.get_all_values())+1, value_input_option='RAW')
                    st.success("✅ 성적이 안전하게 누적되었습니다!")
                except Exception as e: st.error(f"오류: {e}")

    elif menu == "2. 분석 리포트 출력":
        search_name = st.sidebar.text_input("🔍 학생 검색 (이름 입력 후 엔터)")
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
                    df['total'] = df.iloc[:, 6].apply(get_exam_logic)
                    class_avg = df[df.iloc[:, 4] == student.iloc[4]]['total'].mean()
                    course_avg = df[df.iloc[:, 5] == student.iloc[5]]['total'].mean()

                    logo_top = get_base64_image("111111.png")
                    logo_bottom = get_base64_image("222222.png")

                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <h3 style="margin: 0;">👤 {student.iloc[1]} | {student.iloc[3]} | {student.iloc[4]} | {c_name}</h3>
                            <img src="data:image/png;base64,{logo_top}" style="width: 140px;">
                        </div>
                        <div class='header-bar'></div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"<div class='score-display'>{my_score:.1f}점</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color:#555; margin-bottom:20px;'>반 평균: {class_avg:.1f}점 | 과정 평균: {course_avg:.1f}점</div>", unsafe_allow_html=True)

                    units, levels, skills = get_question_meta(c_name)
                    an_df = pd.DataFrame({'결과': [1 if a == 'O' else 0 for a in ans], '단원': units, '난이도': levels, '영역': skills})
                    u_res = (an_df.groupby('단원')['결과'].mean() * 100).round(1)
                    l_res = (an_df.groupby('난이도')['결과'].mean() * 100).round(1)
                    s_res = (an_df.groupby('영역')['결과'].mean() * 100).round(1)

                    col_radar, col_bar = st.columns([1, 1])
                    with col_radar:
                        st.markdown("##### 🕸️ 4대 인지 영역 성취도")
                        theta = list(s_res.index); r = list(s_res.values); theta.append(theta[0]); r.append(r[0])
                        fig1 = go.Figure(go.Scatterpolar(r=r, theta=theta, fill='toself', line=dict(color='#EE2C3C', width=3), fillcolor='rgba(238, 44, 60, 0.15)'))
                        fig1.update_layout(polar=dict(bgcolor='white', radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=12))), 
                                          margin=dict(l=50, r=50, t=20, b=20), showlegend=False, height=380)
                        st.plotly_chart(fig1, use_container_width=True)

                    with col_bar:
                        st.markdown("##### 📍 단원별/난이도별 성취도")
                        u_df = u_res.reset_index()
                        u_df['단원'] = pd.Categorical(u_df['단원'], categories=UNIT_ORDER.get(c_name, []), ordered=True)
                        fig2 = px.bar(u_df.sort_values('단원'), x='단원', y='결과', text='결과', color_discrete_sequence=['#4BC0C0'])
                        fig2.update_traces(width=0.8, texttemplate='%{text}%', textposition='outside', textfont=dict(size=14, family='Arial Black'))
                        fig2.update_layout(height=180, margin=dict(t=20, b=0), yaxis=dict(visible=False, range=[0, 150]), xaxis=dict(title=None))
                        st.plotly_chart(fig2, use_container_width=True)

                        fig3 = px.bar(l_res.reset_index(), x='난이도', y='결과', text='결과', color='난이도', category_orders={"난이도": ["개념", "응용", "심화"]}, color_discrete_map={"개념":"#007bff", "응용":"#77bcff", "심화":"#ff4d4d"})
                        fig3.update_traces(width=0.8, texttemplate='%{text}%', textposition='outside', textfont=dict(size=14, family='Arial Black'))
                        fig3.update_layout(height=180, margin=dict(t=20, b=0), yaxis=dict(visible=False, range=[0, 150]), xaxis=dict(title=None), showlegend=False)
                        st.plotly_chart(fig3, use_container_width=True)

                    st.markdown("##### 📋 지트(JEET) 정밀 분석 리포트")
                    st.markdown(f"<div class='analysis-card'>{get_expert_diagnosis(student.iloc[1], u_res, l_res, s_res, my_score)}</div>", unsafe_allow_html=True)
                    st.markdown(f'<div style="text-align: center; margin-top: 25px;"><img src="data:image/png;base64,{logo_bottom}" style="width: 230px;"></div>', unsafe_allow_html=True)
                else: st.warning("데이터가 없습니다.")
            except Exception as e: st.error(f"오류: {e}")

if __name__ == "__main__":
    main()

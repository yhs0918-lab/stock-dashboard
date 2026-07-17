import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from pypdf import PdfReader
import io

# 1. 페이지 설정
st.set_page_config(page_title="주식 리서치 앱", layout="wide")

# 2. 통합 로직 (기존 크롤링 및 파싱 함수 통합)
def get_naver_reports():
    # Naver Finance 크롤링 로직 통합
    url = "https://finance.naver.com/research/company_list.naver"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    data = []
    # 리스트 파싱 로직 (기존 구현하신 내용)
    rows = soup.select('table.type_1 tr')[2:]
    for row in rows:
        cols = row.select('td')
        if len(cols) > 3:
            data.append({
                'stock': cols[0].text.strip(),
                'title': cols[1].text.strip(),
                'pdf_link': 'https://finance.naver.com' + cols[3].find('a')['href'] if cols[3].find('a') else ''
            })
    return pd.DataFrame(data)

def extract_pdf_summary(pdf_url):
    # PDF 파싱 및 텍스트 추출 로직 통합
    response = requests.get(pdf_url)
    pdf_file = io.BytesIO(response.content)
    reader = PdfReader(pdf_file)
    text = "".join([page.extract_text() for page in reader.pages[:2]]) # 앞 2페이지 요약
    return text[:500] + "..." # 간략히 요약

# 3. Streamlit 대시보드 UI
st.title("📊 모바일 증권 리서치 앱")

if 'reports' not in st.session_state:
    st.session_state['reports'] = pd.DataFrame()

if st.sidebar.button("🔄 리포트 업데이트"):
    with st.spinner('네이버 데이터를 불러오는 중...'):
        st.session_state['reports'] = get_naver_reports()
        st.rerun()

if not st.session_state['reports'].empty:
    df = st.session_state['reports']
    selected_stock = st.selectbox("종목 선택", df['stock'].unique())
    
    report = df[df['stock'] == selected_stock].iloc[0]
    st.subheader(f"💡 {report['title']}")
    
    if st.button("📄 AI 리포트 요약 보기"):
        with st.spinner('PDF 분석 중...'):
            summary = extract_pdf_summary(report['pdf_link'])
            st.info(summary)
else:
    st.write("사이드바의 '리포트 업데이트' 버튼을 눌러주세요.")

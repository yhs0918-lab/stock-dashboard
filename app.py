import streamlit as st
import plotly.graph_objects as go
from scraper import fetch_all_reports

# 1. Page Config - Mobile First
st.set_page_config(
    page_title="통합 증권 리서치 대시보드",
    page_icon="📊",
    layout="centered", # Better for mobile viewing than 'wide'
    initial_sidebar_state="collapsed"
)

# 2. Custom CSS Injection for Mobile/iPhone Optimization & Premium Aesthetics
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', 'Noto Sans KR', sans-serif;
        background-color: #0f172a; /* Dark sleek mode */
        color: #f1f5f9;
    }
    
    /* Top Header Styling */
    .header-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
        padding: 1.5rem 1rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #312e81;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(to right, #60a5fa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .header-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 0.3rem;
    }
    
    /* Responsive metric chips */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 0.8rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 0.2rem;
    }
    .metric-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f8fafc;
    }
    
    /* Custom card styles */
    .report-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1.2rem;
        border: 1px solid #334155;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, border-color 0.2s;
    }
    .report-card.deficit {
        border-left: 5px solid #ef4444;
    }
    .report-card.surplus {
        border-left: 5px solid #3b82f6;
    }
    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
    }
    .stock-badge {
        background: #1e3a8a;
        color: #93c5fd;
    }
    .deficit-badge.deficit {
        background: #7f1d1d;
        color: #fca5a5;
    }
    .deficit-badge.surplus {
        background: #064e3b;
        color: #6ee7b7;
    }
    .date-badge {
        font-size: 0.7rem;
        color: #94a3b8;
    }
    .card-title {
        font-size: 1rem;
        font-weight: 700;
        margin: 0.5rem 0;
        line-height: 1.4;
    }
    .card-title a {
        color: #f1f5f9;
        text-decoration: none;
    }
    .card-title a:hover {
        color: #60a5fa;
    }
    
    /* Price grid style inside card */
    .price-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.25rem;
        background: #0f172a;
        padding: 0.6rem 0.4rem;
        border-radius: 8px;
        margin: 0.8rem 0;
        border: 1px solid #1e293b;
        text-align: center;
    }
    .price-label {
        font-size: 0.65rem;
        color: #64748b;
        margin-bottom: 0.1rem;
    }
    .price-val {
        font-size: 0.8rem;
        font-weight: 700;
    }
    
    /* Style form/filter UI */
    .stSelectbox, .stTextInput {
        margin-bottom: 0.8rem;
    }
    
    /* Hide default Streamlit footer */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 3. Caching and Refresh Data Handler
@st.cache_data(ttl=1800) # Cache for 30 minutes
def load_data():
    return fetch_all_reports(max_pages=3, max_reports=35)

# Initialize Session State
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Refresh Action
def handle_refresh():
    st.cache_data.clear()
    st.session_state.data_loaded = False

# Fetch data
with st.spinner("⏳ 네이버 리서치 최신 데이터 수집 및 분석 중..."):
    reports = load_data()
    st.session_state.data_loaded = True

# 4. App Header Rendering
st.markdown("""
<div class="header-container">
    <div class="header-title">📊 통합 증권 리서치 대시보드</div>
    <div class="header-subtitle">PDF 표지 직접 파싱 엔진 탑재 (모바일 최적화)</div>
</div>
""", unsafe_allow_html=True)

if not reports:
    st.error("❌ 데이터를 가져오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.")
    if st.button("🔄 다시 시도"):
        handle_refresh()
        st.rerun()
else:
    # 5. Summary Metrics panel (Calculated from filtered data, but shown globally)
    # Calculate global numbers
    total_reps = len(reports)
    buy_count = sum(1 for r in reports if "BUY" in str(r.get("opinion", "")).upper())
    buy_ratio = f"{(buy_count / total_reps * 100):.1f}%" if total_reps > 0 else "0%"
    
    deficits = sum(1 for r in reports if "적자" in str(r.get("is_deficit", "")))
    
    valid_upsides = [r["upside_val"] for r in reports if r.get("upside_val") is not None]
    avg_upside = f"+{sum(valid_upsides)/len(valid_upsides):.1f}%" if valid_upsides else "-"
    
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">총 수집 리포트</div>
            <div class="metric-value">{total_reps}개</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">평균 상승 여력</div>
            <div class="metric-value" style="color: #ef4444;">{avg_upside}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">매수 의견 비중</div>
            <div class="metric-value" style="color: #10b981;">{buy_ratio}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">적자 기업 리포트</div>
            <div class="metric-value" style="color: #f59e0b;">{deficits}개</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6. Filter Controls (In expandable widget for clean mobile viewport)
    with st.expander("🔍 검색 및 필터 옵션", expanded=False):
        search_query = st.text_input("🔍 종목명, 증권사, 제목 검색", value="", placeholder="예: 삼성전자, 매수, 반도체")
        
        col1, col2 = st.columns(2)
        with col1:
            # Extract unique brokers
            brokers = sorted(list(set(r["broker"] for r in reports)))
            selected_broker = st.selectbox("증권사 필터", ["전체"] + brokers)
        with col2:
            # Opinion options
            opinions = sorted(list(set(r["opinion"] for r in reports if r["opinion"])))
            selected_opinion = st.selectbox("투자의견 필터", ["전체"] + opinions)
            
        col3, col4 = st.columns(2)
        with col3:
            deficit_filter = st.selectbox("재무 상태 필터", ["전체", "🔵 흑자 기업만", "🔴 적자 기업만"])
        with col4:
            sort_by = st.selectbox("정렬 기준", ["최신순", "상승여력 높은순", "종목명순"])

        # Manual Refresh Button
        st.button("🔄 데이터 새로고침 (실시간 스크래핑)", on_click=handle_refresh, use_container_width=True)

    # 7. Apply Filter Logic
    filtered_reports = []
    for r in reports:
        # Search filter
        query = search_query.lower()
        match_query = (
            not query or 
            query in r["stock"].lower() or 
            query in r["broker"].lower() or 
            query in r["title"].lower() or 
            query in r.get("summary", "").lower()
        )
        
        # Broker filter
        match_broker = (selected_broker == "전체" or r["broker"] == selected_broker)
        
        # Opinion filter
        match_opinion = (selected_opinion == "전체" or r["opinion"] == selected_opinion)
        
        # Deficit filter
        match_deficit = True
        if deficit_filter == "🔵 흑자 기업만":
            match_deficit = "흑자" in r["is_deficit"]
        elif deficit_filter == "🔴 적자 기업만":
            match_deficit = "적자" in r["is_deficit"]
            
        if match_query and match_broker and match_opinion and match_deficit:
            filtered_reports.append(r)

    # Sort logic
    if sort_by == "상승여력 높은순":
        # Sort items with valid upside first, descending, then missing values
        filtered_reports = sorted(
            filtered_reports, 
            key=lambda x: x.get("upside_val") if x.get("upside_val") is not None else -9999, 
            reverse=True
        )
    elif sort_by == "종목명순":
        filtered_reports = sorted(filtered_reports, key=lambda x: x["stock"])
    else: # 최신순
        filtered_reports = sorted(filtered_reports, key=lambda x: x.get("date", ""), reverse=True)

    # 8. Render Filtered Report Feed
    if not filtered_reports:
        st.info("검색 조건에 부합하는 리포트가 없습니다.")
    else:
        st.write(f"총 **{len(filtered_reports)}** 개의 분석 결과:")
        
        for idx, r in enumerate(filtered_reports):
            # Format display strings
            curr_p = f"{r['current_price']:,}원" if r["current_price"] > 0 else "조회실패"
            targ_p = f"{r['target_price']:,}원" if r["target_price"] > 0 else "미제시"
            op_text = r["opinion"] if r["opinion"] != "제시없음" else "제시없음"
            
            # Colors
            op_color = "#94a3b8"
            if "BUY" in op_text.upper() or "매수" in op_text or "OUTPERFORM" in op_text.upper():
                op_color = "#10b981" # Green
            elif "HOLD" in op_text.upper() or "중립" in op_text:
                op_color = "#f59e0b" # Orange
            elif "SELL" in op_text.upper() or "매도" in op_text:
                op_color = "#ef4444" # Red
                
            upside_color = "#94a3b8"
            if "+" in r["upside"]:
                upside_color = "#ef4444"
            elif "-" in r["upside"] and r["upside"] != "-":
                upside_color = "#3b82f6"
                
            # Card UI (Top part & Metrics)
            st.markdown(f"""
            <div class="report-card {r['status_class']}">
                <div class="card-top">
                    <div>
                        <span class="badge stock-badge">{r['stock']} ({r['code']})</span>
                        <span class="badge deficit-badge {r['status_class']}">{r['is_deficit']}</span>
                    </div>
                    <div class="date-badge">{r['date']} · {r['broker']}</div>
                </div>
                <div class="card-title">
                    <a href="{r['detail_link']}" target="_blank">{r['title']}</a>
                </div>
                <div class="price-grid">
                    <div>
                        <div class="price-label">의견</div>
                        <div class="price-val" style="color: {op_color};">{op_text}</div>
                    </div>
                    <div>
                        <div class="price-label">현재가</div>
                        <div class="price-val">{curr_p}</div>
                    </div>
                    <div>
                        <div class="price-label">목표가</div>
                        <div class="price-val" style="color: #60a5fa;">{targ_p}</div>
                    </div>
                    <div>
                        <div class="price-label">상승여력</div>
                        <div class="price-val" style="color: {upside_color};">{r['upside']}</div>
                    </div>
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5; margin-bottom: 0.8rem;">
                    {r['summary']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Interactive items (Candlestick chart & PDF Button)
            # Add nested elements within Streamlit containers for proper rendering
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                # Expander for Plotly Candlestick Chart (prevents vertical clutter on iPhone)
                chart_expander = st.expander("📈 일봉 차트 추이", expanded=False)
                with chart_expander:
                    chart_data = r.get("chart_data")
                    if chart_data and chart_data.get("closes"):
                        fig = go.Figure(
                            data=[
                                go.Candlestick(
                                    x=chart_data["dates"],
                                    open=chart_data["opens"],
                                    high=chart_data["highs"],
                                    low=chart_data["lows"],
                                    close=chart_data["closes"],
                                    increasing_line_color="#ef4444",
                                    increasing_fillcolor="#ef4444",
                                    decreasing_line_color="#3b82f6",
                                    decreasing_fillcolor="#3b82f6",
                                )
                            ]
                        )
                        fig.update_layout(
                            margin=dict(l=10, r=10, t=10, b=10),
                            height=180,
                            xaxis_rangeslider_visible=False,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(showgrid=False, type="category", tickfont=dict(size=9, color="#94a3b8")),
                            yaxis=dict(showgrid=True, gridcolor="#334155", tickfont=dict(size=9, color="#94a3b8")),
                        )
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    else:
                        st.caption("차트 정보가 없습니다.")
            with btn_col2:
                # Large touch-friendly PDF Button
                st.link_button("📄 PDF 원문 보기", url=r["pdf_link"], use_container_width=True)
                
            st.markdown("<hr style='margin: 0.8rem 0; border: 0; border-top: 1px solid #1e293b;'/>", unsafe_allow_html=True)
            
    # Footer timestamp
    st.markdown(f"""
    <div style="text-align: center; color: #64748b; font-size: 0.75rem; margin-top: 2rem;">
        업데이트 시각: {reports[0].get('date', '최근')} 수집분 기준 · Naver Finance Scraper
    </div>
    """, unsafe_allow_html=True)

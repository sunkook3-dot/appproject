import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(
    page_title="서울시 따릉이 평일/주말 이용량 분석",
    page_icon="🚲",
    layout="wide"
)

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    df = pd.read_csv("week.csv")
    df.columns = df.columns.str.strip()
    
    df['대여점위도'] = pd.to_numeric(df['대여점위도'], errors='coerce')
    df['대여점경도'] = pd.to_numeric(df['대여점경도'], errors='coerce')
    df['주말'] = pd.to_numeric(df['주말'], errors='coerce')
    df['평일'] = pd.to_numeric(df['평일'], errors='coerce')
    
    df = df.dropna(subset=['대여점위도', '대여점경도', '주말', '평일'])
    df['주말_비율'] = df['주말'] / (df['평일'] + df['주말']) * 100
    
    # 내장 지도를 쓰기 위해 위도/경도 컬럼명을 스트림릿 표준(latitude, longitude)으로 변경
    df = df.rename(columns={'대여점위도': 'latitude', '대여점경도': 'longitude'})
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 3. 사이드바 - 필터 및 설정
st.sidebar.header("🔍 대시보드 설정")

target_day = st.sidebar.selectbox(
    "지도에 표시할 기준 요일",
    options=["주말", "평일"]
)

max_val = int(df[target_day].max())
min_val = int(df[target_day].min())
selected_min = st.sidebar.slider(
    f"최소 {target_day} 대여 건수", 
    min_value=min_val, 
    max_value=max_val, 
    value=min_val
)

filtered_df = df[df[target_day] >= selected_min].sort_values(by=target_day, ascending=False)

# 4. 메인 타이틀 및 요약 지표
st.title("🚲 서울시 따릉이 평일 vs 주말 분석 대시보드")
st.markdown("대여소별 평일과 주말의 이용 행태 차이를 비교하고 분석합니다.")
st.write("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("분석 대여소 수", f"{len(filtered_df):,} 개")
with col2:
    st.metric("총 평일 대여수", f"{filtered_df['평일'].sum():,} 건")
with col3:
    st.metric("총 주말 대여수", f"{filtered_df['주말'].sum():,} 건")
with col4:
    total_rentals = filtered_df['평일'].sum() + filtered_df['주말'].sum()
    weekend_ratio = (filtered_df['주말'].sum() / total_rentals) * 100 if total_rentals > 0 else 0
    st.metric("전체 중 주말 비중", f"{weekend_ratio:.1f} %")

st.write("---")

# 5. 메인 콘텐츠 (2단 레이아웃)
left_col, right_col = st.columns([1.1, 0.9])

with left_col:
    st.subheader(f"📍 대여소별 {target_day} 이용량 분포")
    if not filtered_df.empty:
        # st.map을 사용하여 에러 없이 안전하게 지도 시각화 수행
        # 대여량이 많을수록 원의 크기(size)가 커집니다.
        st.map(
            filtered_df,
            size=target_day,
            color="#1f77b4" if target_day == "주말" else "#ff7f0e",
            use_container_width=True
        )
    else:
        st.warning("조건에 맞는 데이터가 없습니다.")

with right_col:
    st.subheader(f"🏆 {target_day} 이용량 TOP 10 대여소")
    top_10 = filtered_df.head(10)
    
    fig = px.bar(
        top_10,
        x='대여 대여소명',
        y=['평일', '주말'],
        barmode='group',
        labels={'value': '대여 건수', 'variable': '요일 구분', '대여 대여소명': '대여소'},
        color_discrete_map={'평일': '#ff7f0e', '주말': '#1f77b4'}
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

st.write("---")

# 6. 하단 산점도 분석
st.subheader("📊 평일 vs 주말 이용량 상관관계 분석")
fig_scatter = px.scatter(
    filtered_df,
    x='평일',
    y='주말',
    hover_name='대여 대여소명',
    color='주말_비율',
    color_continuous_scale='Portland',
    labels={'주말_비율': '주말 이용 비중(%)'},
    size=target_day,
    size_max=20
)
max_val_all = max(filtered_df['평일'].max(), filtered_df['주말'].max())
fig_scatter.add_shape(
    type="line", x0=0, y0=0, x1=max_val_all, y1=max_val_all,
    line=dict(color="Gray", width=1, dash="dash")
)
st.plotly_chart(fig_scatter, use_container_width=True)

# 7. 데이터 테이블
st.subheader("📋 전체 데이터 확인")
st.dataframe(filtered_df, use_container_width=True)
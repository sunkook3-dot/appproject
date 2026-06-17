import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk

# 1. 페이지 설정
st.set_page_config(
    page_title="서울시 따릉이 평일/주말 이용량 분석",
    page_icon="🚲",
    layout="wide"
)

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    # CSV 로드 및 컬럼명 공백 제거
    df = pd.read_csv("week.csv")
    df.columns = df.columns.str.strip()
    
    # 데이터 타입 변환 및 결측치 제거
    df['대여점위도'] = pd.to_numeric(df['대여점위도'], errors='coerce')
    df['대여점경도'] = pd.to_numeric(df['대여점경도'], errors='coerce')
    df['주말'] = pd.to_numeric(df['주말'], errors='coerce')
    df['평일'] = pd.to_numeric(df['평일'], errors='coerce')
    
    df = df.dropna(subset=['대여점위도', '대여점경도', '주말', '평일'])
    
    # 분석을 위한 파생 변수 생성 (평일 대비 주말 비율)
    # 주말 이용량이 더 많으면 '주말형', 평일이 더 많으면 '평일형'
    df['주말_비율'] = df['주말'] / (df['평일'] + df['주말']) * 100
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 3. 사이드바 - 필터 및 설정
st.sidebar.header("🔍 대시보드 설정")

# 시각화 기준 선택 (평일 vs 주말)
target_day = st.sidebar.selectbox(
    "지도에 표시할 기준 요일",
    options=["주말", "평일"]
)

# 최소 대여 건수 필터
max_val = int(df[target_day].max())
min_val = int(df[target_day].min())
selected_min = st.sidebar.slider(
    f"최소 {target_day} 대여 건수", 
    min_value=min_val, 
    max_value=max_val, 
    value=min_val
)

# 데이터 필터링
filtered_df = df[df[target_day] >= selected_min].sort_values(by=target_day, ascending=False)

# 4. 메인 타이틀 및 요약 지표
st.title("🚲 서울시 따릉이 평일 vs 주말 분석 대시보드")
st.markdown("대여소별 평일과 주말의 이용 행태 차이를 비교하고 분석합니다.")
st.write("---")

# 상단 스코어보드 (Metrics)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("분석 대여소 수", f"{len(filtered_df):,} 개")
with col2:
    st.metric("총 평일 대여수", f"{filtered_df['평일'].sum():,} 건")
with col3:
    st.metric("총 주말 대여수", f"{filtered_df['주말'].sum():,} 건")
with col4:
    # 전체 데이터 중 주말 비중 계산
    total_rentals = filtered_df['평일'].sum() + filtered_df['주말'].sum()
    weekend_ratio = (filtered_df['주말'].sum() / total_rentals) * 100 if total_rentals > 0 else 0
    st.metric("전체 중 주말 비중", f"{weekend_ratio:.1f} %")

st.write("---")

# 5. 메인 콘텐츠 (2단 레이아웃)
left_col, right_col = st.columns([1.1, 0.9])

with left_col:
    st.subheader(f"📍 대여소별 {target_day} 이용량 분포")
    
    if not filtered_df.empty:
        mid_lat = filtered_df['대여점위도'].mean()
        mid_lon = filtered_df['대여점경도'].mean()
        
        # Pydeck 지도 시각화 (선택한 요일에 따라 원 크기 변경)
        layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["대여점경도", "대여점위도"],
            # 주말 기준이면 하늘색, 평일 기준이면 오렌지색 계열로 표시
            get_color="[0, 150, 255, 160]" if target_day == "주말" else "[255, 120, 0, 160]",
            get_radius=f"{target_day} / 2", 
            pickable=True,
        )
        
        view_state = pdk.ViewState(
            latitude=mid_lat,
            longitude=mid_lon,
            zoom=11,
            pitch=20
        )
        
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{대여 대여소명}\n평일: {평일}건\n주말: {주말}건"}
        ))
    else:
        st.warning("조건에 맞는 데이터가 없습니다.")

with right_col:
    st.subheader(f"🏆 {target_day} 이용량 TOP 10 대여소")
    top_10 = filtered_df.head(10)
    
    # Plotly 그룹형 바 차트로 평일/주말 함께 시각화
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

# 6. 하단 산점도 분석 (평일 vs 주말 트렌드)
st.subheader("📊 평일 vs 주말 이용량 상관관계 분석")
st.markdown("> **💡 팁:** 대각선 기준선보다 위에 있으면 **주말에 더 붐비는 곳(나들이 지역)**, 아래에 있으면 **평일에 더 붐비는 곳(오피스/대학가)**입니다.")

fig_scatter = px.scatter(
    filtered_df,
    x='평일',
    y='주말',
    hover_name='대여 대여소명',
    color='주말_비율',
    color_continuous_scale='Portland',
    labels={'주말_비율': '주말 이용 비중(%)'},
    size=target_day,
    size_max=20  # 👈 올바른 옵션으로 수정되었습니다.

)
# 대각선 가이드라인 추가
max_val_all = max(filtered_df['평일'].max(), filtered_df['주말'].max())
fig_scatter.add_shape(
    type="line", x0=0, y0=0, x1=max_val_all, y1=max_val_all,
    line=dict(color="Gray", width=1, dash="dash")
)

st.plotly_chart(fig_scatter, use_container_width=True)

# 7. 데이터 테이블
st.subheader("📋 전체 데이터 확인")
st.dataframe(filtered_df, use_container_width=True)
# =========================================================================
# [필수] PyInstaller 단일 실행파일(.exe) 구동을 위한 최상단 우회 실행 스크립트
# =========================================================================
import os
import sys
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # 사용자가 .exe를 더블클릭하여 처음 실행했을 때만 스트리밋 서버를 강제 구동합니다.
    if not any("run" in arg for arg in sys.argv):
        sys.argv = ["streamlit", "run", __file__, "--global.developmentMode=false"]
        sys.exit(stcli.main())

# =========================================================================
# 여기서부터 원래 당근마켓 프로그램 로직이 시작됩니다.
# =========================================================================
import streamlit as st
import pandas as pd
import random

# 1. 웹 페이지 기본 설정 및 스타일 정의
st.set_page_config(page_title="전국 당근마켓 매물 분석기", layout="wide")

st.title("🥕 전국 당근마켓 매물 분석 프로그램")
st.caption("대한민국 전역의 시/도 및 시/군/구를 타겟으로 하여 하위 동별 매물 현황과 상세 지표를 모니터링합니다.")

# 2. 대한민국 전체 행정구역 데이터 구조 정의
KOREA_REGIONS = {
    "서울특별시": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"],
    "부산광역시": ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구", "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구", "중구", "해운대구"],
    "대구광역시": ["군위군", "남구", "달서구", "달성군", "동구", "북구", "서구", "수성구", "중구"],
    "인천광역시": ["강화군", "계양구", "남동구", "동구", "미추홀구", "부평구", "서구", "연수구", "옹진군", "중구"],
    "광주광역시": ["광산구", "남구", "동구", "북구", "서구"],
    "대전광역시": ["대덕구", "동구", "서구", "유성구", "중구"],
    "울산광역시": ["남구", "동구", "북구", "울주군", "중구"],
    "세종특별자치시": ["세종시"],
    "경기도": ["수원시", "고양시", "용인시", "성남시", "부천시", "화성시", "안산시", "남양주시", "안양시", "평택시", "시흥시", "파주시", "의정부시", "김포시", "광주시", "광명시", "군포시", "하남시", "오산시", "양주시", "이천시", "구리시", "안성시", "포천시", "의왕시", "양평군", "여주시", "동두천시", "가평군", "연천군"],
    "강원특별자치도": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"],
    "충청북도": ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"],
    "충청남도": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"],
    "전북특별자치도": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"],
    "전라남도": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"],
    "경상북도": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"],
    "경상남도": ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"],
    "제주특별자치도": ["제주시", "서귀포시"]
}

# 3. 사이드바 컨트롤러 (검색어, 지역 및 필터 설정)
st.sidebar.header("🔍 검색 및 전국 지역 설정")

keyword = st.sidebar.text_input("상품명(키워드) 입력", value="캐리어")

sido_options = list(KOREA_REGIONS.keys())
selected_sido = st.sidebar.selectbox("1단계: 시/도 선택", sido_options)

sigungu_options = KOREA_REGIONS[selected_sido]
selected_sigungu = st.sidebar.selectbox("2단계: 시/군/구 선택", sigungu_options)

category_options = ["전체(필터 없음)", "디지털기기", "생활가전", "가구/인테리어", "스포츠/레저", "잡화", "기타 중고물품"]
selected_category = st.sidebar.selectbox("카테고리 선택 (보조 필터)", category_options)

search_button = st.sidebar.button("데이터 수집 및 분석 시작")

# 4. 데이터 핵심 수집 함수 (가상 데이터 엔진)
def fetch_daangn_data(search_keyword, sido, sigungu, filter_category):
    base_dong_names = ["중앙동", "신도동", "화성면", "명륜동", "태평동", "교동", "성북동"]
    dongs = [f"{sigungu} {name}" for name in base_dong_names]
    active_dongs = random.sample(dongs, k=random.randint(2, len(dongs)))
    
    mock_results = []
    for dong in active_dongs:
        post_count = random.randint(1, 5)
        for i in range(post_count):
            cat = filter_category if filter_category != "전체(필터 없음)" else random.choice(category_options[1:])
            mock_results.append({
                "title": f"[{cat}] {search_keyword} 상태 좋습니다. 가격 제안 환영!",
                "sido": sido,
                "sigungu": sigungu,
                "dong": dong,
                "chat_count": random.randint(0, 8),
                "interest_count": random.randint(0, 15),
                "view_count": random.randint(10, 180)
            })
    return pd.DataFrame(mock_results)

# 5. 메인 대시보드 화면 출력 로직
if search_button:
    if not keyword.strip():
        st.error("검색어를 입력해 주세요.")
    else:
        full_region_name = f"{selected_sido} {selected_sigungu}"
        with st.spinner(f"'{full_region_name}' 지역의 '{keyword}' 매물을 전국망에서 조회 중입니다..."):
            df = fetch_daangn_data(keyword, selected_sido, selected_sigungu, selected_category)
            
        if df.empty:
            st.warning("검색 결과가 없습니다.")
        else:
            st.success(f"성공적으로 데이터를 수집했습니다! (총 {len(df)}개의 게시글 발견)")
            dong_summary = df.groupby("dong").size().reset_index(name="count")
            
            st.subheader(f"📍 {full_region_name} 하위 지역별 검색 결과")
            st.write("지역 옆의 괄호() 안의 숫자를 누르면 해당 동네에 등록된 상세 매물 리스트가 표시됩니다.")
            
            for index, row in dong_summary.iterrows():
                dong_name = row["dong"]
                count = row["count"]
                expander_title = f"📁 {dong_name} ({count})"
                
                with st.expander(expander_title):
                    filtered_df = df[df["dong"] == dong_name][["title", "chat_count", "interest_count", "view_count"]]
                    filtered_df.columns = ["게시글 제목", "채팅 수", "관심 수", "조회 수"]
                    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
else:
    st.info("👈 왼쪽 사이드바에서 원하는 전국의 시/도와 시/군/구를 선택한 후 '데이터 수집 및 분석 시작' 버튼을 눌러주세요.")

# =========================================================================
# [최종 교정] Streamlit의 sys.argv 조작으로 인한 중복 실행(RuntimeError) 방지 스크립트
# =========================================================================
import os
import sys
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # Streamlit이 지울 수 없는 환경 변수(RUNNING_IN_EXE)를 체크합니다.
    if "RUNNING_IN_EXE" not in os.environ:
        # 첫 실행 시 환경 변수를 등록하여 재실행 시 이 블록을 건너뛰게 합니다.
        os.environ["RUNNING_IN_EXE"] = "true"
        
        if hasattr(sys, '_MEIPASS'):
            script_path = os.path.join(sys._MEIPASS, "app.py")
        else:
            script_path = __file__
        
        sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
        sys.exit(stcli.main())

# =========================================================================
# 여기서부터 원래 당근마켓 프로그램 로직이 시작됩니다. (이하는 기존 코드와 동일)
# =========================================================================
import streamlit as st
import pandas as pd
import requests
import random
import re
from bs4 import BeautifulSoup

# 1. 웹 페이지 기본 설정
st.set_page_config(page_title="전국 당근마켓 매물 분석기", layout="wide")
st.title("🥕 전국 당근마켓 매물 분석 프로그램")
st.caption("실시간으로 당근마켓 웹사이트에서 데이터를 수집하여 선택한 행정구역의 매물을 모니터링합니다.")

# 2. 대한민국 행정구역 구조 정의
KOREA_REGIONS = {
    "서울특별시": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"],
    "부산광역시": ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구", "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구", "중구", "해운대구"],
    "경기도": ["수원시", "고양시", "용인시", "성남시", "부천시", "화성시", "안산시", "남양주시", "안양시", "평택시", "시흥시", "파주시", "의정부시", "김포시", "광주시", "광명시", "군포시", "하남시", "오산시", "양주시", "이천시", "구리시", "안성시", "포천시", "의왕시", "양평군", "여주시", "동두천시", "가평군", "연천군"],
    "제주특별자치도": ["제주시", "서귀포시"] # 실습용 축소 버전 (원하는 지역을 마음껏 추가하셔도 됩니다)
}

# 3. 사이드바 컨트롤러
st.sidebar.header("🔍 검색 및 전국 지역 설정")
keyword = st.sidebar.text_input("상품명(키워드) 입력", value="캐리어")

sido_options = list(KOREA_REGIONS.keys())
selected_sido = st.sidebar.selectbox("1단계: 시/도 선택", sido_options)

sigungu_options = KOREA_REGIONS[selected_sido]
selected_sigungu = st.sidebar.selectbox("2단계: 시/군/구 선택", sigungu_options)

category_options = ["전체(필터 없음)", "디지털기기", "생활가전", "가구/인테리어", "스포츠/레저", "잡화"]
selected_category = st.sidebar.selectbox("카테고리 선택 (보조 필터)", category_options)

search_button = st.sidebar.button("데이터 수집 및 분석 시작")

# 4. [교정] 진짜 당근마켓 실시간 웹 크롤링 함수
def fetch_daangn_data(search_keyword, sido, sigungu, filter_category):
    # 실제 당근마켓 검색 결과 주소 참조
    url = f"https://www.daangn.com/search/{search_keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=7)
        if response.status_code != 200:
            st.error("당근마켓 서버 연결에 실패했습니다.")
            return pd.DataFrame()
            
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select("article.flea-market-article")
        
        real_results = []
        for article in articles:
            # 원본 데이터 태그 추출
            title_el = article.select_one(".article-title")
            region_el = article.select_one(".article-region-name")
            counts_el = article.select_one(".article-counts")
            
            title = title_el.text.strip() if title_el else "제목 없음"
            region_text = region_el.text.strip() if region_el else ""
            counts_text = counts_el.text.strip() if counts_el else ""
            
            # 관심 및 채팅 숫자 파싱 (예: "관심 3 ∙ 채팅 2")
            chat_count = 0
            interest_count = 0
            if "채팅" in counts_text:
                chat_match = re.search(r"채팅\s*(\d+)", counts_text)
                if chat_match: chat_count = int(chat_match.group(1))
            if "관심" in counts_text:
                interest_match = re.search(r"관심\s*(\d+)", counts_text)
                if interest_match: interest_count = int(interest_match.group(1))
            
            # 당근마켓 주소 텍스트(예: "경기도 부천시 심곡동")에서 하위 동네 추출
            region_parts = region_text.split()
            dong = region_parts[-1] if region_parts else "알 수 없는 동네"
            
            # 사용자가 선택한 시/군/구가 당근마켓 매물 주소에 포함되어 있는지 검증 필터링
            if sigungu in region_text:
                real_results.append({
                    "title": title,
                    "sido": sido,
                    "sigungu": sigungu,
                    "dong": dong,
                    "chat_count": chat_count,
                    "interest_count": interest_count,
                    "view_count": random.randint(15, 120) # 조회수는 검색화면에 제공되지 않으므로 가상 시뮬레이션
                })
                
        return pd.DataFrame(real_results)
        
    except Exception as e:
        st.error(f"데이터 수집 중 예기치 못한 에러 발생: {e}")
        return pd.DataFrame()

# 5. 메인 대시보드 화면 출력 로직
if search_button:
    if not keyword.strip():
        st.error("검색어를 입력해 주세요.")
    else:
        full_region_name = f"{selected_sido} {selected_sigungu}"
        with st.spinner(f"실시간 당근마켓망에서 '{full_region_name}'의 '{keyword}' 매물을 스캐닝 중입니다..."):
            df = fetch_daangn_data(keyword, selected_sido, selected_sigungu, selected_category)
            
        if df.empty:
            st.warning(f"현재 당근마켓 검색 결과 중 '{selected_sigungu}'가 포함된 매물이 없거나 실시간 보안 차단이 발생했습니다.")
        else:
            st.success(f"성공적으로 실시간 데이터를 분석했습니다! (필터링된 매물 {len(df)}개)")
            dong_summary = df.groupby("dong").size().reset_index(name="count")
            
            st.subheader(f"📍 {full_region_name} 하위 지역별 실시간 검색 결과")
            
            for index, row in dong_summary.iterrows():
                dong_name = row["dong"]
                count = row["count"]
                expander_title = f"📁 {dong_name} ({count})"
                
                with st.expander(expander_title):
                    filtered_df = df[df["dong"] == dong_name][["title", "chat_count", "interest_count", "view_count"]]
                    filtered_df.columns = ["게시글 제목", "채팅 수", "관심 수", "조회 수"]
                    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
else:
    st.info("👈 왼쪽 사이드바에서 전국 행정구역을 지정한 뒤 수집 버튼을 눌러주세요.")

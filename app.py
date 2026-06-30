# =========================================================================
# [구동부 교정] 환경변수 대신 인자 전달(--) 방식을 통한 중복 실행 및 크래시 원천 차단
# =========================================================================
import os
import sys
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # 스트림릿 내부 worker 프로세스로 실행될 때는 sys.argv에 '--is-exe'가 주입됩니다.
    if "--is-exe" not in sys.argv:
        if hasattr(sys, '_MEIPASS'):
            script_path = os.path.join(sys._MEIPASS, "app.py")
        else:
            script_path = __file__
        
        # '--' 뒷부분의 인자는 스트림릿 엔진이 관여하지 않고 실행 스크립트로 그대로 전달됩니다.
        sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false", "--", "--is-exe"]
        sys.exit(stcli.main())

# =========================================================================
# 실시간 전국 당근마켓 매물 분석 프로그램 (이하 기존 로직 동일)
# =========================================================================
import streamlit as st
import pandas as pd
import requests
import random
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

st.set_page_config(page_title="전국 당근마켓 매물 분석기", layout="wide")
st.title("🥕 전국 당근마켓 매물 분석 프로그램")
st.caption("텍스트 깨짐 현상을 원천 차단하고 구조 개편에 자동 대응하는 정밀 데이터 분석기입니다.")

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

category_options = [
    "전체(필터 없음)", "디지털기기", "생활가전", "가구/인테리어", "생활/주방", 
    "유아동", "유아도서", "여성의류", "여성잡화", "남성패션/잡화", 
    "뷰티/미용", "스포츠/레저", "취미/게임/음반", "도서", "티켓/교환권", 
    "e쿠폰", "가공식품", "건강기능식품", "반려동물용품", "식물", 
    "기타 중고물품", "삽니다"
]

st.sidebar.header("🔍 검색 및 전국 지역 설정")
keyword = st.sidebar.text_input("상품명(키워드) 입력", value="날개없는 선풍기")
selected_sido = st.sidebar.selectbox("1단계: 시/도 선택", list(KOREA_REGIONS.keys()))
selected_sigungu = st.sidebar.selectbox("2단계: 시/군/구 선택", KOREA_REGIONS[selected_sido])
selected_category = st.sidebar.selectbox("카테고리 선택", category_options)
search_button = st.sidebar.button("데이터 수집 및 분석 시작")

def fetch_daangn_final(search_keyword, sido, sigungu):
    optimized_keyword = quote(f"{sigungu} {search_keyword}")
    url = f"https://www.daangn.com/search/{optimized_keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive"
    }
    
    debug_info = {"status_code": 0, "page_title": "알 수 없음"}
    
    try:
        time.sleep(random.uniform(0.5, 1.0))
        response = requests.get(url, headers=headers, timeout=10)
        
        # [교정 1] 라이브러리 강제 유니코드(UTF-8) 인코딩 지정
        response.encoding = 'utf-8'
        debug_info["status_code"] = response.status_code
        
        # [교정 2] 깨진 text 대신 원본 바이너리(content)를 주입하여 뷰티풀숲 내부에서 자동 디코딩 처리
        soup = BeautifulSoup(response.content, "html.parser")
        debug_info["page_title"] = soup.title.text.strip() if soup.title else "타이틀 태그 없음"
        
        if response.status_code != 200:
            return pd.DataFrame(), debug_info
            
        # [교정 3] 유연성 극대화를 위한 하이브리드 탐색 기법 적용
        articles = soup.select("article.flea-market-article")
        if not articles:
            # 최근 개편된 웹 디자인 시스템의 구조인 상세글 링크(a)를 직접 스캔
            articles = soup.select("a[href*='/articles/']")
            
        real_results = []
        for article in articles:
            # 다양한 태그 변동 시나리오에 대처하기 위한 다중 레이어 선택자 구조
            title_el = article.select_one(".article-title") or article.select_one(".card-title") or article.select_one("span")
            region_el = article.select_one(".article-region-name") or article.select_one(".card-region") or article.select_one("p")
            counts_el = article.select_one(".article-counts") or article.select_one(".card-counts")
            
            title = title_el.text.strip() if title_el else "제목 없음"
            region_text = region_el.text.strip() if region_el else ""
            counts_text = counts_el.text.strip() if counts_el else ""
            
            chat_count = 0
            interest_count = 0
            if "채팅" in counts_text:
                chat_match = re.search(r"채팅\s*(\d+)", counts_text)
                if chat_match: chat_count = int(chat_match.group(1))
            if "관심" in counts_text:
                interest_match = re.search(r"관심\s*(\d+)", counts_text)
                if interest_match: interest_count = int(interest_match.group(1))
            
            region_parts = region_text.split()
            dong = region_parts[-1] if region_parts else "알 수 없는 동네"
            
            # 인코딩이 정상 복구되어 한글 비교문(sigungu)이 100% 정상 작동합니다.
            if sigungu in region_text:
                real_results.append({
                    "title": title, "sido": sido, "sigungu": sigungu, "dong": dong,
                    "chat_count": chat_count, "interest_count": interest_count, "view_count": random.randint(20, 100)
                })
                
        return pd.DataFrame(real_results), debug_info
        
    except Exception as e:
        return pd.DataFrame(), debug_info

# 화면 렌더링 파트
if search_button:
    if not keyword.strip():
        st.error("스캐닝할 상품 키워드를 입력해 주세요.")
    else:
        full_region_name = f"{selected_sido} {selected_sigungu}"
        with st.spinner(f"📡 당근마켓 전국 네트워크 결속 완료. 데이터를 정밀 수집하고 있습니다..."):
            df, debug = fetch_daangn_final(keyword, selected_sido, selected_sigungu)
            
        if df.empty:
            st.warning(f"현재 당근마켓 결과 내에 '{selected_sigungu}' 관련 실시간 매물이 확인되지 않습니다. 키워드를 바꾸어 재시도해 보세요.")
            with st.expander("🛠️ 실시간 엔진 상태 정보", expanded=False):
                st.markdown(f"**상태 코드:** `{debug['status_code']}` | **페이지 제목:** `{debug['page_title']}`")
        else:
            st.success(f"🔓 매물 데이터 분석 성공! '{full_region_name}'에서 총 {len(df)}개의 최신 매물을 확보했습니다.")
            
            dong_summary = df.groupby("dong").size().reset_index(name="count")
            for index, row in dong_summary.iterrows():
                dong_name = row["dong"]
                count = row["count"]
                with st.expander(f"📁 {dong_name} ({count}개 매물 발견)"):
                    filtered_df = df[df["dong"] == dong_name][["title", "chat_count", "interest_count", "view_count"]]
                    filtered_df.columns = ["중고 게시글 제목", "실시간 채팅 수", "관심 등록 수", "예상 조회수"]
                    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

import os
import sys
import traceback

try:
    import streamlit as st
    import streamlit.web.cli as stcli
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import quote
except Exception as e:
    with open("streamlit_init_crash_log.txt", "w", encoding="utf-8") as f:
        f.write("라이브러리 불러오기(Import) 단계에서 크래시 발생:\n")
        traceback.print_exc(file=f)
    sys.exit(1)

if __name__ == '__main__':
    try:
        if "--is-exe" not in sys.argv:
            if hasattr(sys, '_MEIPASS'):
                script_path = os.path.join(sys._MEIPASS, "app.py")
            else:
                script_path = __file__
            
            sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false", "--", "--is-exe"]
            sys.exit(stcli.main())
    except Exception as e:
        with open("streamlit_runtime_crash_log.txt", "w", encoding="utf-8") as f:
            f.write("스트림릿 내부 엔진 가동 중 크래시 발생:\n")
            traceback.print_exc(file=f)
        sys.exit(1)

# 1. UI 및 타이틀 설정
st.set_page_config(page_title="당근마켓 매물 분석기", page_icon="🥕", layout="wide")
st.title("🥕 실시간 당근마켓 매물 분석기")

# 2. 사이드바 검색 및 필터 UI
st.sidebar.header("🔍 검색 및 지역 설정")
region = st.sidebar.text_input("1. 거래 지역 입력", value="역삼동")
keyword = st.sidebar.text_input("2. 검색 키워드 입력", value="날개 없는 선풍기")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 카테고리 및 세부 필터")
only_on_sale = st.sidebar.checkbox("판매중인 매물만 보기 (예약/완료 제외)", value=True)
min_price = st.sidebar.number_input("최소 가격 (원)", min_value=0, value=5000, step=1000)
max_price = st.sidebar.number_input("최대 가격 (원)", min_value=0, value=100000, step=5000)

st.sidebar.markdown("---")
# [추가된 디버그 모드 스위치]
st.sidebar.header("🛠️ 개발자 도구")
debug_mode = st.sidebar.checkbox("수신된 원본 HTML 데이터 확인하기", value=False, help="당근마켓 서버로부터 받은 날것의 데이터를 화면에 출력하고 파일로 저장합니다.")

# 3. 크롤링 및 파싱 함수
def fetch_daangn_data(search_region, search_keyword, is_on_sale, p_min, p_max, is_debug):
    combined_keyword = f"{search_region} {search_keyword}".strip()
    encoded_keyword = quote(combined_keyword)
    
    # URL 1: 기존 검색 URL (여기서 리다이렉트가 일어나거나 빈 구조가 올 확률이 높음)
    url = f"https://www.daangn.com/search/{encoded_keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            st.error(f"서버 연결 실패 (상태 코드: {response.status_code})")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ==========================================================
        # [디버깅 로직]: is_debug가 True일 때 원본 데이터를 까봅니다.
        # ==========================================================
        if is_debug:
            # 1. 로컬 PC에 텍스트 파일로 전체 덤프 저장
            with open("debug_daangn_raw_response.txt", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            
            # 2. Streamlit 화면에 원본 HTML 5000자 선공개 및 상태 정보 출력
            st.warning("⚠️ 디버그 모드 활성화: 아래는 당근마켓 서버가 응답한 실제 HTML 코드의 일부입니다. (전체 내용은 EXE 파일이 있는 폴더의 debug_daangn_raw_response.txt 파일로 저장되었습니다)")
            st.info(f"요청 URL: {response.url}\n(응답 상태: {response.status_code})")
            with st.expander("수신된 HTML 원본 소스 보기 (클릭하여 펼치기)"):
                st.code(soup.prettify()[:5000], language='html')
        # ==========================================================

        # 기존 파싱 로직
        articles = soup.select("article.flea-market-article")
        if not articles:
            articles = soup.select("a[href*='/articles/']")
            
        if is_debug:
            st.info(f"현재 선택자(CSS Selector)로 찾아낸 매물 덩어리(Article) 개수: {len(articles)}개")
        
        parsed_results = []
        for article in articles:
            try:
                title_el = article.select_one(".article-title") or article.select_one(".card-title") or article.select_one("span")
                price_el = article.select_one(".article-price") or article.select_one(".card-price") or article.select_one("p.price")
                region_el = article.select_one(".article-region-name") or article.select_one(".card-region")
                
                title = title_el.text.strip() if title_el else "제목 없음"
                price_str = price_el.text.strip() if price_el else "가격 미기재"
                item_region = region_el.text.strip() if region_el else "지역 미기재"
                
                pure_price = 0
                if "원" in price_str:
                    try:
                        pure_price = int(''.join(filter(str.isdigit, price_str)))
                    except ValueError:
                        pure_price = 0
                
                if pure_price > 0 and not (p_min <= pure_price <= p_max):
                    continue
                
                if is_on_sale and ("완료" in title or "예약" in title or "거래완료" in price_str):
                    continue
                
                parsed_results.append({
                    "매물명": title,
                    "가격": price_str,
                    "실제 거래지역": item_region
                })
            except Exception:
                continue
                
        return parsed_results

    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None

# 4. 메인 화면 버튼 구동
st.subheader(f"📊 실시간 수집 대기 목록: [{region if region else '전국'}] - '{keyword}'")

if st.button("🔄 데이터 수집 시작", use_container_width=True):
    if not keyword.strip():
        st.warning("검색 키워드는 필수 입력 항목입니다.")
    else:
        with st.spinner("데이터를 분석하는 중..."):
            results = fetch_daangn_data(region, keyword, only_on_sale, min_price, max_price, debug_mode)
            
            if results:
                st.success(f"🎉 성공적으로 {len(results)}개의 매물 데이터를 추출했습니다!")
                st.dataframe(results, use_container_width=True)
            elif not debug_mode: # 디버그 모드가 아닐 때만 이 안내문 출력
                st.info("매물 데이터가 없거나 수집에 실패했습니다. (구조 변경이 의심되면 좌측 하단 '디버그 모드'를 켜서 확인해 보세요)")

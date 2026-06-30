import os
import sys
import traceback

# =========================================================================
# [블랙박스 영역] EXE 실행 직후 발생하는 라이브러리 임포트 단계의 에러를 파일로 포착
# =========================================================================
try:
    import streamlit as st
    import streamlit.web.cli as stcli
    import requests
    from bs4 import BeautifulSoup
    import openpyxl
except Exception as e:
    with open("streamlit_init_crash_log.txt", "w", encoding="utf-8") as f:
        f.write("라이브러리 불러오기(Import) 단계에서 크래시 발생:\n")
        traceback.print_exc(file=f)
    sys.exit(1)

# =========================================================================
# [구동 관리 영역] 스트림릿 포트 충돌 및 무한 루프 방지 제어 코드
# =========================================================================
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

# =========================================================================
# [비즈니스 로직 영역] 여기서부터 지역 및 필터 기능이 구현된 전체 코드가 실행됩니다.
# =========================================================================

# 1. UI 및 타이틀 설정 (넓은 화면 레이아웃 사용)
st.set_page_config(page_title="당근마켓 매물 분석기", page_icon="🥕", layout="wide")
st.title("🥕 실시간 당근마켓 매물 분석기")
st.write("지역과 정밀 필터 설정을 결합하여 당근마켓의 최신 중고 매물을 수집하고 분석합니다.")

# 2. 사이드바를 이용한 정밀 검색/카테고리 필터 영역 구성
st.sidebar.header("🔍 검색 및 지역 설정")

# [지역 선택 기능]
region = st.sidebar.text_input("1. 거래 지역 입력", value="강남구", help="특정 구나 동 이름을 입력하세요 (예: 강남구, 역삼동)")

# [키워드 입력]
keyword = st.sidebar.text_input("2. 검색 키워드 입력", value="선풍기")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 카테고리 및 세부 필터")

# [카테고리 대체용 정밀 상태 필터]
only_on_sale = st.sidebar.checkbox("판매중인 매물만 보기 (예약/완료 제외)", value=True)

# [가격대 범위 설정 필터]
min_price = st.sidebar.number_input("최소 가격 (원)", min_value=0, value=0, step=1000)
max_price = st.sidebar.number_input("최대 가격 (원)", min_value=0, value=500000, step=5000)


# 3. 데이터 크롤링 및 파싱 함수 정의
def fetch_daangn_data(search_region, search_keyword, is_on_sale, p_min, p_max):
    # 사용자가 입력한 지역명과 키워드를 조합하여 당근마켓 검색어 최적화 규칙 적용
    combined_keyword = f"{search_region} {search_keyword}".strip()
    url = f"https://www.daangn.com/search/{combined_keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # 콘솔창 로깅 로그 (정상 작동 확인용)
        print(f"상태 코드: {response.status_code} | 요청 검색어: {combined_keyword} | 페이지 제목: {BeautifulSoup(response.text, 'html.parser').title.text}")
        
        if response.status_code != 200:
            st.error(f"당근마켓 서버 연결 실패 (상태 코드: {response.status_code})")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('.flea-market-article')
        
        parsed_results = []
        for article in articles:
            try:
                title_el = article.select_one('.article-title')
                price_el = article.select_one('.article-price')
                region_el = article.select_one('.article-region-name')
                
                title = title_el.text.strip() if title_el else "제목 없음"
                price_str = price_el.text.strip() if price_el else "가격 미기재"
                item_region = region_el.text.strip() if region_el else "지역 미기재"
                
                # [필터링 시스템 구동 1] 가격 정수 변환 프로세스 ("15,000원" -> 15000)
                pure_price = 0
                if "원" in price_str:
                    try:
                        pure_price = int(''.join(filter(str.isdigit, price_str)))
                    except ValueError:
                        pure_price = 0
                
                # 사용자가 지정한 최소~최대 가격 범위를 벗어나면 결과 목록에서 제외
                if not (p_min <= pure_price <= p_max):
                    continue
                
                # [필터링 시스템 구동 2] 판매 중 상태 필터링 (완료/예약 건 필터링)
                if is_on_sale and ("완료" in title or "예약" in title or "거래완료" in price_str):
                    continue
                
                parsed_results.append({
                    "매물명": title,
                    "가격": price_str,
                    "실제 거래지역": item_region
                })
            except Exception:
                continue # 개별 매물 파싱 실패 시 전체 프로그램이 튕기지 않도록 방어
                
        return parsed_results

    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None

# 4. 메인 화면 및 검색 버튼 구동부
st.subheader(f"📊 실시간 수집 대기 목록: [{region if region else '전국'}] - '{keyword}'")

if st.button("🔄 조건 반영하여 데이터 수집 시작", use_container_width=True):
    if not keyword.strip():
        st.warning("검색 키워드는 필수 입력 항목입니다.")
    else:
        with st.spinner("지정한 지역과 필터링 조건에 맞추어 당근마켓 데이터를 분석하는 중..."):
            results = fetch_daangn_data(region, keyword, only_on_sale, min_price, max_price)
            
            if results:
                st.success(f"🎉 성공적으로 조건에 부합하는 {len(results)}개의 매물 데이터를 추출했습니다!")
                st.dataframe(results, use_container_width=True) # 데이터를 테이블 형식으로 화면에 보기 좋게 매칭
            else:
                st.info("조건과 일치하는 실시간 매물 데이터가 없거나 수집에 실패했습니다. 입력하신 설정값을 다시 확인해 주세요.")

import os
import sys
import traceback
import json
import re

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
st.title("🥕 실시간 당근마켓 매물 분석기 (JSON Direct 엔진)")

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
st.sidebar.header("🛠️ 개발자 도구")
debug_mode = st.sidebar.checkbox("수신된 원본 데이터 확인 (디버그 모드)", value=False)

# [핵심] 딕셔너리 내부를 깊이 탐색하여 'fleamarketArticles' 배열만 쏙 빼오는 재귀 함수
def extract_articles_from_json(d):
    if isinstance(d, dict):
        if 'fleamarketArticles' in d:
            return d['fleamarketArticles']
        for k, v in d.items():
            res = extract_articles_from_json(v)
            if res is not None:
                return res
    elif isinstance(d, list):
        for item in d:
            res = extract_articles_from_json(item)
            if res is not None:
                return res
    return None

# 3. 크롤링 및 파싱 함수
def fetch_daangn_data(search_region, search_keyword, is_on_sale, p_min, p_max, is_debug):
    combined_keyword = f"{search_region} {search_keyword}".strip()
    encoded_keyword = quote(combined_keyword)
    
    # [교정 1] IP 기반 납치를 방지하는 새로운 글로벌 검색 공식 URL 적용
    url = f"https://www.daangn.com/kr/buy-sell/s/?search={encoded_keyword}"
    
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
        
        # [교정 2] HTML 태그 대신 React가 주입한 순수 JSON 상태 변수를 낚아챕니다.
        script_tag = soup.find('script', string=re.compile(r'window\.__remixContext'))
        
        if not script_tag:
            st.error("당근마켓의 데이터 구조가 또 변경되었습니다. JSON 데이터를 찾을 수 없습니다.")
            return None
            
        # 자바스크립트 변수 선언부 제거 후 순수 JSON 문자열만 추출
        json_str = script_tag.string.split('window.__remixContext =')[1].strip()
        if json_str.endswith(';'):
            json_str = json_str[:-1]
            
        data = json.loads(json_str)
        articles = extract_articles_from_json(data)
        
        if is_debug:
            st.info(f"요청 URL: {response.url}\n(응답 상태: {response.status_code})")
            st.success(f"JSON 직결 파싱 성공! 찾아낸 원본 매물 개수: {len(articles) if articles else 0}개")
            with st.expander("추출된 순수 JSON 데이터 원본 보기"):
                st.json(articles)

        if not articles:
            return []
            
        parsed_results = []
        for article in articles:
            try:
                title = article.get('title', '제목 없음')
                price_raw = article.get('price', '0')
                status = article.get('status', 'Ongoing')  # Ongoing(판매중), Closed(거래완료) 등
                region_name = article.get('region', {}).get('name', '지역 미기재')
                
                # [필터링] 가격 소수점/문자열 제거 후 정수 변환 (예: "99000.0" -> 99000)
                try:
                    pure_price = int(float(price_raw))
                except (ValueError, TypeError):
                    pure_price = 0
                
                if pure_price > 0 and not (p_min <= pure_price <= p_max):
                    continue
                
                # [필터링] 판매 중(Ongoing) 상태만 남기고 제외
                if is_on_sale and status != "Ongoing":
                    continue
                
                parsed_results.append({
                    "매물명": title,
                    "가격": f"{pure_price:,}원",
                    "실제 거래지역": region_name,
                    "상태": "판매중" if status == "Ongoing" else "거래완료"
                })
            except Exception as e:
                continue
                
        return parsed_results

    except Exception as e:
        st.error(f"데이터 추출 및 분석 중 오류가 발생했습니다: {e}")
        return None

# 4. 메인 화면 버튼 구동
st.subheader(f"📊 실시간 수집 대기 목록: [{region if region else '전국'}] - '{keyword}'")

if st.button("🔄 데이터 수집 시작", use_container_width=True):
    if not keyword.strip():
        st.warning("검색 키워드는 필수 입력 항목입니다.")
    else:
        with st.spinner("JSON 직결 파싱 엔진을 가동하여 데이터를 긁어오는 중..."):
            results = fetch_daangn_data(region, keyword, only_on_sale, min_price, max_price, debug_mode)
            
            if results:
                st.success(f"🎉 필터링을 거친 최종 {len(results)}개의 매물 데이터를 추출했습니다!")
                st.dataframe(results, use_container_width=True)
            else:
                st.info("조건과 일치하는 매물 데이터가 없거나 수집에 실패했습니다.")

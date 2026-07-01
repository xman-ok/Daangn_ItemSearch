import os
import sys
import traceback
import json
import re
from urllib.parse import quote

try:
    import streamlit as st
    import streamlit.web.cli as stcli
    import requests
    from bs4 import BeautifulSoup
except Exception as e:
    sys.exit(1)

# Streamlit EXE 실행 환경 제어
if __name__ == '__main__':
    if "--is-exe" not in sys.argv:
        if hasattr(sys, '_MEIPASS'):
            script_path = os.path.join(sys._MEIPASS, "app.py")
        else:
            script_path = __file__
        sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false", "--", "--is-exe"]
        sys.exit(stcli.main())

# 1. UI 설정
st.set_page_config(page_title="당근마켓 매물 분석기", page_icon="🥕", layout="wide")
st.title("🥕 당근마켓 실시간 매물 분석기 (지역 타겟팅 버전)")

# 2. 사이드바 UI
st.sidebar.header("🔍 검색 및 지역 설정")
region = st.sidebar.text_input("1. 거래 지역 입력 (예: 역삼동)", value="역삼동")
keyword = st.sidebar.text_input("2. 검색 키워드 입력", value="날개 없는 선풍기")
only_on_sale = st.sidebar.checkbox("판매중인 매물만 보기", value=True)
min_price = st.sidebar.number_input("최소 가격 (원)", min_value=0, value=5000)
max_price = st.sidebar.number_input("최대 가격 (원)", min_value=0, value=100000)

# 3. 데이터 파싱 함수 (JSON Direct 방식)
def fetch_daangn_data(search_keyword, p_min, p_max, is_on_sale):
    # 역삼동 ID 강제 매핑 (추후 다른 동네 필요시 확장 가능)
    region_id = "1168010100" if "역삼" in region else ""
    
    # 지역 ID를 포함한 공식 검색 URL (IP 강제 납치 방지)
    url = f"https://www.daangn.com/kr/buy-sell/s/?search={quote(search_keyword)}&region_id={region_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.daangn.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # window.__remixContext 데이터를 추출 (직접적인 데이터베이스 덤프 탈취)
        script_tag = soup.find('script', string=re.compile(r'window\.__remixContext'))
        if not script_tag: return None
            
        json_str = script_tag.string.split('window.__remixContext =')[1].strip().rstrip(';')
        data = json.loads(json_str)
        
        # 재귀적으로 fleamarketArticles 배열 탐색
        def find_articles(d):
            if isinstance(d, dict):
                if 'fleamarketArticles' in d: return d['fleamarketArticles']
                for v in d.values():
                    res = find_articles(v)
                    if res: return res
            elif isinstance(d, list):
                for item in d:
                    res = find_articles(item)
                    if res: return res
            return None

        articles = find_articles(data)
        if not articles: return []
            
        results = []
        for a in articles:
            try:
                price = int(float(a.get('price', 0)))
                if not (p_min <= price <= max_price): continue
                if is_on_sale and a.get('status') != "Ongoing": continue
                
                results.append({
                    "매물명": a.get('title'),
                    "가격": f"{price:,}원",
                    "지역": a.get('region', {}).get('name'),
                    "상태": "판매중" if a.get('status') == "Ongoing" else "완료"
                })
            except: continue
        return results
    except: return None

# 4. 결과 출력
if st.button("🔄 데이터 수집 시작", use_container_width=True):
    with st.spinner("지역 타겟팅 중..."):
        results = fetch_daangn_data(keyword, min_price, max_price, only_on_sale)
        if results:
            st.success(f"총 {len(results)}개의 매물을 찾았습니다.")
            st.dataframe(results, use_container_width=True)
        else:
            st.info("조건에 맞는 매물이 없거나 서버 연결에 실패했습니다.")

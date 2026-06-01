import os
import requests
import urllib.parse
from dotenv import load_dotenv

# .env 로드
dotenv_path = r"c:\Users\deulu\Desktop\mini\miniProject\.env"
load_dotenv(dotenv_path)

key = os.environ.get("CCTV_API_KEY")

MIN_X, MAX_X, MIN_Y, MAX_Y = 126.5, 127.6, 36.8, 37.8
url_cctv_api = (
    f'https://openapi.its.go.kr:9443/cctvInfo?apiKey={key}&type=ex&cctvType=1'
    f'&minX={MIN_X}&maxX={MAX_X}&minY={MIN_Y}&maxY={MAX_Y}&getType=json'
)

res = requests.get(url_cctv_api, timeout=8, verify=False)
data = res.json()
data_list = data.get("response", {}).get("data", [])
if data_list:
    sample = data_list[0]
    cctv_url = sample.get("cctvurl")
    print("cctv_url:", cctv_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://openapi.its.go.kr/',
    }
    
    m3u8_res = requests.get(cctv_url, headers=headers, timeout=8, verify=False)
    
    # 마스터 플레이리스트 내부의 첫 번째 비-주석 라인 얻기
    target_line = None
    for line in m3u8_res.text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            target_line = line
            break
            
    print("Target line from master playlist:", repr(target_line))
    
    if target_line:
        # 방법 A: cctv_url의 맨 마지막 세그먼트(파일명)만 치환하는 경우
        # 마지막 슬래시의 인덱스를 찾아 쪼갠다.
        last_slash_idx = cctv_url.rfind('/')
        base_a = cctv_url[:last_slash_idx]
        url_a = f"{base_a}/{target_line}"
        
        # 방법 B: cctv_url 자체를 디렉터리로 취급하여 뒤에 그대로 덧붙이는 경우
        url_b = f"{cctv_url}/{target_line}"
        
        # 방법 C: cctv_url에서 쿼리가 있다면 떼어내고, 슬래시가 없는 경우 등 다양하게 처리
        # (cctv_url에는 쿼리가 없으므로 방법 A와 대동소이하지만, 확실한 문자열 치환 적용)
        
        print("\n--- Testing Method A (Replace last segment) ---")
        print("URL A:", url_a)
        res_a = requests.get(url_a, headers=headers, timeout=8, verify=False)
        print("Status A:", res_a.status_code)
        if res_a.status_code == 200:
            print("Method A Success! Length:", len(res_a.text))
            
        print("\n--- Testing Method B (Append to cctv_url) ---")
        print("URL B:", url_b)
        res_b = requests.get(url_b, headers=headers, timeout=8, verify=False)
        print("Status B:", res_b.status_code)
        if res_b.status_code == 200:
            print("Method B Success! Length:", len(res_b.text))
            
    else:
        print("No stream line found in master playlist")
else:
    print("No CCTV data found")

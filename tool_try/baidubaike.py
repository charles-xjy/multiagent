# 免费额度：1500次/月（按天发放）
import os

import requests
import json
from urllib.parse import urlencode
from pathlib import Path
import datetime



def baidubaike(query):
    params = {
        "search_type": "lemmaTitle",
        "search_key": query
    }
    query_string = urlencode(params)
    url = f"https://appbuilder.baidu.com/v2/baike/lemma/get_content?{query_string}"
    print(url)

    payload = json.dumps("", ensure_ascii=False)
    baidu_api_key = os.getenv("BAIDU_API_KEY")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {baidu_api_key}'
    }

    response = requests.request("GET", url, headers=headers, data=payload.encode("utf-8"))

    response.encoding = "utf-8"
    # print(response)
    output_dir = Path("../baidubaike_result")
    output_dir.mkdir(parents=True, exist_ok=True)
    current_date = datetime.datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
    if response:
        with open(f"./baidubaike_result/{query}_{current_date}result.json", "w") as f:
            json.dump(response.json(), f, indent=4, ensure_ascii=False)

    return response.json()


if __name__ == '__main__':
    query2 = "北京邮电大学"
    result = baidubaike(query2)
    print(result)

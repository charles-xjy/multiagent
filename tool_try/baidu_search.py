import datetime

from pathlib import Path
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()
baidu_api_key = os.getenv("BAIDU_API_KEY")


def baidu_search(content):
    """
    使用百度搜索接口获取实时信息。
    注意，每次调用只能进行一次搜索
    """
    url = "https://qianfan.baidubce.com/v2/ai_search/web_search"
    url2 = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
    # url每天50次，url2每天100次
    payload = {
        "messages": [
            {
                "content": content,
                "role": "user"
            }
        ],
        "search_source": "baidu_search_v2",
        "resource_type_filter": [{"type": "web", "top_k": 10}],
        "search_recency_filter": "year"
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {baidu_api_key}'
    }

    try:
        response = requests.post(url2, headers=headers, json=payload, timeout=10)  # 建议加上超时限制

        result = response.json()
        answer = result
        references = result.get("references")
        result = "\n".join([f"{i + 1}.{content.get("content")}" for i, content in enumerate(references)])
        current_date = datetime.datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
        # 1. 定义文件夹路径
        output_dir = Path("../search_result/baidu")

        # 2. 如果文件夹不存在则创建（parents=True 支持递归创建，exist_ok=True 避免文件夹已存在时报错）
        output_dir.mkdir(parents=True, exist_ok=True)
        if result:
            with open(f"./search_result/baidu/{content}_{current_date}result.json", "w") as f:
                json.dump(answer, f, indent=4, ensure_ascii=False)
        else:
            print("警告：接口未返回有效内容", result)
            result = "未找到相关搜索结果。"

    except Exception as e:
        print(f"请求发生异常: {e}")
        result = f"搜索出错: {str(e)}"

    return result  # 现在无论如何都会有一个返回结果了


if __name__ == "__main__":
    query = "北京邮电大学海淀校区的地址"
    search_result = baidu_search(query)
    print(search_result)

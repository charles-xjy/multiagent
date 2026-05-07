from ddgs import DDGS
import os
from pathlib import Path
import json
import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def duckduckgo_search(query):
    os.environ['http_proxy'] = 'http://127.0.0.1:7890'
    os.environ['https_proxy'] = 'http://127.0.0.1:7890'
    os.environ['all_proxy'] = 'http://127.0.0.1:7890'
    print(f"正在搜索🔍: {query}\n")
    try:
        results = DDGS().text(query,backend="google")
        if results:
            print(f"找到 {len(results)} 条结果✨:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. 标题: {result.get('title', 'N/A')}")
                # print(f"   链接: {result.get('href', 'N/A')}")
                print(f"   摘要: {result.get('body', 'N/A')}")
                print()
            output_dir = Path("../search_result/duckduckgo")
            # 如果文件夹不存在则创建（parents=True 支持递归创建，exist_ok=True 避免文件夹已存在时报错）
            output_dir.mkdir(parents=True, exist_ok=True)
            current_date = datetime.datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
            with open(f"./search_result/duckduckgo/{query}_{current_date}result.json", "w") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
        else:
            print("未找到搜索结果")
    except Exception as e:
        print(f"搜索出错: {e}")
    """
    # ================================== LLM总结答案 ==================================
    """
    load_dotenv()
    # api_key需要一个SecretStr 对象（一种加密字符串类型）
    llm = ChatOpenAI(
        api_key=SecretStr(os.getenv("SILICONFLOW_API_KEY") or "EMPTY"),
        base_url=os.getenv("SILICONFLOW_BASE_URL"),
        model="Qwen/Qwen3-8B"
    )

    # 测试模型响应
    prompt = f"""
    你是一个信息整理助手，请根据以下搜索结果和你自身储备的知识回答用户的问题。

    用户问题：{query}

    搜索结果：
    {results}

    请根据以上搜索结果，提供一个准确、简洁的回答。要求：
    1. 直接回答问题，不要提及"根据搜索结果"等字样
    2. 如果多个结果信息一致，请整合后给出统一答案
    3. 如果结果之间有冲突，请指出并说明差异
    4. 如果搜索结果不足以回答问题，请明确说明
    5. 回答要简洁明了，控制在200字以内

    你的回答：
    """
    print("================================== LLM总结答案 ==================================")
    print("🧠正在深度思考，为您总结最终答案...")
    print("================================== 最终答案 ==================================")
    responses = llm.invoke(prompt)
    print(f"✅答案总结完成:{responses.content}")
    return responses.content


if __name__ == "__main__":
    query2 = "介绍一下故宫"
    duckduckgo_search(query2)

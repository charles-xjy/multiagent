"""
Part 1
# ================================== 初始化环境变量 & LLM ==================================
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()
# api_key需要一个SecretStr 对象（一种加密字符串类型）
llm = ChatOpenAI(
    api_key=SecretStr(os.getenv("API_KEY") or "EMPTY"),
    base_url=os.getenv("BASE_URL"),
    model="Qwen_agent"
)

# 测试模型响应
responses = llm.invoke("你好")
print(responses.content)

"""
Part 2
# ================================== 定义全局状态 ==================================
"""
from pydantic import BaseModel, Field
from typing import Optional


class TaskState(BaseModel):
    user_query: str = Field(description="用户原始查询")
    tool_result: Optional[str] = Field(default=None, description="工具调用结果")
    final_answer: Optional[str] = Field(default=None, description="最终回答")

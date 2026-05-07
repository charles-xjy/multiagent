import asyncio

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

# 直接从 tool 包导入
from tool import tool_download_image, get_baidu_tools, get_gaode_tools

model = init_chat_model(
    base_url="http://localhost:8001/v1",
    api_key="vllm-no-key",
    model="Qwen_agent",
    model_provider="openai",
)

system_prompt = """你是一个专业的地理空间情报分析助手。
你的任务是根据用户的需求，通过调用不同的工具获取地理信息、下载卫星遥感影像并进行对比分析。

### 工作流指南：
1. **地点定位**：当用户提到一个地标时，首先调用高德或百度地图工具获取该地点的精确经纬度（lon, lat）。
2. **影像获取**：获取坐标后，调用 `tool_download_image` 工具。你需要根据用户要求的年份（如 2015 和 2025）传入对应的年份列表、经纬度以及地点名称。
3. **路径记忆**：下载成功后，`tool_download_image` 会返回文件的本地路径（path）。请务必记住这些路径。
4. **分析报告**：
   - 确认影像已成功下载。
   - 告知用户影像存储的具体位置。
   - 基于影像获取的情况（以及你已有的地理知识），对该地区在不同年份的变化（如建筑增加、绿化变化、规模扩张）进行初步描述和对比。

### 注意事项：
- 在调用下载工具前，必须确保已经拿到了准确的经纬度。
- 如果用户没有指定具体的年份，默认对比近 10 年的变化。
- 请以专业、严谨的口吻回复。
"""


# 2. 定义统一的异步函数
async def get_all_tools():
    """汇总所有静态工具和动态 MCP 工具，返回一个扁平的列表"""
    # 静态工具（已经是对象了，直接放进列表）
    static_tools = [tool_download_image]

    # 动态工具（因为是异步获取，必须使用 await）
    # 这样拿到的才是真正的 [tool1, tool2...] 列表
    gaode = await get_gaode_tools()
    baidu = await get_baidu_tools()

    # 合并成一个扁平的列表返回
    return static_tools + gaode + baidu


tools = asyncio.run(get_all_tools())

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt
)

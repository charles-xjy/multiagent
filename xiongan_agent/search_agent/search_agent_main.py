from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import RedisSaver

# 直接从 tool 包导入
from tool import duckduckgo_search, langgraph_fetch_web_content, export_webpage_to_pdf, pdf2md

model = init_chat_model(
    base_url="http://localhost:8001/v1",
    api_key="vllm-no-key",
    model="Qwen_agent",
    model_provider="openai",
)

system_prompt = """你是一个深度信息调研助手。
当用户提出一个需要详细了解的主题时，请严格执行以下三阶段流程：

1. **搜索阶段**：调用 `duckduckgo_search` 获取相关网址列表。

2. **抓取与深度解析阶段**：
   - 优先尝试：针对前 1-2 个最具代表性的 URL，调用 `langgraph_fetch_web_content` 抓取正文。
   - **容错逻辑（关键）**：如果上述工具报错（如无法获取 HTML、页面跳转中、或内容为空），请立即执行以下备选方案：
     a. 调用 `export_webpage_to_pdf` 将该网页保存为本地 PDF。
     b. 获取 PDF 存储路径后，调用 `pdf2md` 将其转换为 Markdown 文本。

3. **分析阶段**：
   - 整合所有获取到的详细内容（无论是直接抓取的还是通过 PDF 转换的）。
   - 进行对比、整合，输出一份结构清晰、详实且专业的报告。

注意：
- 严禁仅根据搜索摘要（Snippet）回答。
- 必须确保至少有一个 URL 的深度内容（Markdown/正文）被成功获取。
- 若网页具有复杂的排版或公式，优先使用 PDF 转 MD 路径以保证信息还原度。"""
tools = [duckduckgo_search, langgraph_fetch_web_content, export_webpage_to_pdf, pdf2md]
# tools = [duckduckgo_search, export_webpage_to_pdf, pdf2md]

DB_URI = "redis://localhost:6379"
with RedisSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )


def main():
    config = {
        "configurable": {
            "thread_id": "search_agent"
        }
    }
    inputs = {"messages": [HumanMessage(content="请介绍故宫午门")]}
    for chunk in agent.stream(
            inputs,
            config, stream_mode="updates",
            version="v2",
    ):
        if chunk["type"] == "updates":
            for node_name, node_update in chunk["data"].items():
                if "messages" in node_update:
                    for msg in node_update["messages"]:
                        print(f"\n--- 节点 [{node_name}] 输出 ---")
                        msg.pretty_print()


if __name__ == "__main__":
    main()
    # 查看记忆内容
    from langgraph.checkpoint.redis import RedisSaver

    connection_str = "redis://localhost:6379"

    with RedisSaver.from_conn_string(connection_str) as checkpointer:
        config = {"configurable": {"thread_id": "search_agent"}}
        print(f"--- 正在查询 Thread ID: search_agent 的所有 Checkpoints ---")

        # 使用 list() 获取所有快照
        for state in checkpointer.list(config):
            checkpoint_id = state.config['configurable']['checkpoint_id']
            print(f"\n[Checkpoint ID]: {checkpoint_id}")
            print(f"[metadata]: {state.metadata}")

            # 核心修正：处理可能为 dict 格式的消息
            raw_messages = state.checkpoint.get("channel_values", {}).get("messages", [])

            for msg in raw_messages:
                # 兼容处理：如果是字典则取键值，如果是对象则取属性
                if isinstance(msg, dict):
                    # LangGraph 存储的 dict 通常包含 'type' 和 'data'
                    m_type = msg.get("type", "unknown")
                    # 尝试从嵌套的 data 中获取 content，或者直接获取
                    data = msg.get("data", {})
                    content = data.get("content", str(msg))
                else:
                    m_type = getattr(msg, "type", "unknown")
                    content = getattr(msg, "content", "")

                # 截断过长的内容方便阅读
                display_content = content
                print(f"  - [{m_type}]: {display_content}")

            print("-" * 50)

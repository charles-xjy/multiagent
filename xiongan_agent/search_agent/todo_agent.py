from langchain.chat_models import init_chat_model

model = init_chat_model(
    base_url="http://localhost:8001/v1",
    api_key="vllm-no-key",
    model="Qwen_agent",
    model_provider="openai",
)

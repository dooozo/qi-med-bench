"""
最小可运行的 OpenRouter 调用示例（基于 openai 官方 Python SDK）。

用法：
  1) 确保安装依赖：pip install openai
  2) 直接运行：python openrouter_minimal.py

注意：为方便演示，此处将 API Key "写死" 在代码中。请将占位符替换为你自己的 Key。
"""

from openai import OpenAI


# 将此处替换为你的真实 OpenRouter Key（不要提交到版本库）
API_KEY = "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"

# OpenRouter 的 OpenAI 兼容 Base URL
BASE_URL = "https://openrouter.ai/api/v1"

# ALL_MODELS = [
#     "anthropic/claude-sonnet-4",
#     "anthropic/claude-3.7-sonnet", 
#     "anthropic/claude-opus-4.1",
#     "google/gemini-2.5-flash",
#     "google/gemini-2.5-pro",
#     "moonshotai/kimi-k2-0905",
#     "openai/gpt-4.1",
#     "x-ai/grok-code-fast-1",
#     "deepseek/deepseek-chat-v3-0324",
#     "qwen/qwen3-30b-a3b",
#     "openai/gpt-oss-120b",
#     "z-ai/glm-4.5"
# ]
# 模型可根据自身实际权限调整
MODEL = "google/gemini-2.5-pro"


def main() -> None:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用中文回答：给我讲个简短的冷笑话。"},
    ]

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
        )

        content = resp.choices[0].message.content if resp.choices else "(no content)"
        print("=== 模型回复 ===")
        print(content)

    except Exception as e:
        # 当 Key 无效或网络异常时，会在此处输出错误信息
        print("调用失败：", repr(e))


if __name__ == "__main__":
    main()



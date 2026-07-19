""" LLM 模型设置

统一入口：修改下方 llm = ... 即可切换大模型，所有 agents 自动使用。
API 密钥从项目根目录 `.env` 读取（可先复制 `.env.example` 为 `.env`；勿提交含密钥的 `.env`）。
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载项目根目录的 .env（llm.py 在 ai/setting/ 下，向上两级到项目根目录）
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# 不走系统环境变量里的 HTTP(S)_PROXY，避免本地代理未开或返回 403 时 LLM 请求静默失败。
_HTTP_TIMEOUT = httpx.Timeout(120.0, connect=30.0)
_HTTP_SYNC = httpx.Client(trust_env=False, timeout=_HTTP_TIMEOUT)
_HTTP_ASYNC = httpx.AsyncClient(trust_env=False, timeout=_HTTP_TIMEOUT)


def _build_chat_model(*, model: str, base_url: str, api_key: str) -> ChatOpenAI:
    """统一创建 ChatOpenAI，并关闭 thinking，避免 tool-calling 协议冲突。
    
    注意：部分模型（如 Moonshot、ECNU）对 temperature 有限制，
    这里不设置 temperature，使用模型默认值。
    """
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        http_client=_HTTP_SYNC,
        http_async_client=_HTTP_ASYNC,
        # 兼容不同服务商字段，尽量确保关闭 thinking
        extra_body={"enable_thinking": False, "thinking": {"type": "disabled"}},
    )

class LLM_ecnu_plus:
    def __init__(self):
        self.model = _build_chat_model(
            model="ecnu-plus",
            api_key=os.getenv("ECNU_API_KEY", ""),
            base_url="https://chat.ecnu.edu.cn/open/api/v1",
        )

class LLM_ecnu_max:
    def __init__(self):
        self.model = _build_chat_model(
            model="ecnu-max",
            api_key=os.getenv("ECNU_API_KEY", ""),
            base_url="https://chat.ecnu.edu.cn/open/api/v1",
        )

class LLM_deepseek:
    def __init__(self):
        self.model = _build_chat_model(
            model="deepseek-v4-flash",
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url="https://api.deepseek.com",
        )

class LLM_siliconflow_deepseek:
    def __init__(self):
        self.model = _build_chat_model(
            model="deepseek-ai/DeepSeek-V3.2",
            api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            base_url="https://api.siliconflow.cn/v1",
        )


class LLM_moonshot_kimi:
    def __init__(self):
        # Moonshot 的 kimi-k2.6 模型只支持 temperature=1
        self.model = ChatOpenAI(
            model="kimi-k2.6",
            base_url="https://api.moonshot.cn/v1",
            api_key=os.getenv("MOONSHOT_API_KEY", ""),
            http_client=_HTTP_SYNC,
            http_async_client=_HTTP_ASYNC,
            temperature=1,
            extra_body={"enable_thinking": False},
        )

class LLM_siliconflow_qwen:
    def __init__(self):
        self.model = _build_chat_model(
            model="Qwen/Qwen3.5-4B",
            api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            base_url="https://api.siliconflow.cn/v1",
        )

class LLM_siliconflow_vision:
    def __init__(self):
        self.model = _build_chat_model(
            model="zai-org/GLM-4.6V",
            api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            base_url="https://api.siliconflow.cn/v1",
        )

class LLM_siliconflow_minimax:
    def __init__(self):
        self.model = _build_chat_model(
            model="Pro/MiniMaxAI/MiniMax-M2.5",
            api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            base_url="https://api.siliconflow.cn/v1",
        )

# 统一入口：切换模型只需修改此行（如 LLM_moonshot()）
llm = LLM_deepseek()
# llm = LLM_ecnu_max() # 需在 .env 中配置 ECNU_API_KEY
# llm = LLM_moonshot_kimi() # 需在 .env 中配置 MOONSHOT_API_KEY
# llm = LLM_siliconflow_minimax()
# llm = LLM_siliconflow_deepseek()

# 课后报告 llm
report_llm = LLM_deepseek()
# report_llm = LLM_ecnu_max()

# 多模态 / 视觉：PPT 配图解析等（需在 .env 配置 MOONSHOT_API_KEY）
vlm = LLM_moonshot_kimi()
"""LLM 统一调用客户端 - 基于 HTTP 请求，支持多种大模型API

参考 history-helper 项目的调用逻辑：
- 统一使用 HTTP 请求 + Bearer 认证
- 智谱 API 路径后缀 /v4，OpenAI/DeepSeek 后缀 /v1
- 正确处理思考模型(GLM-5/DeepSeek-Reasoner)的 reasoning_content 字段
- 不依赖任何第三方 SDK，仅使用标准库 httpx/requests
"""

import json
import logging
from typing import Optional

import httpx

from patsona.config import get_settings

logger = logging.getLogger(__name__)

# 各服务商默认配置
PROVIDER_DEFAULTS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas",
        "api_path_suffix": "/v4",  # 智谱用 /v4
        "default_model": "glm-4-flash",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_path_suffix": "/v1",  # DeepSeek 用 /v1
        "default_model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "api_path_suffix": "/v1",  # OpenAI 用 /v1
        "default_model": "gpt-4o-mini",
    },
}

# 思考模型列表（这些模型的推理过程在 reasoning_content 中，content 可能为空）
THINKING_MODELS = {
    "glm-5", "glm-5.1", "glm-5-turbo",
    "deepseek-reasoner",
}


def _is_thinking_model(model: str) -> bool:
    """判断是否为思考模型"""
    model_lower = model.lower()
    return any(t in model_lower for t in THINKING_MODELS)


def _build_url(base_url: str, provider: str) -> str:
    """构建 API URL，自动追加路径后缀

    智谱用 /v4，OpenAI/DeepSeek 用 /v1
    """
    base = base_url.rstrip("/")
    suffix = PROVIDER_DEFAULTS[provider]["api_path_suffix"]
    if not base.endswith(suffix):
        base += suffix
    return f"{base}/chat/completions"


def _strip_model_prefix(model: str) -> str:
    """去掉模型名前缀（如 zhipu/glm-4-flash -> glm-4-flash）"""
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def _get_provider_from_model(model: str) -> str:
    """根据模型名判断服务商"""
    if model.startswith("zhipu/") or "glm" in model.lower():
        return "zhipu"
    elif model.startswith("deepseek/") or "deepseek" in model.lower():
        return "deepseek"
    else:
        return "openai"


def _get_api_key(settings, provider: str) -> str:
    """获取对应服务商的 API Key"""
    key = ""
    if provider == "zhipu":
        key = settings.zhipu_api_key or ""
    elif provider == "deepseek":
        key = settings.deepseek_api_key or ""
    else:
        key = settings.openai_api_key or ""
    return key.strip()


def _get_base_url(settings, provider: str) -> str:
    """获取对应服务商的 Base URL"""
    if provider == "zhipu":
        return PROVIDER_DEFAULTS["zhipu"]["base_url"]
    elif provider == "deepseek":
        return PROVIDER_DEFAULTS["deepseek"]["base_url"]
    else:
        return settings.openai_api_base or PROVIDER_DEFAULTS["openai"]["base_url"]


def _build_request_body(
    model: str,
    messages: list[dict],
    provider: str,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    stream: bool = False,
) -> dict:
    """构建请求体

    根据参考项目 history-helper 的逻辑：
    - 智谱：不支持 thinking/response_format/stream_options，只传基础参数
    - DeepSeek：支持 thinking/stream_options/response_format
    - OpenAI：支持 response_format
    """
    is_thinking = _is_thinking_model(model)

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens if not is_thinking else max(4096, max_tokens),
        "stream": stream,
    }

    if provider == "deepseek":
        # DeepSeek 推理模式不传 temperature
        if is_thinking:
            body["thinking"] = {"type": "enabled"}
            body["stream_options"] = {"include_usage": True}
        else:
            body["temperature"] = temperature
            body["stream_options"] = {"include_usage": True}
    elif provider == "zhipu":
        # 智谱只传 temperature，不支持其他参数
        body["temperature"] = temperature
    else:
        # OpenAI
        body["temperature"] = temperature

    return body


def _parse_response(response_data: dict, model: str) -> str:
    """解析非流式响应

    正确处理思考模型的 reasoning_content 字段：
    - 思考模型(GLM-5等)：推理过程在 reasoning_content，最终答案在 content
    - 如果 content 为空但有 reasoning_content，返回 reasoning_content
    """
    choices = response_data.get("choices", [])
    if not choices:
        raise RuntimeError(f"API返回无choices: {json.dumps(response_data, ensure_ascii=False)[:300]}")

    choice = choices[0]
    message = choice.get("message", {})
    content = message.get("content", "") or ""
    reasoning_content = message.get("reasoning_content", "") or ""

    finish_reason = choice.get("finish_reason", "")

    # 如果输出被截断，记录警告
    if finish_reason == "length":
        logger.warning(f"模型 {model} 输出被截断(finish_reason=length)，考虑增大 max_tokens")

    # 思考模型：content 可能为空，推理过程在 reasoning_content
    if not content and reasoning_content:
        logger.info(f"思考模型 {model}: content为空，使用reasoning_content(长度={len(reasoning_content)})")
        content = reasoning_content

    return content


def _parse_stream_chunk(line_data: str) -> tuple[str, str, bool]:
    """解析流式 SSE 数据行

    Returns:
        (content, reasoning_content, is_done)
    """
    if not line_data.startswith("data:"):
        return "", "", False

    data = line_data[5:].strip()
    if data == "[DONE]":
        return "", "", True

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return "", "", False

    choices = parsed.get("choices", [])
    if not choices:
        return "", "", False

    delta = choices[0].get("delta", {})
    content = delta.get("content", "") or ""
    reasoning_content = delta.get("reasoning_content", "") or ""

    return content, reasoning_content, False


class LLMClient:
    """LLM 统一调用客户端

    基于 HTTP 请求，支持多种大模型API：
    - OpenAI: /v1/chat/completions
    - DeepSeek: /v1/chat/completions
    - 智谱: /v4/chat/completions

    每次调用时会重新获取配置，支持动态更新API Key。

    Args:
        model_override: 可选的模型覆盖（优先级高于配置文件）
    """

    def __init__(self, model_override: Optional[str] = None) -> None:
        self.model_override = model_override

    def _get_model(self) -> str:
        """获取当前模型名"""
        if self.model_override:
            return self.model_override
        return get_settings().litellm_model

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> str:
        """调用 LLM 进行对话（文本输出）

        Args:
            messages: 消息列表，格式 [{"role": "system/user/assistant", "content": "..."}]
            model: 可选的模型覆盖
            temperature: 生成温度，分类任务建议低温度
            max_tokens: 最大生成 token 数

        Returns:
            LLM 返回的文本内容
        """
        settings = get_settings()
        raw_model = model or self._get_model()
        provider = _get_provider_from_model(raw_model)
        clean_model = _strip_model_prefix(raw_model)
        api_key = _get_api_key(settings, provider)
        base_url = _get_base_url(settings, provider)

        if not api_key:
            raise RuntimeError(f"未配置 {provider} 的 API Key，请在设置中配置")

        url = _build_url(base_url, provider)
        body = _build_request_body(clean_model, messages, provider, temperature, max_tokens, stream=False)

        logger.info(f"LLM调用: provider={provider}, model={clean_model}, url={url}")

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json=body,
                )

            if response.status_code != 200:
                error_text = response.text[:500]
                raise RuntimeError(f"API请求失败 (HTTP {response.status_code}): {error_text}")

            response_data = response.json()
            result = _parse_response(response_data, clean_model)
            logger.info(f"LLM响应成功: 长度={len(result)}")
            return result

        except httpx.TimeoutException:
            raise RuntimeError(f"API请求超时(120s): provider={provider}, model={clean_model}")
        except httpx.ConnectError as e:
            raise RuntimeError(f"API连接失败: {e}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"API调用异常: {type(e).__name__}: {e}")

    def chat_json(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> str:
        """调用 LLM 并要求 JSON 格式输出

        Args:
            messages: 消息列表
            model: 可选的模型覆盖
            max_tokens: 最大生成 token 数

        Returns:
            LLM 返回的原始文本（应包含 JSON）
        """
        # 在最后一条消息中追加 JSON 输出提示
        enhanced_messages = list(messages)
        if enhanced_messages:
            last_msg = enhanced_messages[-1]
            if last_msg["role"] == "user":
                last_msg["content"] += (
                    "\n\n请严格按照以下JSON格式输出，不要输出其他内容：\n"
                    "```json\n{...}\n```"
                )

        return self.chat(enhanced_messages, model, temperature=0.0, max_tokens=max_tokens)

    def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        """流式调用 LLM（生成器）

        Args:
            messages: 消息列表
            model: 可选的模型覆盖
            temperature: 生成温度
            max_tokens: 最大生成 token 数

        Yields:
            每次生成的文本片段
        """
        settings = get_settings()
        raw_model = model or self._get_model()
        provider = _get_provider_from_model(raw_model)
        clean_model = _strip_model_prefix(raw_model)
        api_key = _get_api_key(settings, provider)
        base_url = _get_base_url(settings, provider)

        if not api_key:
            raise RuntimeError(f"未配置 {provider} 的 API Key，请在设置中配置")

        url = _build_url(base_url, provider)
        body = _build_request_body(clean_model, messages, provider, temperature, max_tokens, stream=True)

        logger.info(f"LLM流式调用: provider={provider}, model={clean_model}")

        try:
            with httpx.Client(timeout=180.0) as client:
                with client.stream(
                    "POST",
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json=body,
                ) as response:
                    if response.status_code != 200:
                        error_text = response.text[:500]
                        raise RuntimeError(f"API请求失败 (HTTP {response.status_code}): {error_text}")

                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop() or ""

                        for line in lines:
                            content, reasoning, is_done = _parse_stream_chunk(line.strip())
                            if is_done:
                                return
                            if content:
                                yield content
                            # 思考模型的推理内容也可yield
                            if reasoning:
                                yield reasoning

        except httpx.TimeoutException:
            raise RuntimeError(f"API流式请求超时: provider={provider}, model={clean_model}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"API流式调用异常: {type(e).__name__}: {e}")

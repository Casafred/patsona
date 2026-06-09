"""配置管理API - 管理API Key和模型配置"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加patsona模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from patsona.config import reload_settings, get_settings

router = APIRouter(prefix="/api/config", tags=["config"])

# 项目根目录的.env文件路径
ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"


class ConfigModel(BaseModel):
    """配置模型"""
    provider: str = "openai"  # openai, deepseek, zhipu
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    confidence_threshold: float = 0.6
    keep_existing_key: bool = False  # 为空时保留原Key


class ConfigResponse(BaseModel):
    """配置响应"""
    provider: str
    api_key_masked: str  # 脱敏后的API Key
    api_base: str
    model: str
    confidence_threshold: float


def mask_api_key(key: str) -> str:
    """脱敏API Key"""
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def read_env_config() -> dict:
    """读取.env文件配置"""
    config = {
        "provider": "openai",
        "api_key": "",
        "api_base": "https://api.openai.com",
        "model": "gpt-4o-mini",
        "confidence_threshold": 0.6
    }

    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "LITELLM_MODEL":
                    config["model"] = value
                    # 根据模型推断provider
                    if "deepseek" in value.lower():
                        config["provider"] = "deepseek"
                    elif "glm" in value.lower() or "zhipu" in value.lower():
                        config["provider"] = "zhipu"
                    else:
                        config["provider"] = "openai"
                elif key == "OPENAI_API_KEY":
                    config["api_key"] = value
                elif key == "OPENAI_API_BASE":
                    config["api_base"] = value
                elif key == "DEEPSEEK_API_KEY" and value:
                    config["provider"] = "deepseek"
                    config["api_key"] = value
                elif key == "ZHIPU_API_KEY" and value:
                    config["provider"] = "zhipu"
                    config["api_key"] = value
                elif key == "CONFIDENCE_THRESHOLD":
                    try:
                        config["confidence_threshold"] = float(value)
                    except ValueError:
                        pass

    return config


def write_env_config(config: ConfigModel) -> None:
    """写入.env文件配置"""
    # 读取现有配置
    existing = {}
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip()

    # 更新配置 - 清理所有API Key的首尾空格
    if config.provider == "openai":
        existing["LITELLM_MODEL"] = config.model.strip() or "gpt-4o-mini"
        if config.api_key.strip():
            existing["OPENAI_API_KEY"] = config.api_key.strip()
        elif not config.keep_existing_key:
            existing["OPENAI_API_KEY"] = ""
        # keep_existing_key=True且api_key为空时，保留原Key不动
        if config.api_base:
            existing["OPENAI_API_BASE"] = config.api_base.strip()
        # 清除其他provider的key
        existing.pop("DEEPSEEK_API_KEY", None)
        existing.pop("ZHIPU_API_KEY", None)
    elif config.provider == "deepseek":
        existing["LITELLM_MODEL"] = config.model.strip() or "deepseek/deepseek-chat"
        if config.api_key.strip():
            existing["DEEPSEEK_API_KEY"] = config.api_key.strip()
        elif not config.keep_existing_key:
            existing["DEEPSEEK_API_KEY"] = ""
        existing["OPENAI_API_KEY"] = ""
    elif config.provider == "zhipu":
        existing["LITELLM_MODEL"] = config.model.strip() or "zhipu/glm-4-flash"
        if config.api_key.strip():
            existing["ZHIPU_API_KEY"] = config.api_key.strip()
        elif not config.keep_existing_key:
            existing["ZHIPU_API_KEY"] = ""
        existing["OPENAI_API_KEY"] = ""

    existing["CONFIDENCE_THRESHOLD"] = str(config.confidence_threshold)

    # 写入文件
    lines = ["# LLM API配置"]
    lines.append(f"LITELLM_MODEL={existing.get('LITELLM_MODEL', 'gpt-4o-mini')}")
    lines.append(f"OPENAI_API_KEY={existing.get('OPENAI_API_KEY', '')}")
    lines.append(f"OPENAI_API_BASE={existing.get('OPENAI_API_BASE', 'https://api.openai.com')}")
    lines.append("")
    lines.append("# 备用模型")
    lines.append(f"DEEPSEEK_API_KEY={existing.get('DEEPSEEK_API_KEY', '')}")
    lines.append(f"ZHIPU_API_KEY={existing.get('ZHIPU_API_KEY', '')}")
    lines.append("")
    lines.append("# 分类配置")
    lines.append(f"RULES_DIR=rules")
    lines.append(f"CONFIDENCE_THRESHOLD={existing.get('CONFIDENCE_THRESHOLD', '0.6')}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


@router.get("", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    config = read_env_config()
    return ConfigResponse(
        provider=config["provider"],
        api_key_masked=mask_api_key(config["api_key"]),
        api_base=config["api_base"],
        model=config["model"],
        confidence_threshold=config["confidence_threshold"]
    )


@router.post("")
async def save_config(config: ConfigModel):
    """保存配置到.env文件并立即生效"""
    try:
        # 写入.env文件
        write_env_config(config)
        # 立即重新加载配置，让API Key生效
        reload_settings()
        return {"success": True, "message": "配置已保存并立即生效"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")
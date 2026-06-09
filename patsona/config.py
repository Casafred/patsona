"""配置管理模块 - 使用 pydantic-settings 从环境变量和 .env 文件加载配置"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，自动从 .env 文件和环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM 模型配置
    litellm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com"

    # 备用模型 API Key
    deepseek_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None

    # 分类规则目录（相对于项目根目录）
    rules_dir: str = "rules"

    # 置信度阈值：低于此值将触发 Layer3 细分类
    confidence_threshold: float = 0.6

    @property
    def rules_path(self) -> Path:
        """获取规则目录的绝对路径

        如果 rules_dir 是相对路径，则相对于项目根目录解析
        """
        p = Path(self.rules_dir)
        if p.is_absolute():
            return p
        # 项目根目录：patsona包的父目录
        project_root = Path(__file__).parent.parent
        return (project_root / self.rules_dir).resolve()


# 全局单例
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取当前配置（支持动态重载）"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reload_settings() -> Settings:
    """重新加载配置（从 .env 文件重新读取）"""
    global _settings_instance
    # 清除环境变量缓存，强制重新读取 .env
    _settings_instance = Settings()
    # 同时更新环境变量（让 litellm 能读取到）
    if _settings_instance.openai_api_key:
        os.environ["OPENAI_API_KEY"] = _settings_instance.openai_api_key
    if _settings_instance.openai_api_base:
        os.environ["OPENAI_API_BASE"] = _settings_instance.openai_api_base
    if _settings_instance.deepseek_api_key:
        os.environ["DEEPSEEK_API_KEY"] = _settings_instance.deepseek_api_key
    if _settings_instance.zhipu_api_key:
        os.environ["ZHIPU_API_KEY"] = _settings_instance.zhipu_api_key
    return _settings_instance


# 兼容旧代码的 settings 属性
settings = get_settings()
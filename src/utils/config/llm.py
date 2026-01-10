"""
LLM 配置

管理大语言模型相关配置
"""

from pydantic import Field, field_validator

from .base import BaseConfig


class LLMConfig(BaseConfig):
    """LLM 配置"""

    # API Keys
    deepseek_api_key: str | None = Field(default=None, description="DeepSeek API Key")
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API Key")
    dashscope_api_key: str | None = Field(default=None, description="阿里云 DashScope API Key")
    cerebras_api_key: str | None = Field(default=None, description="Cerebras API Key")

    # LLM 服务配置
    llm_server: str = Field(default="Cerebras:Qwen-3-235B-Instruct", description="LLM 服务选择")

    llm_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM 温度（0.0-2.0，越高越随机）"
    )

    llm_max_tokens: int = Field(default=6000, ge=1, le=32000, description="LLM 最大 tokens")

    llm_top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="LLM Top-p（0.0-1.0）")

    llm_top_k: int = Field(default=64, ge=0, description="LLM Top-k")

    # 文本处理配置
    split_limit: int = Field(default=1000, ge=1, description="文本分段长度（每段文本的最大字符数）")

    async_flag: bool = Field(default=True, description="是否使用异步处理")

    # 摘要生成配置
    summary_llm_server: str = Field(
        default="Cerebras:Qwen-3-235B-Thinking", description="摘要 LLM 服务"
    )

    summary_llm_temperature: float = Field(default=1.0, ge=0.0, le=2.0, description="摘要 LLM 温度")

    summary_llm_max_tokens: int = Field(
        default=8192, ge=1, le=32000, description="摘要 LLM 最大 tokens"
    )

    # 功能开关
    disable_llm_polish: bool = Field(default=False, description="是否禁用 LLM 润色")

    disable_llm_summary: bool = Field(default=False, description="是否禁用 LLM 摘要")

    local_llm_enabled: bool = Field(default=False, description="是否启用本地 LLM")

    # 支持的 LLM 服务列表
    llm_server_supported: list[str] = Field(
        default=[
            "qwen3-plus",
            "qwen3-max",
            "deepseek-chat",
            "deepseek-reasoner",
            "Cerebras:Qwen-3-32B",
            "Cerebras:Qwen-3-235B-Instruct",
            "Cerebras:Qwen-3-235B-Thinking",
            "gemini-2.0-flash",
            "local:Qwen/Qwen2.5-1.5B-Instruct",
        ],
        description="支持的 LLM 服务列表",
    )

    @field_validator("llm_server", "summary_llm_server")
    @classmethod
    def validate_llm_server(cls, v: str) -> str:
        """验证 LLM 服务是否支持"""
        # 注意：这里不能访问 llm_server_supported，因为它可能还未初始化
        # 我们在运行时验证
        return v

    def validate_server_support(self) -> None:
        """验证选择的 LLM 服务是否在支持列表中"""
        if self.llm_server not in self.llm_server_supported:
            raise ValueError(
                f"不支持的 LLM 服务: {self.llm_server}。"
                f"支持的服务: {', '.join(self.llm_server_supported)}"
            )
        if self.summary_llm_server not in self.llm_server_supported:
            raise ValueError(
                f"不支持的摘要 LLM 服务: {self.summary_llm_server}。"
                f"支持的服务: {', '.join(self.llm_server_supported)}"
            )

    def has_valid_api_key(self) -> bool:
        """检查是否至少配置了一个有效的 API Key"""
        return any(
            [
                self.deepseek_api_key,
                self.gemini_api_key,
                self.dashscope_api_key,
                self.cerebras_api_key,
            ]
        )

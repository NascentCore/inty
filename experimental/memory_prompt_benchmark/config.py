# CREATED_BY_AGENT
"""
配置管理模块

读取项目根目录的 config.yaml 配置文件
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class DatabaseConfig:
    """数据库配置"""

    host: str
    port: int
    user: str
    password: str
    db: str

    @property
    def connection_string(self) -> str:
        """生成 PostgreSQL 连接字符串"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass
class AgentConfig:
    """Agent LLM 配置"""

    api_key: str
    base_url: str
    model: str


@dataclass
class BenchmarkConfig:
    """评测配置"""

    database: DatabaseConfig
    agent: AgentConfig
    results_dir: Path
    prompts_dir: Path

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "BenchmarkConfig":
        """从 YAML 文件加载配置"""
        if config_path is None:
            # 默认从项目根目录加载
            config_path = Path(__file__).parent.parent.parent / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        db_config = config_data.get("database", {})
        agent_config = config_data.get("agent", {})

        return cls(
            database=DatabaseConfig(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 5432),
                user=db_config.get("user", "postgres"),
                password=db_config.get("password", ""),
                db=db_config.get("db", "inty"),
            ),
            agent=AgentConfig(
                api_key=agent_config.get("api_key", ""),
                base_url=agent_config.get("base_url", "https://openrouter.ai/api/v1"),
                model=agent_config.get("model", "google/gemini-2.5-flash"),
            ),
            results_dir=Path(__file__).parent / "results",
            prompts_dir=Path(__file__).parent / "prompts",
        )


# 全局配置实例（延迟加载）
_config: Optional[BenchmarkConfig] = None


def get_config() -> BenchmarkConfig:
    """获取配置实例（单例模式）"""
    global _config
    if _config is None:
        _config = BenchmarkConfig.from_yaml()
    return _config


def get_default_memory_prompt() -> str:
    """获取默认的记忆提取提示词"""
    config = get_config()
    prompt_path = config.prompts_dir / "default_memory.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"默认记忆提示词文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")

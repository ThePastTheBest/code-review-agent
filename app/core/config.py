import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_turns: int = 10


class GitLabEnvConfig(BaseModel):
    url: str
    token: str


class GitLabConfig(BaseModel):
    clone_depth: int = 1
    temp_dir: str = "/tmp/code-review"


class ReviewConfig(BaseModel):
    prompt_template: str = "prompt/code_review.md"


class ClaudeEnvConfig(BaseModel):
    api_key: str
    base_url: Optional[str] = "https://api.anthropic.com"


class FeishuEnvConfig(BaseModel):
    app_id: str
    app_secret: str


class FeishuConfig(BaseModel):
    enabled: bool = True


class Settings(BaseModel):
    server: ServerConfig = ServerConfig()
    agent: AgentConfig = AgentConfig()
    gitlab: GitLabConfig = GitLabConfig()
    gitlab_env: GitLabEnvConfig
    claude_env: ClaudeEnvConfig
    review: ReviewConfig = ReviewConfig()
    feishu: FeishuConfig = FeishuConfig()
    feishu_env: FeishuEnvConfig


def load_settings() -> Settings:
    """加载配置"""
    config_path = BASE_DIR / "config" / "config.yaml"

    yaml_config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

    gitlab_env = GitLabEnvConfig(
        url=os.getenv("GITLAB_URL", ""),
        token=os.getenv("GITLAB_TOKEN", ""),
    )

    claude_env = ClaudeEnvConfig(
        api_key=os.getenv("CLAUDE_API_KEY", ""),
        base_url=os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com"),
    )

    # 将 CLAUDE_API_KEY / CLAUDE_BASE_URL 映射为 ANTHROPIC_* 供 claude-agent-sdk 使用
    if claude_env.api_key:
        os.environ["ANTHROPIC_API_KEY"] = claude_env.api_key
    if claude_env.base_url:
        os.environ["ANTHROPIC_BASE_URL"] = claude_env.base_url

    feishu_env = FeishuEnvConfig(
        app_id=os.getenv("FEISHU_APP_ID", ""),
        app_secret=os.getenv("FEISHU_APP_SECRET", ""),
    )

    return Settings(
        server=ServerConfig(**yaml_config.get("server", {})),
        agent=AgentConfig(**yaml_config.get("agent", {})),
        gitlab=GitLabConfig(**yaml_config.get("gitlab", {})),
        gitlab_env=gitlab_env,
        claude_env=claude_env,
        review=ReviewConfig(**yaml_config.get("review", {})),
        feishu=FeishuConfig(**yaml_config.get("feishu", {})),
        feishu_env=feishu_env,
    )


settings = load_settings()

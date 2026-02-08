# Code Review Agent

基于 Claude Agent SDK 的自动化代码审查服务。输入 GitLab 项目和分支信息，自动分析代码差异，生成审查报告，并在 Merge Request 上添加行级评论。

## 功能特性

- **自动代码审查** — 通过 Claude AI 多轮推理，自动分析分支间的代码差异
- **结构化审查报告** — 生成包含风险等级、问题分类、修改建议的结构化结果
- **GitLab 深度集成** — 自动创建/更新 MR，写入审查摘要，对问题代码添加行级评论
- **多维度分析** — 覆盖安全性、Bug、性能、稳定性、可维护性等审查维度
- **分级风险评估** — 按 critical / high / medium / low 四级划分问题严重程度
- **全配置化** — GitLab 地址、API Key、模型参数、Prompt 模板均可配置

## 系统架构

```
用户 / CI 系统
       │
       ▼
┌─────────────────────────────────────┐
│  接口层 — FastAPI                    │
│  POST /api/v1/review  代码审查请求   │
│  GET  /api/v1/health  健康检查       │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  服务层                              │
│  GitLabService · ReviewService      │
│  PromptService                      │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Agent 层 — Claude Agent SDK        │
│  多轮推理 · MCP Tools · 结构化输出   │
└─────────────────────────────────────┘
       │
       ▼
  GitLab API  ·  Claude API
```

## 快速开始

### 环境要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 运行服务 |
| Node.js | 18+ | claude-agent-sdk 运行时依赖 |

### 方式一：一键启动（推荐）

```bash
# 赋予执行权限
chmod +x start.sh

# 启动（自动检测环境、安装依赖、配置检查、启动服务）
./start.sh

# 仅检测环境，不启动服务
./start.sh --check

# 跳过所有确认提示，全自动执行
./start.sh -y
```

脚本会自动完成：环境检测 → 创建虚拟环境 → 安装依赖 → 检查 `.env` 配置 → 启动服务。

### 方式二：手动部署

**1. 创建虚拟环境并安装依赖**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. 配置环境变量**

```bash
cp .env.example .env
```

编辑 `.env`，填入真实值：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `GITLAB_URL` | GitLab 实例地址 | 如 `https://gitlab.company.com` |
| `GITLAB_TOKEN` | GitLab Private Token | GitLab → Settings → Access Tokens（需 `api` 权限） |
| `CLAUDE_API_KEY` | Anthropic API Key | 从 [console.anthropic.com](https://console.anthropic.com) 获取 |
| `CLAUDE_BASE_URL` | API 地址（可选） | 默认 `https://api.anthropic.com` |

> `CLAUDE_API_KEY` 启动时会自动映射为 `ANTHROPIC_API_KEY` 供 SDK 使用。

**3. 启动服务**

```bash
python app/main.py
```

启动后访问 http://localhost:8000/docs 查看 Swagger API 文档。

## 使用方式

### 发起代码审查

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "project": "group/repo",
    "source_branch": "feature-branch",
    "target_branch": "main"
  }'
```

| 参数 | 说明 |
|------|------|
| `project` | GitLab 项目路径，如 `mygroup/myrepo` |
| `source_branch` | 源分支（包含新代码的分支） |
| `target_branch` | 目标分支（合并目标） |

### 审查流程

Agent 会自主完成以下多轮推理：

1. 调用 `get_diff` 获取两个分支间的代码差异
2. 如需更多上下文，调用 `get_file_content` 获取完整文件内容
3. 分析完成后，调用 `submit_review` 提交结构化审查结果
4. 服务层自动创建/更新 MR，写入审查摘要
5. 对 medium 及以上风险的问题添加行级评论

### 审查输出

- **MR 描述** — 包含变更概述、风险评估、测试建议的完整 Markdown 文档
- **行级评论** — 针对具体问题代码行的评论，包含严重程度、分类、描述和修改建议
- **审查决定** — `approve` / `approve-with-comments` / `request-changes`

## 可选配置

业务配置位于 `config/config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8000

agent:
  model: "claude-sonnet-4-20250514"
  max_tokens: 20000
  max_turns: 10

gitlab:
  clone_depth: 1
  temp_dir: "/tmp/code-review"

review:
  prompt_template: "prompt/code_review.md"
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `server.host` | 监听地址 | `0.0.0.0` |
| `server.port` | 监听端口 | `8000` |
| `agent.model` | Claude 模型 | `claude-sonnet-4-20250514` |
| `agent.max_tokens` | 单次响应最大 token 数 | `20000` |
| `agent.max_turns` | Agent 最大推理轮数 | `10` |

## 项目结构

```
pay-agent-codereview/
├── app/                          # 应用主目录
│   ├── main.py                   # FastAPI 应用入口
│   ├── api/                      # 接口层
│   │   ├── router.py             # 路由定义（/review, /health）
│   │   ├── schemas.py            # 请求/响应模型
│   │   └── dependencies.py       # 依赖注入与参数校验
│   ├── service/                  # 服务层
│   │   ├── gitlab_service.py     # GitLab API 交互
│   │   ├── review_service.py     # 审查流程协调
│   │   └── prompt_service.py     # Prompt 模板管理
│   ├── agent/                    # Agent 层
│   │   ├── code_review_agent.py  # Claude Agent 主逻辑
│   │   └── tools.py              # MCP 工具（get_diff, get_file_content, submit_review）
│   ├── core/
│   │   └── config.py             # 配置加载
│   └── models/
│       └── review.py             # 审查结果数据模型
├── config/
│   └── config.yaml               # 业务配置
├── prompt/
│   ├── code_review.md            # 审查 Prompt 模板
│   └── code_review_result_json_schema.md  # 输出 JSON Schema
├── docs/
│   └── design.md                 # 系统设计文档
├── .env.example                  # 环境变量模板
├── requirements.txt              # Python 依赖
├── start.sh                      # 一键启动脚本
└── Readme.md
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 数据校验 | Pydantic v2 |
| GitLab 集成 | python-gitlab |
| AI Agent | claude-agent-sdk |
| 配置管理 | PyYAML + python-dotenv |

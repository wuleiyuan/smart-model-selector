# 🧠 OpenCode Smart Model Selector

[![Version](https://img.shields.io/badge/Version-v2.2.0-blue.svg)](https://github.com/wuleiyuan/opencode-smart-model-selector/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/wuleiyuan/opencode-smart-model-selector?style=social)](https://github.com/wuleiyuan/opencode-smart-model-selector/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/wuleiyuan/opencode-smart-model-selector/main.svg)](https://github.com/wuleiyuan/opencode-smart-model-selector/commits/main)

> 🇨🇳 中文 | [English](./README_EN.md)

#JX|**OpenCode 智能模型调度系统** - 基于任务类型自动选择最优 AI 模型，支持多 Provider 负载均衡、故障自动转移、成本优化。

> 🤖 AI 模型路由 | ⚡ API 负载均衡 | 🛡️ 自动故障转移 | 💰 成本优化 | 🔄 OpenCode/Claude/GPT/Gemini 多模型支持

**关键字**: AI, LLM, Model Router, API Gateway, Load Balancer, Claude, GPT, Gemini, DeepSeek, Qwen, OpenCode, Smart Selector, Token Optimization, API Failover, Multi-Provider

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 **智能路由** | 根据任务类型自动选择最优模型 (Coding/Research/Fast) |
| ⚡ **负载均衡** | 多 API Key 轮询，避免单点限流 |
| 🛡️ **故障转移** | API 故障自动切换，用户无感知 |
| 💰 **成本优化** | 长文本自动降级，免费模型优先 |
| ⏰ **智能 TTL** | 手动指定模型 24h 过期，自动恢复智能模式 |
| 🔄 **热启动** | 测速记忆持久化，重启后无需重新探测网络 |
| 🖥️ **多 Shell 支持** | 支持 Zsh 和 Bash 自动启动 |

## 🚀 快速开始

### 安装

```bash
cd /path/to/smart-model-selector
pip install -r requirements.txt
```

### 配置 API Key

在 `auth.json` 中配置你的 API Key：

```json
{
  "google_api_key": "your-google-api-key",
  "anthropic_api_key": "your-anthropic-key",
  "deepseek_api_key": "your-deepseek-key"
}
```

### 基本使用

```bash
# 🎯 全自动模式 (推荐) - 直接输入任务描述
op 帮我写一个 Python 排序算法
op 分析这段代码的性能问题
op 翻译这段英文到中文

# 📋 手动模式 - 显式指定
op -m              # 研究模式 (Google Gemini Pro)
op -c              # 编程模式 (Claude 3.5/3.7)
op -f              # 极速模式 (免费模型优先)
op -w              # 吞吐模式 (DeepSeek/豆包)
op -cn             # 中文模式 (硅基流动/MiniMax)

#MJ|```

## 🎯 模型优先级说明

| 命令 | 说明 |
|------|------|
| `op set google/gemini-2.0-pro` | 手动指定模型（**优先级最高**），24h 有效 |
| `op 写代码` | 自动分析任务，**优先使用**用户指定的模型（如果未过期） |
| `op -m / -c / -f / -w / -cn` | 手动指定模式，**清除**用户指定的模型 |
| `op auto / reset` | 清除手动指定，恢复智能模式 |

### 优先级规则

```
手动指定 (op set) > 自动分析 (op 写代码) > 手动模式 (op -m) > 智能恢复 (op auto)
```

### 自动清除条件

- **24h 过期**: 手动指定的模型 24 小时后自动失效，恢复智能模式
- **连续失败**: 连续 3 次调用失败后自动清除，恢复智能模式

## 📊 支持的模型

| Provider | 模型 | 特点 |
|----------|------|------|
| Google Gemini | 2.0 Pro / 1.5 Pro | 高性能、长上下文 |
| Anthropic Claude | 3.5/3.7 Sonnet | 编程王者、推理专家 |
| DeepSeek | Chat / Coder | 性价比高、中文优化 |
| SiliconFlow | Qwen/DeepSeek 免费 | 免费额度多 |
| MiniMax | Chat | 中文场景优化 |

## 🏗️ 项目架构

```
smart-model-selector/
├── smart_model_dispatcher.py  # 核心调度引擎
├── model_selector.py           # 任务分析模型选择
├── daemon.py                   # 后台守护进程
├── version.py                  # 版本管理
├── op.sh                      # 命令行工具
```

## 🔗 OpenCode 集成

可以将 smart-model-selector 集成到 OpenCode CLI 作为模型选择器。

### 方式 1: 使用 model-selector.sh（推荐）

1. 复制脚本到 OpenCode 配置目录：
```bash
cp model-selector.sh ~/.opencode/model-selector.sh
chmod +x ~/.opencode/model-selector.sh
```

2. 配置环境变量：
```bash
# 在 .zshrc 或 .bashrc 中添加
export OPENCODE_MODEL_SELECTOR="$HOME/.opencode/model-selector.sh"
```

3. 重启终端后生效

### 方式 2: 直接使用 op 命令

```bash
# 安装
cd smart-model-selector
pip install -r requirements.txt
chmod +x op.sh

# 使用
op 帮我写一个Python排序算法
op set google/gemini-2.0-pro  # 手动指定模型
op auto  # 恢复智能模式
```

### 工作原理

```
OpenCode 调用 model-selector.sh
        ↓
调用 smart-model-selector (Python)
        ↓
成功 → 返回智能选择的模型
失败 → 返回默认模型 (gemini-1.5-flash)
```

## 🌐 API Server (OpenAI 兼容接口)

支持启动本地 API Server，提供 OpenAI 兼容接口，可供 **Openclaw** 等 AI 工具调用。

### 快速开始

```bash
# 安装 Flask 依赖
pip install -r requirements.txt

# 启动 API Server
op api start
# 或
python api_server.py --port 8080
```

### Openclaw 配置

在 Openclaw 中配置使用本服务：

```json
{
  "models": {
    "providers": {
      "smart-selector": {
        "baseUrl": "http://localhost:8080/v1",
        "apiKey": "dummy",
        "api": "openai-completions",
        "models": [
          {
            "id": "auto",
            "name": "Smart Selector"
          }
        ]
      }
    }
  }
}
```

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | 聊天完成 |
| `GET /v1/models` | 获取可用模型 |
| `GET /health` | 健康检查 |

### 使用示例

```bash
# 智能选择模型
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "写一个Python排序算法"}]
  }'

# 指定模型
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [{"role": "user", "content": "写一个Python排序算法"}]
  }'
```

---

## 📈 功能详解

### 智能模型选择

系统会根据任务描述自动分析并选择最优模型：

```python
# 任务分析 -> 模型匹配
"写代码" -> Coding 模式 -> Claude
"分析数据" -> Research 模式 -> Gemini Pro
"翻译" -> Fast 模式 -> 免费模型
```

### 故障处理机制

```
Primary API 故障 → 自动切换 Secondary API
全部故障 → 切换 Emergency Pool (OpenRouter)
限流 429 → 进入冷静期 (10分钟)
```

### 成本优化策略

- 长文本 (>8000 tokens) 自动降级到免费模型
- 免费模型优先使用
#PZ|
## 🔗 配套项目

### Token Monitor - Token 使用监控

企业级 Token 使用监控系统，配套 OpenCode Smart Model Selector 使用。

| 特性 | 说明 |
|------|------|
| 📊 实时监控 | 追踪 Token 消耗，支持多模型对比 |
| 🏢 多供应商 | 支持 Google、Anthropic、OpenAI 等 |
| 📈 数据可视化 | 趋势图、饼图等图表展示 |
| ⚠️ 智能告警 | 支持日限额、错误率告警 |

**GitHub**: https://github.com/wuleiyuan/token-monitor

**功能**:
- 实时监控 API 调用量和 Token 消耗
- 多模型对比分析
- 使用趋势图表
- 告警通知
- 支持 Docker 部署

**快速开始**:
```bash
# 克隆项目
git clone https://github.com/wuleiyuan/token-monitor.git
cd token-monitor

# 配置环境
cp .env.template .env

# 启动服务
pip install -r requirements.txt
python enterprise_api_server.py
```

访问 http://localhost:8000，默认账户: `admin` / `admin123`

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

## 📄 License

MIT License - 查看 [LICENSE](LICENSE) 了解详情

---

**⭐ 如果这个项目对你有帮助，请点个 Star 支持一下！**

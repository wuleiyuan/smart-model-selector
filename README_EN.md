JT|# 🧠 Smart Model Selector

[![Version](https://img.shields.io/badge/Version-v4.0.0-blue.svg)](https://github.com/wuleiyuan/smart-model-selector/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/wuleiyuan/smart-model-selector?style=social)](https://github.com/wuleiyuan/smart-model-selector/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/wuleiyuan/smart-model-selector/main.svg)](https://github.com/wuleiyuan/smart-model-selector/commits/main)

> English | [中文](./README.md)

ZB|MW|**Smart Model Selector** - AI model auto-selection tool compatible with OpenCode, OpenClaw, and Cursor. **Supports multiple free API rotation**, no payment required to enjoy the best AI model experience.

## ✨ Core Features

RJ|**Keywords**: AI, LLM, Model Router, API Gateway, Load Balancer, Claude, GPT, Gemini, DeepSeek, Qwen, OpenCode, OpenClaw, Cursor, Smart Selector, Token Optimization, API Failover, Multi-Provider, Model Selection, AI Coding Assistant
|---------|-------------|
NX|| 🤖 **Smart Routing** | Auto-select optimal model based on task type (Coding/Research/Fast) |
KM|| ⚡ **Load Balancing** | Multiple API keys rotation, prevents rate limits |
KV|| 🛡️ **Failover** | Automatic API failover, seamless for users |
NT|| 🆓 **Free API Rotation** | Multiple free APIs smart rotation, auto-select best |
MY|| 💰 **Cost Optimization** | Long text auto-downgrade, free models prioritized |
RP|| ⏱️ **Speed Test** | Latency-based routing, remembers response times |
| ⚡ **Load Balancing** | Multiple API keys rotation, prevents rate limits |
| 🛡️ **Failover** | Automatic API failover, seamless for users |
| 💰 **Cost Optimization** | Long text auto-downgrade, free models prioritized |
| ⏱️ **Speed Test** | Latency-based routing, remembers response times |
| 📊 **Usage Tracking** | Token usage monitoring and statistics |

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/wuleiyuan/smart-model-selector.git
cd smart-model-selector
chmod +x install.sh
./install.sh
```

### Configuration

```bash
# Edit configuration file
vim ~/.local/share/opencode/auth.json

# Or use environment variables
export OPENCODE_ANTHROPIC_KEY=sk-xxx
export OPENCODE_GOOGLE_KEY=AIzaSyxxx
export OPENCODE_DEEPSEEK_KEY=sk-xxx
```

### Usage

```bash
# Auto mode (default)
op 帮我写一个排序算法

# Set specific model (24h validity)
op set google/gemini-2.0-pro

# View current model
op status

# Reset to auto mode
op auto
op reset

# Profile modes
op -m  # Developer mode (Claude Sonnet)
op -c  # Coding mode
op -f  # Fast mode
op -w  # Writing mode
op -cn  # Chinese mode
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `op <task>` | Auto-analyze and select model |
| `op set <model>` | Manually specify model (24h) |
| `op auto/reset` | Reset to auto mode |
| `op status` | Show current status |
| `op version` | Show version |
| `op api start` | Start API Server |
| `op api stop` | Stop API Server |

## 🎯 Model Priority

| Command | Description |
|---------|-------------|
| `op set google/gemini-2.0-pro` | Manual model (**highest priority**), 24h valid |
| `op <task>` | Auto-analyze, **use** user-specified model if not expired |
| `op -m / -c / -f / -w / -cn` | Manual profile mode, **clears** user-specified model |
| `op auto / reset` | Clear manual spec, restore smart mode |

### Priority Rules

```
Manual Spec (op set) > Auto Analyze > Manual Mode > Smart Reset
```

### Auto-Clear Conditions

- **24h Expiry**: Manual spec expires after 24 hours
- **3 Failures**: Auto-clears after 3 consecutive failures

SH|## 🆓 Supported Free Models

| Provider | Models | Features | Price |
|----------|--------|----------|-------|
| Google Gemini | 2.0 Flash | High performance, multimodal | 🆓 Free |
| DeepSeek | Chat | Strong coding ability | 🆓 Free |
| SiliconFlow | Qwen/DeepSeek | Free credits | 🆓 Free |
| MiniMax | Chat | Chinese optimization | 🆓 Free |

## 💎 Premium Models (Optional)

| Provider | Models | Features |
|----------|--------|----------|
| Anthropic Claude | 3.5/3.7 Sonnet | Coding king, reasoning expert |
| OpenAI | GPT-4o | Balanced |
| Google Gemini | 2.0 Pro | High performance, long context |

| Provider | Models | Features |
|----------|--------|----------|
| Google Gemini | 2.0 Pro / 1.5 Pro | High performance, long context |
| Anthropic Claude | 3.5/3.7 Sonnet | Coding king, reasoning expert |
| DeepSeek | Chat / Coder | Cost-effective, Chinese optimized |
| SiliconFlow | Qwen/DeepSeek Free | Free credits |
| MiniMax | Chat | Chinese optimization |

## 🌐 API Server (OpenAI Compatible)

Start a local API server with OpenAI-compatible interface, for use with **Openclaw** and other AI tools.

```bash
# Install dependencies
pip install -r requirements.txt

# Start API Server
op api start
# or
python api_server.py --port 8080
```

### Openclaw Configuration

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

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat completion |
| `GET /v1/models` | List available models |
| `GET /health` | Health check |

## 🔗 Related Projects

### Token Monitor - Token Usage Monitoring

Enterprise-grade Token usage monitoring system, designed to work with OpenCode Smart Model Selector.

| Feature | Description |
|---------|-------------|
| 📊 Real-time Monitoring | Track Token usage, multi-model comparison |
| 🏢 Multi-Provider | Google, Anthropic, OpenAI support |
| 📈 Visualization | Trend charts, pie charts |
| ⚠️ Alerts | Daily limits, error rate alerts |

**GitHub**: https://github.com/wuleiyuan/token-monitor

## 🏗️ Project Structure

```
smart-model-selector/
├── smart_model_dispatcher.py  # Core dispatch engine
├── model_selector.py           # Task analysis & model selection
├── api_server.py              # API Server (OpenAI compatible)
├── daemon.py                  # Background daemon
├── version.py                 # Version management
├── op.sh                      # CLI tool
├── auto_start.sh              # Auto-start script
├── api_config.json            # API config template
└── README.md                  # Documentation
```

## 📈 Feature Details

### Smart Model Selection

Analyzes task description and selects optimal model:

- **Coding**: Claude 3.5/3.7 Sonnet
- **Research**: Gemini 2.0 Pro
- **Fast**: Gemini 1.5 Flash / Free models

### Load Balancing

- Automatically rotates between multiple API keys
- Response time based selection
- Remembers historical latency

### Cost Optimization

- Long text (>8000 tokens) auto-downgrade to free models
- Free models prioritized
- Task complexity based model selection

## 🤝 Contributing

Welcome to submit Issues and PRs!

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

⭐ If this project helps you, please give it a Star!

# 🧠 Smart Model Selector

> **智能模型路由 · 双引擎驱动 · 故障自动转移**
> 兼容 OpenCode / OpenClaw，让你的 AI 助手始终调用最合适的模型

[![Version](https://img.shields.io/badge/Version-v5.0.0-blue.svg)](https://github.com/wuleiyuan/smart-model-selector/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ 30 秒快速开始

```bash
# 1. 一键安装
curl -sSL https://raw.githubusercontent.com/wuleiyuan/smart-model-selector/main/install.sh | bash

# 2. 填入你的 API Keys
nano ~/.opencode/keys.json

# 3. 查看状态
python3 selector_core.py --status

# 4. 启动服务
python3 api_server.py
```

---

## 🧠 它是如何工作的？

```
┌─────────────────────────────────────────────────────────────┐
│                        用户输入                              │
│                   "帮我写一个 Python 爬虫"                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    🧠 智慧大脑                               │
│              selector_core.py (意图分析)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  关键词检测 → 路由决策                                │   │
│  │  "代码" → Gemini 3.1 Pro                            │   │
│  │  "润色" → MiniMax M2.7                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   💪 执行肌肉                               │
│         smart_model_dispatcher.py (动态调度)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  故障转移 | 负载均衡 | 流式输出                        │   │
│  │  Google ❌ → 自动切换 → MiniMax ✅                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 模型路由策略

| 场景 | 关键词 | 路由模型 |
|------|--------|----------|
| 🐍 **编程开发** | 代码、Python、Java、Bug、算法 | `Gemini 3.1 Pro` |
| ✍️ **中文创作** | 润色、文章、小说、剧本、翻译 | `MiniMax M2.7` |
| ❓ **日常问答** | (默认) | `Gemini 3.1 Pro` |

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **智能路由** | 根据任务关键词自动选择最优模型 |
| 🔄 **故障转移** | API 故障自动切换，用户无感知 |
| ⚡ **流式输出** | 实时流式返回，像打字机一样丝滑 |
| 📊 **P0 协议** | 大输出自动分流，防止上下文过载 |
| 🛡️ **自愈能力** | 独立健康监控，发现异常立即告警 |

---

## 🚀 快速开始

### 安装方式一：一键安装（推荐）

```bash
curl -sSL https://raw.githubusercontent.com/wuleiyuan/smart-model-selector/main/install.sh | bash
```

### 安装方式二：手动安装

```bash
git clone https://github.com/wuleiyuan/smart-model-selector.git
cd smart-model-selector
./install.sh
```

### 配置 API Keys

复制模板并填入你的 Keys：

```bash
cp keys.example.json keys.json
nano keys.json
```

```json
{
  "google_paid": ["YOUR_GOOGLE_API_KEY"],
  "google_free": ["YOUR_GOOGLE_FREE_API_KEY"],
  "minimax_paid": ["YOUR_MINIMAX_API_KEY"]
}
```

### 启动服务

```bash
# 查看系统状态
python3 selector_core.py --status

# 启动 API 服务
python3 api_server.py

# 测试路由
python3 selector_core.py "帮我写一个 Python 排序算法"
```

---

## 📁 项目架构

```
smart-model-selector/
├── 🧠 selector_core.py          # 智慧大脑 - 意图分析 + 路由决策
├── 💪 smart_model_dispatcher.py  # 执行肌肉 - 动态调度 + 故障转移
├── 🌐 api_server.py              # API 网关 - OpenAI 兼容接口
├── 📋 output_protocol.py         # P0 协议 - 大输出自动分流
├── ⚙️  lobster_sentinel.py       # 龙虾侍卫 - 健康监控（可选）
├── 📜 keys.example.json          # 配置模板（脱敏）
├── 📖 README.md                  # 本文档
└── 🔧 install.sh                 # 一键安装脚本
```

---

## 🔧 高级配置

### P0 输出避让协议

当输出超过 4KB 时，自动分流到 `/tmp/smart_selector_outputs/`

```python
from output_protocol import OutputProtocol

protocol = OutputProtocol()
result = protocol.handle(large_content)

if result["evaded"]:
    print(f"📁 内容已保存至: {result['save_path']}")
```

### 龙虾侍卫健康监控

```bash
# 启动监控（每15秒检测一次）
python3 lobster_sentinel.py

# 查看日志
tail -f ~/.openclaw/logs/health.log
```

---

## 🎨 设计原则

| 原则 | 说明 |
|------|------|
| **核心极简** | 每个模块只做一件事，做到极致 |
| **插件解耦** | 路由规则可扩展，方便添加新模型 |
| **自愈能力强** | 故障自动转移，无需人工干预 |

---

## 📖 文档

- [English](./README_EN.md)
- [版本历史](./version.py)

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

**⭐ 如果这个项目对你有帮助，请点个 Star 支持一下！**

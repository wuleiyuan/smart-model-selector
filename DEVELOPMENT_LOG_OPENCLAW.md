# OpenClaw Auto Model Selector 开发记录

## 项目概述

为 OpenClaw 设计的独立自动模型选择模块。

**功能**：
- 根据任务类型自动选择最优模型
- 混合策略：任务匹配 + 性能驱动自动切换
- 性能监控：记录延迟和成功率
- 支持 OpenClaw Gateway API

**当前版本**: v1.0.0

---

## 模块架构

### 文件结构

```
opencode-smart-model-selector/
├── openclaw_selector.py     # 独立模块 (NEW)
├── model_selector.py        # 原智能选择器
├── smart_model_dispatcher.py # 调度器
├── api_server.py            # API 服务器
└── dual_engine.py          # 双引擎
```

### 核心类

| 类名 | 功能 |
|------|------|
| `ModelInfo` | 模型信息数据结构 |
| `PerformanceTracker` | 性能监控 - 延迟/成功率/冷却期 |
| `OpenClawModelSelector` | 主选择器 - 混合策略 |

---

## 技术设计

### 模型定义

支持 10+ 模型，覆盖主流 AI Provider：

| Provider | 模型 | 特点 |
|----------|------|------|
| Anthropic | Claude Opus 4.6, Sonnet 4.5, Haiku 3.5 | 研究/编程/快速 |
| Google | Gemini 2.0 Pro, Flash | 多模态/快速 |
| OpenAI | GPT-4o, GPT-4o Mini | 编程/均衡 |
| DeepSeek | DeepSeek Chat | 编程/便宜 |
| Qwen | Qwen 2.5 Coder 32B | 编程/免费 |
| OpenCode | MiniMax 2.5 (Free) | 免费/快速 |

### 任务类型识别

| 任务类型 | 关键词 | 推荐模型 |
|----------|--------|----------|
| coding | code, 编程, debug, 函数 | Claude Sonnet, GPT-4o |
| research | 分析, 研究, 调研 | Claude Opus, Gemini Pro |
| writing | 写, 创作, 翻译 | Claude Haiku, GPT-4o |
| fast | 快速, 简单 | MiniMax Free, Gemini Flash |
| multimodal | 图片, 图像 | Gemini Pro |

### 混合策略

```
1. 任务分析 → 确定任务类型
2. 候选筛选 → 按任务匹配候选模型
3. 性能排序 → 按延迟/成功率排序
4. 最佳选择 → 选择最优模型
```

### 性能监控

- **缓存文件**: `~/.config/openclaw/model_performance.json`
- **监控指标**: 平均延迟、成功率、最后使用时间
- **冷却机制**: 失败率 >50% 自动进入冷却期

---

## 使用方法

### 基本用法

```bash
# 选择模型
python3 openclaw_selector.py "帮我写一个排序算法"

# JSON 输出
python3 openclaw_selector.py "分析代码" --json

# 列出所有模型
python3 openclaw_selector.py --list

# 显示性能统计
python3 openclaw_selector.py --stats
```

### OpenClaw 集成

将模块路径配置到 OpenClaw：

```bash
# 或在 OpenClaw 配置中指定模型选择器
export OPENCODE_MODEL_SELECTOR="/path/to/openclaw_selector.py"
```

---

## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 1.0.0 | 2026-02-27 | 初始版本 - 任务类型分析 + 性能监控 |

---

## 已知问题

- 暂无 OpenClaw 深度集成示例
- 流式响应待实现

---

## 参考资料

- [OpenClaw 官网](https://openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw Model Failover](https://docs.openclaw.ai/concepts/model-failover)

---

*最后更新: 2026-02-27*

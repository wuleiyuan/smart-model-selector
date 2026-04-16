# 我做了一个 AI 模型路由器，每月省了 60% 的 API 成本

**标题**: I Built a Smart AI Model Router That Saved Me $200/Month on API Costs

---

## 🔥 背景

我用 AI 写代码已经一年多了，但每个月收到账单时都很肉疼。

Claude Code 很好，但 $200/月 的订阅让我犹豫。Gemini 便宜但中文理解差。DeepSeek 便宜但时不时挂掉。MiniMax 中文好但只能在国内用。

于是我想：**能不能做一个"智能路由器"，让 AI 助手根据任务类型自动选择最合适的模型？**

---

## 💡 核心想法

```
任务类型          →    自动路由到
─────────────────────────────────────
写代码 / Debug    →    DeepSeek Coder (便宜 + 准)
中文润色 / 写作   →    MiniMax M2.7 (最懂中文)
复杂推理 / 分析   →    Claude / GPT-4o (贵但强)
日常问答 / 搜索   →    Gemini (免费额度大)
```

同时，如果某个 API 挂了，**自动无缝切换**到备用模型，用户完全无感知。

---

## 🏗️ 架构

```
用户输入: "帮我写一个 Python 爬虫"
        ↓
   🧠 智慧大脑 (selector_core)
        ↓
   关键词检测: "代码" → 路由到 DeepSeek
        ↓
   💪 执行肌肉 (dispatcher)
        ↓
   DeepSeek ❌ (限流)
        ↓
   自动切换 → Gemini ✅
```

---

## ⚡ 核心代码

```python
# 路由决策 (selector_core.py)
def select(self, task_text: str):
    task_text = task_text.lower()

    # 代码场景 → DeepSeek
    if any(k in task_text for k in ['代码', 'python', 'bug', 'java', '算法']):
        if self.inventory.get("deepseek", 0) > 0:
            return "deepseek", "代码场景 → DeepSeek Coder"

    # 中文写作 → MiniMax
    if any(k in task_text for k in ['润色', '写封信', '文章', '翻译']):
        if self.inventory.get("minimax", 0) > 0:
            return "minimax", "中文创作 → MiniMax M2.7"

    # 默认 → Gemini
    return "gemini-3.1-pro-preview", "默认 → Gemini"
```

```python
# 故障转移 (dispatcher.py)
for api_key in sorted_keys:
    try:
        yield from self._stream(api_key, messages)
        return  # 成功，退出
    except Exception as e:
        logger.warning(f"⚠️ {provider} 节点熔断，切换到备用...")
        continue  # 自动切换到下一个 Key
```

---

## 📊 效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 月度 API 成本 | $200 | $80 |
| API 故障次数 | 手动切换 10+ 次/月 | **0 次**（自动切换）|
| 路由延迟 | N/A | < 10ms |
| 支持模型数 | 1 个 | **15+ 个** |

---

## 🚀 一键安装

```bash
# 克隆项目
git clone https://github.com/wuleiyuan/smart-model-selector.git
cd smart-model-selector

# 一键安装
./install.sh

# 配置你的 API Keys
cp keys.example.json keys.json
nano keys.json

# 启动服务
python3 api_server.py
```

或者用 Docker：

```bash
docker-compose up -d
```

---

## 🆚 竞品对比

| 特性 | Smart Model Selector | LiteLLM | PortKey |
|------|---------------------|---------|---------|
| 故障自动转移 | ✅ 零配置 | ❌ 需手动 | ✅ 需付费 |
| 关键词路由 | ✅ 开箱即用 | ❌ 不支持 | ❌ 不支持 |
| 零外部依赖 | ✅ 纯 Python | ❌ 需 Redis | ❌ 需云服务 |
| 部署复杂度 | ⭐ 极简 | ⭐⭐⭐ 复杂 | ⭐⭐ 中等 |

---

## 🎯 适用场景

1. **个人开发者** - 不想为 Claude Code 付 $200/月
2. **小型团队** - 需要在多个模型间平衡成本和效果
3. **AI 工具开发者** - 需要给 AI 助手加故障转移能力
4. **OpenCode / OpenClaw 用户** - 想要更智能的模型选择

---

## 🤔 局限

- 目前主要针对中文场景优化
- 需要一定的配置能力（填 API Keys）
- 路由策略基于关键词，未来可以加 LLM 意图识别

---

## 🔗 项目地址

**GitHub**: https://github.com/wuleiyuan/smart-model-selector
**Star**: 如果对你有帮助，请点个 ⭐

---

*你在用 AI 写代码时遇到过什么问题？欢迎评论区聊聊！*

WZ|# Smart Model Selector 开发记录

## 项目概述

NW|智能模型选择系统 - 兼容 OpenCode/OpenClaw，支持多个免费 API 智能轮换，无需付费即可享受最优 AI 模型体验。

**当前版本**: v4.0.0

---

## 两个项目目录的用途

| 目录 | 用途 |
|------|------|
| `/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector/` | **本地自用工作目录** - 保留隐私配置 (api_config.json 含密钥) |
| `/Users/leiyuanwu/GitHub/smart-model-selector/` | **GitHub 同步目录** - 干净环境开发测试，验证后同步 |

### 工作流程 (重要)

```
GitHub 目录 (干净环境开发测试)
    ↓
开发、测试、验证
    ↓
同时同步到：
    ├── 本地工作目录 (保留隐私配置)
    └── GitHub 仓库 (公开发布)
```

**核心原则**：
- GitHub 目录是测试验证环境
- 验证通过后再同步两边
- 本地工作目录保留隐私信息
- 出问题可从本地工作目录回滚

XM|---

## V1.1 配置驱动架构 (2026-03-02)

### 变更内容

| 文件 | 功能 | 行数 |
|------|------|------|
| `models_config.json` | 模型配置文件 (JSON) | 160 |
| `selector_core.py` | 支持从配置文件动态加载模型 | 421 |

### 功能说明

- **零代码添加模型**: 只需编辑 `models_config.json` 即可添加新模型
- **向后兼容**: 配置文件加载失败时自动回退到硬编码默认模型
- **新能力标签**: 添加 `PREMIUM` 能力标签

### 配置字段说明

```json
{
  "models": {
    "model-id": {
      "id": "model-id",
      "name": "显示名称",
      "provider": "提供商",
      "capabilities": ["coding", "fast", "cheap"],
      "context_window": 128000,
      "cost_per_1k_input": 0.0,
      "cost_per_1k_output": 0.0,
      "latency_tier": "fast",
      "enabled": true,
      "priority": 100,
      "tags": ["free", "fast"]
    }
  }
}
```

---

## V3.0.0 通用架构升级 (2026-03-01)

### 新增模块

| 模块 | 功能 | 行数 |
|------|------|------|
| `selector_core.py` | 核心逻辑 (任务分析 + 模型路由 + 性能监控) | 373 |
| `base_adapter.py` | 抽象基类 (定义标准接口) | 263 |
| `adapter_opencode.py` | OpenCode 适配器 | 230 |
| `adapter_openclaw.py` | OpenClaw 适配器 | 306 |
| `selector_factory.py` | 工厂类 (动态实例化) | 233 |

### 架构

```
selector_core.py (核心层)
        │
    ┌───┴───┐
    ↓       ↓
adapter_   adapter_
opencode  openclaw
```

### SEO 优化

- 项目更名为 "Smart Model Selector"
- 强调免费 API 轮换功能
- 支持 OpenCode/OpenClaw/Cursor 多平台

---

## 本次开发内容 (2026-02-27 第二次修复)

HR|## 本次开发内容 (2026-02-27 第二次修复)

### 审计问题修复

根据代码审计报告，修复以下问题：

#### 1. 测速缓存 Bug 修复 (高优先级)

| 文件 | 问题 | 修复 |
|------|------|------|
| `smart_model_dispatcher.py` | `_load_cache` 方法缺少历史数据赋值，导致热启动失效 | 添加 `self._history = data.get("history", {})` |

#### 2. 流式响应支持 (高优先级)

| 文件 | 问题 | 修复 |
|------|------|------|
| `api_server.py` | Streaming 请求返回 400 错误 | 实现 `_stream_response` 方法，支持 OpenAI SSE 协议 |

#### 3. Gunicorn 启动说明 (中优先级)

| 文件 | 问题 | 修复 |
|------|------|------|
| `README.md` | 缺少生产环境启动说明 | 添加 `gunicorn -w 4 -k gevent` 启动命令 |

---

## 历史开发内容 (2026-02-27 第一次)

### 1. 测试验证

- **Python 语法检查**: 所有核心文件语法正确
- **模块导入测试**: version, dual_engine, api_server 均可正常导入
- **功能运行测试**: DualEngineManager 初始化成功
- **注意**: 项目没有单元测试文件

### 2. 代码审查 (逐字逐句)

发现并修复 **1 个 bug**:

| 文件 | 行号 | 问题 | 修复 |
|------|------|------|------|
| `dual_engine.py` | 183 | `failure_count_count` → 拼写错误 | 改为 `failure_count` |
| `dual_engine.py` | 115 | 注释误导 | "优先使用原生引擎" → "优先使用自定义引擎" |

### 3. 文档完善

**README.md 更新**:
- 新增 3 个核心特性:
  - 🔀 双引擎冗余
  - ⚡ 熔断降级
  - 📡 API Server
- 新增 `op engine custom / native` 命令说明

**README_EN.md 更新**:
- 新增英文版核心特性说明

### 4. GitHub Release

- 创建 v2.2.0 Release
- 修复 Release 未发布问题

### 1. 测试验证

- **Python 语法检查**: 所有核心文件语法正确
- **模块导入测试**: version, dual_engine, api_server 均可正常导入
- **功能运行测试**: DualEngineManager 初始化成功
- **注意**: 项目没有单元测试文件

### 2. 代码审查 (逐字逐句)

发现并修复 **1 个 bug**:

| 文件 | 行号 | 问题 | 修复 |
|------|------|------|------|
| `dual_engine.py` | 183 | `failure_count_count` → 拼写错误 | 改为 `failure_count` |
| `dual_engine.py` | 115 | 注释误导 | "优先使用原生引擎" → "优先使用自定义引擎" |

### 3. 文档完善

**README.md 更新**:
- 新增 3 个核心特性:
  - 🔀 双引擎冗余
  - ⚡ 熔断降级
  - 📡 API Server
- 新增 `op engine custom / native` 命令说明

**README_EN.md 更新**:
- 新增英文版核心特性说明

### 4. GitHub Release

- 创建 v2.2.0 Release
- 修复 Release 未发布问题

---

## Git 操作记录

### 本次提交

| Commit | 描述 |
|--------|------|
| `fae693a` | docs: 添加开发记录 DEVELOPMENT_LOG.md |
| `bce5f3a` | docs: 更新 README - 修复格式 |
| `2963e0c` | fix: 修复 dual_engine.py 拼写错误 + 更新 README 文档 |
| `49b9222` | release: v2.2.0 - 双引擎架构 + 熔断降级 + 并发优化 |

### 同步命令

```bash
# 同时同步到本地目录 + 推送到 GitHub
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.egg-info' --exclude='dist' --exclude='api_config.json' /Users/leiyuanwu/GitHub/smart-model-selector/ /Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector/

cd /Users/leiyuanwu/GitHub/smart-model-selector && git push origin main
```

---

## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 1.0.0 | 2025-01-01 | 初始版本 - 智能模型选择 + 故障转移 |
| 2.0.0 | 2025-02-25 | 重大更新: 手动指定模型 > 自动推荐优先级, 24h TTL, 连续3次失败自动切换, op auto/reset 命令, 长文本降级策略, 测速记忆持久化 |
| 2.1.0 | 2026-02-26 | 新增功能: API Server 模块 (OpenAI 兼容接口), op api 命令 |
MV|| 2.2.0 | 2026-02-27 | 新增功能: 双引擎架构, 熔断降级, 并发优化, 测速缓存4h过期, op engine 命令 |
MX|| 2.2.1 | 2026-02-27 | Bug修复: 测速缓存热启动, 流式响应支持, Gunicorn启动说明 |

---

## 已知问题

- 暂无单元测试文件
- 网络不稳定时 GitHub 推送可能失败

---

## 常用命令

```bash
# 进入 GitHub 目录
cd /Users/leiyuanwu/GitHub/smart-model-selector

# 进入本地工作目录
cd /Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector

# 测试模块导入
python3 -c "from dual_engine import DualEngineManager; print(DualEngineManager().get_status())"

# 查看版本
python3 version.py
```
```

---

## 版本更新流程

每次发布新版本时，按以下步骤操作：

### 1. 更新版本号

```bash
# 更新 version.py
# 修改 __version__ = "X.X.X"
# 添加 VERSION_HISTORY 条目

# 更新 pyproject.toml
# version = "X.X.X"

# 更新 README.md / README_EN.md
[![Version](https://img.shields.io/badge/Version-vX.X.X-blue.svg)]
```

### 2. 提交代码

```bash
cd /Users/leiyuanwu/GitHub/smart-model-selector

git add -A
git commit -m "release: vX.X.X - 版本描述"
```

### 3. 创建 GitHub Release

```bash
# 创建 tag
git tag -a vX.X.X -m "vX.X.X - 版本描述"

# 推送到远程
git push origin main
git push origin vX.X.X

# 创建 GitHub Release
gh release create vX.X.X \
  --title "vX.X.X - 版本标题" \
  --notes "## vX.X.X\n\n### 新增功能\n- ...\n\n### 修复\n- ..."
```

### 4. 同步到本地

```bash
rsync -av --exclude='.git' --exclude='__pycache__' \
  --exclude='*.egg-info' --exclude='dist' \
  --exclude='api_config.json' \
  /Users/leiyuanwu/GitHub/smart-model-selector/ \
  /Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector/
```

### 5. 更新 DEVELOPMENT_LOG.md

```markdown
## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| X.X.X | YYYY-MM-DD | 版本描述 |
```

---

*最后更新: 2026-03-02*
---

WY|*最后更新: 2026-02-27*

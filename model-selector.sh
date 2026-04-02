#!/bin/bash
# OpenCode Model Selector - Smart Selector with Fallback
# 优先级: smart-model-selector → OpenCode 默认
# 
# 使用方式:
# 1. 复制到 ~/.opencode/model-selector.sh
# 2. 配置环境变量: export OPENCODE_MODEL_SELECTOR="$HOME/.opencode/model-selector.sh"
# 3. 重启终端

# 获取脚本所在目录（支持软链接）
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_SOURCE" ]; do
    SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
    SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
    [[ $SCRIPT_SOURCE != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"

# 默认模型（fallback）- 使用最通用的 gemini-3.1-pro-preview
DEFAULT_MODEL="gemini-3.1-pro-preview"

# 获取任务描述
TASK="$*"

# 尝试使用智能调度器
if [ -f "$SCRIPT_DIR/model_selector.py" ]; then
    RESULT=$(cd "$SCRIPT_DIR" && python3 -c "
import sys
sys.path.insert(0, '.')
from model_selector import SmartModelSelector
try:
    selector = SmartModelSelector()
    model, reason = selector.select('''$TASK''')
    print(model.id)
except Exception as e:
    pass
" 2>/dev/null)
    
    if [ -n "$RESULT" ]; then
        echo "$RESULT"
        exit 0
    fi
fi

# Fallback
echo "$DEFAULT_MODEL"

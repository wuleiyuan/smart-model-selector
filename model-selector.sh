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

# 默认模型（fallback）
DEFAULT_MODEL="gemini-3.1-pro-preview"

# 获取任务描述
TASK="$*"

# 尝试使用智能调度器
if [ -f "$SCRIPT_DIR/model_selector.py" ]; then
    # 直接调用 Python 脚本，提取 model 字段
    RESULT=$(python3 "$SCRIPT_DIR/model_selector.py" "$TASK" 2>/dev/null)
    
    if [ -n "$RESULT" ]; then
        # 尝试解析 JSON，提取 model 字段
        MODEL=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('model', ''))
except:
    # 如果不是 JSON，直接输出原始内容（可能是纯 model ID）
    print(sys.stdin.read().strip())
" 2>/dev/null)
        
        if [ -n "$MODEL" ] && [ "$MODEL" != "$RESULT" ]; then
            # 成功从 JSON 中提取了 model 字段
            echo "$MODEL"
            exit 0
        elif [ -n "$RESULT" ] && [ "$RESULT" != "${RESULT//\{/}" ]; then
            # 结果仍是 JSON 但无法解析 model，尝试提取第一个引号内的内容
            MODEL=$(echo "$RESULT" | grep -o '"[^"]*"' | head -1 | tr -d '"')
            if [ -n "$MODEL" ]; then
                echo "$MODEL"
                exit 0
            fi
        elif [ -n "$RESULT" ]; then
            # 可能是纯文本（直接是模型ID）
            echo "$RESULT"
            exit 0
        fi
    fi
fi

# Fallback
echo "$DEFAULT_MODEL"
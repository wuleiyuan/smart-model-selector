#!/bin/bash
# =============================================================================
# 🧠 Smart Model Selector - 一键安装脚本 (Apple Style)
# =============================================================================
# curl -sSL https://raw.githubusercontent.com/wuleiyuan/smart-model-selector/main/install.sh | bash
# =============================================================================

set -e

# 色彩定义 (Apple Style)
BOLD='\033[1m'
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
MAGENTA=$'\033[0;35m'
CYAN=$'\033[0;36m'
WHITE=$'\033[1;37m'
NC=$'\033[0m'

# Emoji
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${CYAN}→${NC}"
ROCKET="${MAGENTA}🚀${NC}"
GEAR="${YELLOW}⚙️${NC}"

# Banner
echo ""
echo -e "${BOLD}${WHITE}███╗   ███╗ ██████╗ ███╗   ██╗██╗   ██╗██╗  ██╗██╗   ██╗███╗   ███╗${NC}"
echo -e "${BOLD}${WHITE}████╗ ████║██╔═══██╗████╗  ██║██║   ██║╚██╗ ██╔╝██║   ██║████╗ ████║${NC}"
echo -e "${BOLD}${WHITE}██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║ ╚████╔╝ ██║   ██║██╔████╔██║${NC}"
echo -e "${BOLD}${WHITE}██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║  ╚██╔╝  ██║   ██║██║╚██╔╝██║${NC}"
echo -e "${BOLD}${WHITE}██║ ╚═╝ ██║╚██████╔╝██║ ╚████║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║${NC}"
echo -e "${BOLD}${WHITE}╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝${NC}"
echo ""
echo -e "${CYAN}Smart Model Selector - 智能模型路由 · 双引擎驱动 · 故障自动转移${NC}"
echo ""

# ---- Step 1: Detect OS ----
echo -e "${GEAR} ${BOLD}检测操作系统...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    echo -e "${CHECK} ${GREEN}检测到 macOS${NC}"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    echo -e "${CHECK} ${GREEN}检测到 Linux${NC}"
else
    echo -e "${CROSS} ${RED}不支持的操作系统: $OSTYPE${NC}"
    exit 1
fi

# ---- Step 2: Detect Python ----
echo ""
echo -e "${GEAR} ${BOLD}检测 Python...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${CROSS} ${RED}未找到 Python，请先安装 Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${CHECK} ${GREEN}Python $PYTHON_VERSION${NC}"

# ---- Step 3: Install Dependencies ----
echo ""
echo -e "${GEAR} ${BOLD}安装依赖...${NC}"

if ! $PYTHON_CMD -c "import flask, requests" 2> /dev/null; then
    echo -e "${YELLOW}安装 Flask 和 Requests...${NC}"
    $PYTHON_CMD -m pip install -q flask requests 2>/dev/null || {
        echo -e "${CROSS} ${RED}依赖安装失败${NC}"
        exit 1
    }
fi
echo -e "${CHECK} ${GREEN}依赖就绪${NC}"

# ---- Step 4: Setup Config ----
echo ""
echo -e "${GEAR} ${BOLD}配置文件...${NC}"

CONFIG_DIR="$HOME/.opencode"
KEYS_FILE="$CONFIG_DIR/keys.json"
mkdir -p "$CONFIG_DIR"

if [ -f "$KEYS_FILE" ]; then
    echo -e "${YELLOW}检测到已有 keys.json${NC}"
else
    if [ -f "keys.example.json" ]; then
        cp keys.example.json "$KEYS_FILE"
        echo -e "${CHECK} ${GREEN}已创建 keys.json (请编辑填入 API Keys)${NC}"
    else
        $PYTHON_CMD -c "import json; json.dump({'google_paid': ['YOUR_KEY'], 'minimax_paid': ['YOUR_KEY']}, open('$KEYS_FILE', 'w'), indent=2)"
        echo -e "${CHECK} ${GREEN}已创建 keys.json${NC}"
    fi
fi

# ---- Step 5: Sync to ~/.opencode ----
echo ""
echo -e "${GEAR} ${BOLD}同步到 ~/.opencode...${NC}"

if [ -d ".git" ]; then
    echo -e "${YELLOW}开发模式，跳过同步${NC}"
else
    cp -r . "$CONFIG_DIR/" 2>/dev/null || true
fi
echo -e "${CHECK} ${GREEN}配置目录: $CONFIG_DIR${NC}"

# ---- Done ----
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${ROCKET} ${BOLD}${GREEN}安装完成！${NC}"
echo ""
echo -e "${WHITE}快速开始:${NC}"
echo -e "  ${CYAN}cd $CONFIG_DIR${NC}"
echo -e "  ${CYAN}python3 selector_core.py --status${NC}     # 查看状态"
echo -e "  ${CYAN}python3 api_server.py${NC}                # 启动 API 服务"
echo ""
echo -e "${WHITE}文档:${NC}"
echo -e "  ${CYAN}cat README.md${NC}                         # 查看完整文档"
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

#!/usr/bin/env bash
# ==============================================================================
# Script cai dat rieng phan Quy tac (Rules & Context Monitor) cho macOS & Linux
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}>>> Bat dau cai dat Goi Quy tac (Rules Only) cho $(uname -s)...${NC}"

USER_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 0. Kiem tra moi truong
echo -e "\n${YELLOW}--- 1. Kiem tra moi truong thuc thi ---${NC}"
if command -v node >/dev/null 2>&1; then
    echo -e " [x] Node.js: $(node -v) ${GREEN}(San sang)${NC}"
else
    echo -e " [!] ${RED}Chua tim thay Node.js. Vui long cai dat Node.js truoc!${NC}"
fi

# 1. Cai dat thu muc Global ~/.gemini
echo -e "\n${YELLOW}--- 2. Cai dat Global Rules va Enforce Script ---${NC}"
GEMINI_DIR="$USER_HOME/.gemini"
GEMINI_CONFIG_DIR="$GEMINI_DIR/config"
GEMINI_SCRIPTS_DIR="$GEMINI_DIR/scripts"

mkdir -p "$GEMINI_CONFIG_DIR"
mkdir -p "$GEMINI_SCRIPTS_DIR"

# Sao chep GEMINI.md
if [ -f "$SCRIPT_DIR/global/GEMINI.md" ]; then
    cp -f "$SCRIPT_DIR/global/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
    echo -e " [x] Da cap nhat Global Rules: ${GREEN}$GEMINI_DIR/GEMINI.md${NC}"
fi

# Sao chep enforce_rules.js
if [ -f "$SCRIPT_DIR/global/scripts/enforce_rules.js" ]; then
    cp -f "$SCRIPT_DIR/global/scripts/enforce_rules.js" "$GEMINI_SCRIPTS_DIR/enforce_rules.js"
    chmod +x "$GEMINI_SCRIPTS_DIR/enforce_rules.js" 2>/dev/null || true
    echo -e " [x] Da cai dat script kiem soat: ${GREEN}$GEMINI_SCRIPTS_DIR/enforce_rules.js${NC}"
fi

# 2. Cai dat Extension Context Monitor
echo -e "\n${YELLOW}--- 3. Cai dat Tien ich Giam sat Ngu canh ---${NC}"
TARGET_DIRS=()

if [ -d "$USER_HOME/.antigravity-ide" ]; then
    TARGET_DIRS+=("$USER_HOME/.antigravity-ide/extensions")
fi

if [ -d "$USER_HOME/.vscode" ]; then
    TARGET_DIRS+=("$USER_HOME/.vscode/extensions")
fi

if [ ${#TARGET_DIRS[@]} -eq 0 ]; then
    TARGET_DIRS+=("$USER_HOME/.antigravity-ide/extensions")
fi

for TARGET in "${TARGET_DIRS[@]}"; do
    mkdir -p "$TARGET"
    CONTEXT_DEST="$TARGET/antigravity-context-monitor-1.0.0"
    mkdir -p "$CONTEXT_DEST"
    if [ -d "$SCRIPT_DIR/extensions/antigravity-context-monitor" ]; then
        cp -rf "$SCRIPT_DIR/extensions/antigravity-context-monitor/"* "$CONTEXT_DEST/"
        echo -e " [x] Da cai dat extension Context Monitor vao: ${GREEN}$TARGET${NC}"
    fi
done

echo -e "\n${GREEN}>>> Chuc mung! Cai dat thanh cong Goi Quy tac (Rules Only).${NC}"
echo -e "${YELLOW}>>> Khoi dong lai IDE de ap dung cac quy chuan moi.${NC}\n"

#!/usr/bin/env bash
# ==============================================================================
# Script cai dat tu dong Antigravity Suite cho macOS & Linux
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}>>> Bat dau cai dat Antigravity Suite cho $(uname -s)...${NC}"

USER_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 0. Kiem tra moi truong
echo -e "\n${YELLOW}--- 1. Kiem tra moi truong thuc thi ---${NC}"
if command -v node >/dev/null 2>&1; then
    echo -e " [x] Node.js: $(node -v) ${GREEN}(San sang)${NC}"
else
    echo -e " [!] ${RED}Chua tim thay Node.js. Vui long cai dat Node.js truoc (brew install node)!${NC}"
fi

PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
fi

if [ -n "$PY_CMD" ]; then
    echo -e " [x] Python: $($PY_CMD --version) ${GREEN}(San sang)${NC}"
else
    echo -e " [!] ${YELLOW}Chua tim thay Python (de phat giong doc AI, vui long cai: brew install python)${NC}"
fi

# 1. Cai dat thu muc Global ~/.gemini
echo -e "\n${YELLOW}--- 2. Cai dat Global Rules va Hooks ---${NC}"
GEMINI_DIR="$USER_HOME/.gemini"
GEMINI_CONFIG_DIR="$GEMINI_DIR/config"
GEMINI_SCRIPTS_DIR="$GEMINI_DIR/scripts"

mkdir -p "$GEMINI_CONFIG_DIR"
mkdir -p "$GEMINI_SCRIPTS_DIR"

# Sao chep GEMINI.md
cp -f "$SCRIPT_DIR/global/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
echo -e " [x] Da cap nhat Global Rules: ${GREEN}$GEMINI_DIR/GEMINI.md${NC}"

# Sao chep scripts
cp -rf "$SCRIPT_DIR/global/scripts/"* "$GEMINI_SCRIPTS_DIR/"
chmod +x "$GEMINI_SCRIPTS_DIR"/*.js 2>/dev/null || true
echo -e " [x] Da cai dat cac script bo tro: ${GREEN}$GEMINI_SCRIPTS_DIR${NC}"

# Cau hinh hooks.json voi duong dan thuc te tren Mac/Linux
HOOKS_SRC="$SCRIPT_DIR/global/config/hooks.json"
HOOKS_DEST="$GEMINI_CONFIG_DIR/hooks.json"

sed "s|C:/Users/[^/]*/\.gemini|$USER_HOME/.gemini|g" "$HOOKS_SRC" > "$HOOKS_DEST"
echo -e " [x] Da cau hinh Hooks tu dong hoa: ${GREEN}$HOOKS_DEST${NC}"

# 2. Cai dat Extensions
echo -e "\n${YELLOW}--- 3. Cai dat cac tien ich mo rong (Extensions) ---${NC}"
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

    # Antigravity Voice Selector
    VOICE_DEST="$TARGET/antigravity-voice-selector-1.0.0"
    mkdir -p "$VOICE_DEST"
    cp -rf "$SCRIPT_DIR/extensions/antigravity-voice-selector/"* "$VOICE_DEST/"

    # Antigravity Context Monitor
    CONTEXT_DEST="$TARGET/antigravity-context-monitor-1.0.0"
    mkdir -p "$CONTEXT_DEST"
    cp -rf "$SCRIPT_DIR/extensions/antigravity-context-monitor/"* "$CONTEXT_DEST/"

    echo -e " [x] Da cai dat 2 extension vao: ${GREEN}$TARGET${NC}"
done

echo -e "\n${GREEN}>>> Chuc mung! Cai dat thanh cong toan bo Antigravity Suite.${NC}"
echo -e "${YELLOW}>>> Khoi dong lai IDE de kich hoat toan dien cac tinh nang moi.${NC}\n"

#!/usr/bin/env bash
# ==============================================================================
# Script cai dat rieng phan Giong doc (Voice Daemon & Selector) cho macOS & Linux
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}>>> Bat dau cai dat Goi Giong doc (Voice Only) cho $(uname -s)...${NC}"

USER_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 0. Kiem tra moi truong
echo -e "\n${YELLOW}--- 1. Kiem tra moi truong thuc thi ---${NC}"
PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
fi

if [ -n "$PY_CMD" ]; then
    echo -e " [x] Python: $($PY_CMD --version) ${GREEN}(San sang)${NC}"
else
    echo -e " [!] ${RED}Chua tim thay Python. Vui long cai dat Python truoc!${NC}"
fi

# 1. Cai dat thu muc Global ~/.gemini
echo -e "\n${YELLOW}--- 2. Cai dat Voice Daemon va Notification Scripts ---${NC}"
GEMINI_DIR="$USER_HOME/.gemini"
GEMINI_CONFIG_DIR="$GEMINI_DIR/config"
GEMINI_SCRIPTS_DIR="$GEMINI_DIR/scripts"

mkdir -p "$GEMINI_CONFIG_DIR"
mkdir -p "$GEMINI_SCRIPTS_DIR"

# Sao chep voice scripts
if [ -f "$SCRIPT_DIR/global/scripts/voice_daemon.py" ]; then
    cp -f "$SCRIPT_DIR/global/scripts/voice_daemon.py" "$GEMINI_SCRIPTS_DIR/voice_daemon.py"
    echo -e " [x] Da cai dat dich vu: ${GREEN}$GEMINI_SCRIPTS_DIR/voice_daemon.py${NC}"
fi

if [ -f "$SCRIPT_DIR/global/scripts/voice_notify.py" ]; then
    cp -f "$SCRIPT_DIR/global/scripts/voice_notify.py" "$GEMINI_SCRIPTS_DIR/voice_notify.py"
    echo -e " [x] Da cai dat kich hoat am thanh: ${GREEN}$GEMINI_SCRIPTS_DIR/voice_notify.py${NC}"
fi

# Cau hinh hooks.json
HOOKS_SRC="$SCRIPT_DIR/global/config/hooks.json"
HOOKS_DEST="$GEMINI_CONFIG_DIR/hooks.json"
if [ -f "$HOOKS_SRC" ]; then
    sed "s|C:/Users/[^/]*/\.gemini|$USER_HOME/.gemini|g" "$HOOKS_SRC" > "$HOOKS_DEST"
    echo -e " [x] Da cau hinh Hooks tu dong hoa: ${GREEN}$HOOKS_DEST${NC}"
fi

# 2. Cai dat Extension Voice Selector
echo -e "\n${YELLOW}--- 3. Cai dat Tien ich Chon Giong doc ---${NC}"
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
    VOICE_DEST="$TARGET/antigravity-voice-selector-1.0.0"
    mkdir -p "$VOICE_DEST"
    if [ -d "$SCRIPT_DIR/extensions/antigravity-voice-selector" ]; then
        cp -rf "$SCRIPT_DIR/extensions/antigravity-voice-selector/"* "$VOICE_DEST/"
        echo -e " [x] Da cai dat extension Voice Selector vao: ${GREEN}$TARGET${NC}"
    fi
done

echo -e "\n${GREEN}>>> Chuc mung! Cai dat thanh cong Goi Giong doc (Voice Only).${NC}"
echo -e "${YELLOW}>>> Khoi dong lai IDE de kich hoat toan dien cac tinh nang moi.${NC}\n"

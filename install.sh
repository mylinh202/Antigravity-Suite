#!/usr/bin/env bash
# ==============================================================================
# Script cai dat tong hop Antigravity Suite (Ho tro phan tach module)
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TYPE="$1"

run_all() {
    echo -e "\n${CYAN}>>> Dang thuc hien cai dat TOAN BO Antigravity Suite...${NC}"
    bash "$SCRIPT_DIR/install_rules.sh"
    sleep 0.3
    bash "$SCRIPT_DIR/install_voice.sh"
}

run_rules() {
    bash "$SCRIPT_DIR/install_rules.sh"
}

run_voice() {
    bash "$SCRIPT_DIR/install_voice.sh"
}

if [ "$TYPE" = "All" ] || [ "$TYPE" = "all" ] || [ "$TYPE" = "-all" ]; then
    run_all
    exit 0
elif [ "$TYPE" = "Rules" ] || [ "$TYPE" = "rules" ] || [ "$TYPE" = "-rules" ]; then
    run_rules
    exit 0
elif [ "$TYPE" = "Voice" ] || [ "$TYPE" = "voice" ] || [ "$TYPE" = "-voice" ]; then
    run_voice
    exit 0
fi

# Menu tuong tac
clear 2>/dev/null || true
echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW}         ANTIGRAVITY SUITE - BO CAI DAT MO-DUN HOA          ${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e " Vui long chon goi cai dat ban mong muon:\n"
echo -e "  ${GREEN}[1] Cai dat TOAN BO (Quy tac + Giong doc AI + Tien ich)${NC}"
echo -e "  ${CYAN}[2] Chi cai dat QUY TAC (Global Rules + Context Monitor)${NC}"
echo -e "  ${MAGENTA}[3] Chi cai dat GIONG DOC (Voice Daemon + Selector)${NC}"
echo -e "  [0] Thoat cai dat\n"
echo -e "${CYAN}============================================================${NC}"

read -p "Nhap lua chon cua ban [1/2/3/0] (Mac dinh: 1): " choice

if [ -z "$choice" ] || [ "$choice" = "1" ]; then
    run_all
elif [ "$choice" = "2" ]; then
    run_rules
elif [ "$choice" = "3" ]; then
    run_voice
elif [ "$choice" = "0" ]; then
    echo -e "${YELLOW}Da huy cai dat.${NC}"
    exit 0
else
    echo -e "${YELLOW}Lua chon khong hop le. Dang tien hanh cai dat toan bo theo mac dinh...${NC}"
    run_all
fi

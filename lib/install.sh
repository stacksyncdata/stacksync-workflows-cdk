#!/usr/bin/env bash
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf '%s\n' "$CYAN"
cat <<'EOF'
      _             _                                   _ _    
     | |           | |                                 | | |   
  ___| |_ __ _  ___| | _____ _   _ _ __   ___    ___ __| | | __
 / __| __/ _` |/ __| |/ / __| | | | '_ \ / __|  / __/ _` | |/ /
 \__ \ || (_| | (__|   <\__ \ |_| | | | | (__  | (_| (_| |   < 
 |___/\__\__,_|\___|_|\_\___/\__, |_| |_|\___|  \___\__,_|_|\_\
                              __/ |                            
                             |___/                             
EOF
printf '%s\n' "$RESET"
echo

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "${RED}❌ ERROR:${RESET} No virtualenv detected." >&2
  echo "${YELLOW}   Fix:${RESET} activate one first, e.g.:" >&2
  echo "        ${YELLOW}python3 -m venv .venv${RESET}" >&2
  echo "        ${YELLOW}source .venv/bin/activate${RESET}" >&2
  exit 1
fi

venv_python="$VIRTUAL_ENV/bin/python"
if [[ ! -x "$venv_python" ]]; then
  echo "${RED}❌ ERROR:${RESET} Expected venv python at: $venv_python" >&2
  exit 1
fi

echo "${YELLOW}${BOLD}WARNING:${RESET} ${YELLOW}You are installing a local editable copy of stacksync-cdk for development only.${RESET}" >&2
echo "${YELLOW}The intended way to use this package is to install it from GitHub via:${RESET}" >&2
echo
echo "${CYAN}  pip install \"git+https://github.com/stacksyncdata/stacksync-workflows-cdk.git@prod#subdirectory=lib\"${RESET}" >&2
echo
echo "${GREEN}If your intent is to contribute to the stacksync_cdk package and you need a local installation for this purpose, you may ignore this warning.${RESET}" >&2
echo >&2

"$venv_python" -m pip install -U pip
(
  cd "$script_dir"
  "$venv_python" -m pip install -e . > /dev/null
)

echo "${GREEN}🚀 Installed${RESET} editable stacksync-cdk into venv: $VIRTUAL_ENV"
echo "${GREEN}   Import:${RESET} ${CYAN}from stacksync_cdk import create_app, Request, SchemaResponse${RESET}"

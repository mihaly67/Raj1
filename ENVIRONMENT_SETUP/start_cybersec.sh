#!/bin/bash
# Wrapper script for launching CyberSec Dashboard inside X11 sessions (e.g. from .desktop files)
export DISPLAY=:0
export XAUTHORITY=$HOME/.Xauthority

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/../jules_venv/bin/python"
APP_SCRIPT="$SCRIPT_DIR/../SecurityCenter_dev/security_dashboard.py"

# Fallback paths if deployed directly to home dir
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$HOME/jules_venv/bin/python"
fi
if [ ! -f "$APP_SCRIPT" ]; then
    APP_SCRIPT="$HOME/SecurityCenter_dev/security_dashboard.py"
fi

$VENV_PYTHON $APP_SCRIPT "$@"

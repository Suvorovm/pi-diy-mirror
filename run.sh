#!/bin/bash
# run.sh — запускает Python-скрипты через venv с правами sudo.
#
# Зачем это нужно:
#   GPIO требует root-доступа, поэтому нужен sudo.
#   Но sudo сбрасывает переменные окружения и не видит активированный venv.
#   Решение: передаём sudo полный путь к интерпретатору внутри venv.
#
# Использование:
#   ./run.sh main.py              — запустить основное приложение
#   ./run.sh test_hardware.py     — запустить тест железа
#   ./run.sh <любой_скрипт.py>   — любой другой скрипт

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Ошибка: venv не найден по пути $SCRIPT_DIR/.venv"
    echo "Создай его командой: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

sudo "$VENV_PYTHON" "$@"

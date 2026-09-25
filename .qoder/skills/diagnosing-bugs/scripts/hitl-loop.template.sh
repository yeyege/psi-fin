#!/usr/bin/env bash
# Human-in-the-loop reproduction loop.
# Copy this file, edit the steps below, and run it.
# The agent runs the script; the user follows prompts in their terminal.
#
# Usage:
#   bash hitl-loop.template.sh
#
# This repo is developed on Windows and the script is bash-only
# (`set -euo pipefail`, `printf -v`, interactive `read`): run it in Git Bash or
# WSL, in the user's own terminal. The agent's shell cannot answer `read`.
#
# Two helpers:
#   step "<instruction>"          → show instruction, wait for Enter
#   capture VAR "<question>"      → show question, read response into VAR
#
# At the end, captured values are printed as KEY=VALUE for the agent to parse.
#
# `capture` prints its value back to the terminal, where the agent reads it,
# so capture observations, and leave signing in to the user as a `step`.

set -euo pipefail

# 本项目实际端口：vite dev 5173（frontend-vue/vite.config.ts），FastAPI 8000，
# docker compose 下前端 8080。仓库里没有 3000。改地址不要改下面的步骤。
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [Enter when done] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- edit below ---------------------------------------------------------
# 示例：排查「出库单发货后库存流水与账面不一致」。把步骤换成当前 bug 的真实路径。

step "打开 $FRONTEND_URL 并用 admin 登录，进入「出库管理」。"

step "对一张已确认的出库单点「发货」。到 $BACKEND_URL/api/inventory/flows 看一眼刚才的流水。"

capture ERRORED "页面报错了吗？(y/n)"

capture ERROR_MSG "把报错文本或接口返回的 message 粘过来（没有则填 none）："

# --- edit above ---------------------------------------------------------

printf '\n--- Captured ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"

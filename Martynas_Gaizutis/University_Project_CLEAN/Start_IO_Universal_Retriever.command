#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

./launch_rag.command menu

echo ""
read -r -p "Press Enter to close..." _

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export HAYSTACK_TELEMETRY_ENABLED=False

VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
READY_MARKER="$VENV_DIR/.rag3_ready"

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    echo "[RAG] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
  fi
}

install_deps() {
  echo "[RAG] Installing dependencies..."
  "$PIP_BIN" install --upgrade pip >/dev/null
  "$PIP_BIN" install -e ".[ui]" >/dev/null
  touch "$READY_MARKER"
}

ensure_setup() {
  ensure_venv
  if [ ! -x "$PYTHON_BIN" ] || [ ! -f "$READY_MARKER" ]; then
    install_deps
  fi

  if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "[RAG] Created .env from .env.example"
    echo "[RAG] Please edit .env and set OPENAI_API_KEY"
  fi
}

check_openai_key() {
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    return 0
  fi

  if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "[RAG] Missing .env file. Run setup first."
    return 1
  fi

  local key
  key="$(grep -E '^OPENAI_API_KEY=' "$ROOT_DIR/.env" | head -n1 | cut -d'=' -f2- | tr -d '[:space:]' || true)"
  if [ -z "$key" ]; then
    echo "[RAG] OPENAI_API_KEY is empty in .env"
    return 1
  fi
  return 0
}

check_elasticsearch() {
  local host port
  host="$(grep -E '^ELASTICSEARCH_HOST=' "$ROOT_DIR/.env" | head -n1 | cut -d'=' -f2- | tr -d '[:space:]' || true)"
  port="$(grep -E '^ELASTICSEARCH_PORT=' "$ROOT_DIR/.env" | head -n1 | cut -d'=' -f2- | tr -d '[:space:]' || true)"
  host="${host:-localhost}"
  port="${port:-9200}"

  if ! curl --silent --show-error --max-time 3 "http://$host:$port" >/dev/null 2>&1; then
    echo "[RAG] Elasticsearch is not reachable at http://$host:$port"
    echo "[RAG] Start Elasticsearch first, then retry."
    echo "[RAG] Tip: use menu option 6 to start Elasticsearch via Docker."
    return 1
  fi
  return 0
}

run_start_elasticsearch() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[RAG] Docker is not installed. Install Docker Desktop first."
    return 1
  fi

  if docker ps --format '{{.Names}}' | grep -q '^rag3-es$'; then
    echo "[RAG] Elasticsearch container 'rag3-es' is already running."
    return 0
  fi

  if docker ps -a --format '{{.Names}}' | grep -q '^rag3-es$'; then
    echo "[RAG] Starting existing container 'rag3-es'..."
    docker start rag3-es >/dev/null
  else
    echo "[RAG] Creating and starting container 'rag3-es'..."
    docker run -d \
      --name rag3-es \
      -p 9200:9200 \
      -e discovery.type=single-node \
      -e xpack.security.enabled=false \
      docker.elastic.co/elasticsearch/elasticsearch:8.16.0 >/dev/null
  fi

  echo "[RAG] Waiting for Elasticsearch to become healthy..."
  for _ in {1..30}; do
    if curl --silent --show-error --max-time 2 "http://localhost:9200" >/dev/null 2>&1; then
      echo "[RAG] Elasticsearch is up at http://localhost:9200"
      return 0
    fi
    sleep 1
  done

  echo "[RAG] Elasticsearch did not become ready in time."
  return 1
}

run_setup() {
  ensure_setup
  echo "[RAG] Setup complete."
}

run_index() {
  ensure_setup
  if ! check_elasticsearch; then
    return 1
  fi
  "$PYTHON_BIN" rag_pipeline.py index "$@"
}

run_ask() {
  ensure_setup
  if ! check_openai_key; then
    return 1
  fi
  if ! check_elasticsearch; then
    return 1
  fi
  if [ "$#" -eq 0 ]; then
    read -r -p "Enter your question: " q
    "$PYTHON_BIN" rag_pipeline.py ask "$q"
  else
    "$PYTHON_BIN" rag_pipeline.py ask "$*"
  fi
}

run_ui() {
  ensure_setup
  if ! check_openai_key; then
    return 1
  fi
  if ! check_elasticsearch; then
    return 1
  fi
  echo "[RAG] Starting Streamlit UI..."
  "$STREAMLIT_BIN" run ui_module.py
}

show_menu() {
  echo ""
  echo "IO, Universal Retriever Launcher"
  echo "1) Setup"
  echo "2) Index Documents"
  echo "3) Ask Question"
  echo "4) Launch UI"
  echo "5) Start Elasticsearch (Docker)"
  echo "6) Exit"
  echo ""
  read -r -p "Choose (1-6): " choice

  case "$choice" in
    1) run_setup ;;
    2)
      read -r -p "Clear index first? (y/N): " clear_choice
      if [[ "$clear_choice" =~ ^[Yy]$ ]]; then
        run_index --clear
      else
        run_index
      fi
      ;;
    3)
      run_ask
      ;;
    4)
      run_ui
      ;;
    5)
      run_start_elasticsearch
      ;;
    6)
      exit 0
      ;;
    *)
      echo "Invalid choice"
      ;;
  esac
}

case "${1:-menu}" in
  setup)
    shift
    run_setup "$@"
    ;;
  index)
    shift
    run_index "$@"
    ;;
  ask)
    shift
    run_ask "$@"
    ;;
  ui)
    shift
    run_ui "$@"
    ;;
  es)
    shift
    run_start_elasticsearch "$@"
    ;;
  menu)
    show_menu
    ;;
  *)
    echo "Usage: ./launch_rag.command [setup|index|ask|ui|es|menu]"
    exit 1
    ;;
esac

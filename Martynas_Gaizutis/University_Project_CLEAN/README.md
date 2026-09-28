# IO, Universal Retriever (University Project)

This is a business-focused RAG system tailored for GravityX.

Detailed internal documentation is available at `docs/DEVELOPER_DOCUMENTATION.md`.

Fastest launch on macOS: double-click `Start_IO_Universal_Retriever.command`.

## What It Does

- Indexes documents from `TXT`, `PDF`, `DOCX`, and `XLSX` folders.
- Stores embedded documents in Elasticsearch.
- Retrieves relevant context with BM25.
- Generates answers using OpenAI.
- Optionally validates answer quality with a second LLM pass.
- Provides both CLI and Streamlit UI entrypoints.
- Uses a GravityX-oriented response framework (executive summary, evidence, next steps, confidence).

## New Project Structure

- `src/rag3/config.py`: environment-driven application config.
- `src/rag3/document_store.py`: Elasticsearch connection factory.
- `src/rag3/indexing.py`: document loading + embedding + indexing.
- `src/rag3/retrieval.py`: retrieval layer.
- `src/rag3/generation.py`: OpenAI answer generation.
- `src/rag3/validation.py`: answer validation.
- `src/rag3/pipeline.py`: orchestration.
- `src/rag3/cli.py`: command-line interface.
- `src/rag3/ui.py`: Streamlit UI.

Legacy top-level files (`rag_pipeline.py`, `ui_module.py`, etc.) are now compatibility wrappers.

## Setup (macOS)

1. Create virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -e .[ui]
   ```
3. Configure environment:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set `OPENAI_API_KEY` + Elasticsearch values.

If Elasticsearch is not running locally, you can start one quickly with Docker:
```bash
docker run --name rag3-es -p 9200:9200 -e discovery.type=single-node -e xpack.security.enabled=false docker.elastic.co/elasticsearch/elasticsearch:8.16.0
```

## Run

CLI:
```bash
python rag_pipeline.py index --clear
python rag_pipeline.py ask "What are the main aspects of the document?"
```

Package-style CLI after editable install:
```bash
rag3 index --clear
rag3 ask "What are the main aspects of the document?"
```

UI:
```bash
streamlit run ui_module.py
```
Or:
```bash
./scripts/launch_ui.sh
```

## Notes

- Voice input is intentionally disabled in this project version.
- New code no longer hardcodes Windows paths or API keys.

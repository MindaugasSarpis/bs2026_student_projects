# Developer Documentation

## Project Identity
- Product name: **IO, Universal Retriever**
- Domain focus: **GravityX business knowledge retrieval**
- Deployment style: local Python app with Elasticsearch-backed retrieval and Streamlit UI
- Voice mode: intentionally disabled in this project version

## High-Level Architecture

IO is a Retrieval-Augmented Generation (RAG) system with two primary workflows:
1. **Indexing workflow**: ingest local documents, embed them, and write them to Elasticsearch.
2. **Question-answer workflow**: retrieve relevant documents with BM25, build context, generate an answer with OpenAI, then validate answer quality.

Core stack:
- Elasticsearch document store
- Haystack retrieval + embedding components
- OpenAI generation
- Streamlit UI + CLI entrypoints

## End-to-End Runtime Flow

### A) Indexing Flow
1. User launches indexing via launcher, CLI, or UI.
2. `DocumentIndexer` reads supported file types: `.txt`, `.pdf`, `.docx`, `.xlsx`.
3. Documents are converted to text and wrapped as Haystack `Document` objects.
4. `SentenceTransformersDocumentEmbedder` generates embeddings.
5. Embedded documents are written into Elasticsearch index.

### B) Q&A Flow
1. User asks a business question.
2. `RetrieverModule` runs BM25 retrieval (`top_k` configurable).
3. Retrieved document content is merged into a context block.
4. `GenerativeReader` sends prompt to OpenAI using GravityX-specific response structure.
5. `ValidationAgent` runs a second-pass evaluation of relevance/accuracy.
6. UI/CLI returns answer + validation report.

## Module Reference

### `src/rag3/config.py`
- Defines typed config dataclasses.
- Loads settings from environment (`.env`) with defaults.
- Contains the GravityX-specific generation prompt template.
- Exposes `get_default_config()` used by runtime modules.

### `src/rag3/document_store.py`
- Builds Elasticsearch document store client from config.
- Centralized connection settings (host, port, retries, auth).

### `src/rag3/indexing.py`
- `DocumentIndexer` implementation.
- Handles file loading/parsing per format.
- Embeds documents and writes to Elasticsearch.
- Supports `clear=True` full index wipe before ingest.

### `src/rag3/retrieval.py`
- `RetrieverModule` wrapper around Haystack BM25 retriever.
- Includes retry logic and health checks for Elasticsearch.
- Returns top-k matching documents for a query.

### `src/rag3/generation.py`
- `GenerativeReader` OpenAI integration.
- Builds prompt from template + retrieved context.
- Applies model parameters from config.
- Handles common API failure scenarios.

### `src/rag3/validation.py`
- `ValidationAgent` quality-check stage.
- Asks model for JSON evaluation (`accuracy`, `relevance`, `suggestions`).
- Returns safe fallback values if output is malformed.

### `src/rag3/pipeline.py`
- `RAGPipeline` orchestration layer.
- Exposes main API methods:
  - `index_documents(...)`
  - `run_pipeline(query)`
- Lazily initializes generation/validation to avoid unnecessary startup dependencies.

### `src/rag3/cli.py`
- CLI entrypoint for:
  - `index`
  - `ask`
- Designed for developer ops and automation.

### `src/rag3/ui.py`
- Streamlit application layer.
- Product branding: **IO, Universal Retriever**.
- Supports indexing controls, question input, answer display, validation report, and session history.

### `launch_rag.command`
- One-click launcher script for macOS.
- Provides setup + operational menu.
- Includes preflight checks:
  - `OPENAI_API_KEY` availability
  - Elasticsearch reachability
- Includes Docker-based helper to start local Elasticsearch.

### Compatibility Wrappers (top-level)
- Files such as `rag_pipeline.py`, `ui_module.py`, `settings_manager.py`, etc.
- Preserve legacy imports/entry patterns while routing into `src/rag3`.

## Configuration Model

Primary configuration is environment-driven via `.env`.
Key groups:
- OpenAI settings: key, model, generation params
- Elasticsearch settings: host, port, index, retry policy
- Retrieval settings: top-k and retry behavior
- Embedding model settings
- Data folder paths for indexing

See:
- `.env.example`
- `src/rag3/config.py`

## Prompting Strategy (Business Mode)

The generation prompt enforces a business response layout:
1. Executive Summary
2. Evidence From Documents
3. Recommended Next Steps
4. Confidence (High/Medium/Low)

Prompt safety intent:
- no hallucinated commitments
- explicit uncertainty when evidence is missing
- context-grounded answers only

## Error Handling Strategy

- Launcher prechecks catch missing API key and unavailable Elasticsearch early.
- Retrieval layer validates document store health before query execution.
- Generation layer catches OpenAI API connectivity/rate/status errors.
- Validation layer gracefully handles non-JSON responses.

## Supported Document Types

Currently indexed:
- `.txt`
- `.pdf`
- `.docx`
- `.xlsx`

Not currently indexed by default:
- `.csv`, `.pptx`, `.md`, etc. (can be added by extending `indexing.py`)

## Typical Dev Tasks

### Add a new document type
1. Add parser method in `DocumentIndexer`.
2. Add loader invocation in `_load_documents`.
3. Include source metadata type label.

### Change retrieval strategy
1. Replace or augment BM25 in `retrieval.py`.
2. Keep return shape compatible with pipeline (`documents` containing `.content`).

### Modify business answer format
1. Update `GenerationConfig.default_prompt` in `config.py`.
2. Optionally align validation expectations in `validation.py`.

## Operational Notes

- Elasticsearch must be running before indexing or asking.
- First run may download embedding model artifacts.
- Keep API keys in `.env`, not in source code.
- This version intentionally excludes voice interaction for project scope.

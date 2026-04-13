from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from rag3.pipeline import RAGPipeline

logger = logging.getLogger(__name__)


def _get_pipeline() -> RAGPipeline:
    if "rag_pipeline" not in st.session_state:
        st.session_state["rag_pipeline"] = RAGPipeline()
    return st.session_state["rag_pipeline"]


def render_app() -> None:
    st.set_page_config(page_title="IO, Universal Retriever", page_icon="I", layout="wide")
    st.title("IO, Universal Retriever")
    st.caption("Business RAG assistant tailored for GravityX knowledge retrieval.")

    pipeline = _get_pipeline()

    st.sidebar.header("System Status")
    connected = pipeline.retriever.validate_document_store()
    st.sidebar.write(f"Elasticsearch: {'Connected' if connected else 'Disconnected'}")

    st.sidebar.header("Document Indexing")
    txt_path = st.sidebar.text_input("TXT folder", value=pipeline.config.index_documents.txt_folder_path)
    pdf_path = st.sidebar.text_input("PDF folder", value=pipeline.config.index_documents.pdf_folder_path)
    word_path = st.sidebar.text_input("Word folder", value=pipeline.config.index_documents.word_folder_path)
    excel_path = st.sidebar.text_input("Excel folder", value=pipeline.config.index_documents.excel_folder_path)
    clear = st.sidebar.checkbox("Clear index first", value=False)

    if st.sidebar.button("Run Indexing"):
        try:
            indexed = pipeline.index_documents(
                txt_folder_path=Path(txt_path),
                pdf_folder_path=Path(pdf_path),
                word_folder_path=Path(word_path),
                excel_folder_path=Path(excel_path),
                clear=clear,
            )
            st.sidebar.success(f"Indexed {indexed} documents")
        except Exception as exc:
            st.sidebar.error(str(exc))

    st.header("Ask a Business Question")
    query = st.text_input("Question", value="What are the key priorities in the GravityX roadmap?")

    if st.button("Run Pipeline"):
        try:
            answer, report = pipeline.run_pipeline(query)
            st.subheader("Generated Answer")
            st.write(answer)
            st.subheader("Validation Report")
            st.code(json.dumps(report, indent=2, ensure_ascii=False), language="json")

            history = st.session_state.setdefault("history", [])
            history.append({"question": query, "answer": answer, "validation": report})
        except Exception as exc:
            st.error(str(exc))

    history = st.session_state.get("history", [])
    if history:
        st.header("History")
        table = pd.DataFrame(
            {
                "Question": [item["question"] for item in history],
                "Answer": [item["answer"] for item in history],
            }
        )
        st.dataframe(table, use_container_width=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    render_app()


if __name__ == "__main__":
    main()

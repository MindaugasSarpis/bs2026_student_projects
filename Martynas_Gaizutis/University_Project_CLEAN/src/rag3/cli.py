from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IO, Universal Retriever CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    index_cmd = sub.add_parser("index", help="Index TXT/PDF/DOCX/XLSX files")
    index_cmd.add_argument("--txt-folder", type=Path)
    index_cmd.add_argument("--pdf-folder", type=Path)
    index_cmd.add_argument("--word-folder", type=Path)
    index_cmd.add_argument("--excel-folder", type=Path)
    index_cmd.add_argument("--clear", action="store_true", help="Clear index before writing")

    ask_cmd = sub.add_parser("ask", help="Ask a question")
    ask_cmd.add_argument("query", type=str)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "index":
        from rag3.pipeline import RAGPipeline

        pipeline = RAGPipeline()
        count = pipeline.index_documents(
            txt_folder_path=args.txt_folder,
            pdf_folder_path=args.pdf_folder,
            word_folder_path=args.word_folder,
            excel_folder_path=args.excel_folder,
            clear=args.clear,
        )
        print(f"Indexed {count} documents")
        return

    if args.command == "ask":
        from rag3.pipeline import RAGPipeline

        pipeline = RAGPipeline()
        answer, report = pipeline.run_pipeline(args.query)
        print("\nGenerated Answer:\n")
        print(answer)
        print("\nValidation Report:\n")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

if __name__ == "__main__":
    main()

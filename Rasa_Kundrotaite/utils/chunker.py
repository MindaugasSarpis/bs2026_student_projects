import re


def chunk_by_paragraph(text: str, min_words: int = 5) -> list[str]:
    """Splits text into chunks by paragraphs and return a list of chunk strings"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_paragraphs = re.split(r"\n{2,}", text)

    chunks: list[str] = []
    for paragraph in raw_paragraphs:
        paragraph = re.sub(r"\n", " ", paragraph).strip()
        if len(paragraph.split()) >= min_words:
            chunks.append(paragraph)

    return chunks

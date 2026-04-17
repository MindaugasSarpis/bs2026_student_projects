import html
import logging
import streamlit as st
import pandas as pd
from pathlib import Path
import pdfplumber

from utils.chunker import chunk_by_paragraph
from utils.extraction_logic import extract_obligations as _extract_obligations
from utils.highlighter import highlight_text


@st.cache_data(show_spinner=False, persist="disk")
def extract_obligations(chunk: str) -> list[dict]:
    return _extract_obligations(chunk)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Legal Obligation Extractor",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open(Path(__file__).parent / "ui/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

for k, v in {
    "chunks": [],
    "selected": set(),
    "results": {},
    "last_filename": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


@st.cache_data
def extract_text(file_bytes, filename):
    import io

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        return "\n\n".join(p.extract_text() or "" for p in pdf.pages)


st.markdown(
    """<div class="app-header">
        <div>
            <div class="app-title">Legal Obligation Extractor</div>
            <div class="app-sub">Automated obligation extraction from documents</div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1], gap="large")


with left:
    st.markdown('<div class="col-header">Document</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload a document",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded:
        raw = extract_text(uploaded.read(), uploaded.name)

        if uploaded.name != st.session_state.last_filename:
            st.session_state.chunks = chunk_by_paragraph(raw)
            st.session_state.selected = set()
            st.session_state.results = {}
            st.session_state.last_filename = uploaded.name

        chunks = st.session_state.chunks

        if not chunks:
            st.warning("No paragraphs found in this document.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Select all", width="stretch"):
                    st.session_state.selected = set(range(len(chunks)))
                    st.rerun()
            with c2:
                if st.button("Deselect all", width="stretch"):
                    st.session_state.selected = set()
                    st.rerun()

            n_sel = len(st.session_state.selected)
            st.markdown(
                f'<div class="chunk-count">{n_sel} / {len(chunks)} paragraphs selected</div>',
                unsafe_allow_html=True,
            )

            with st.container(height=500, border=False):
                for i, chunk in enumerate(chunks):
                    is_sel = i in st.session_state.selected
                    has_res = i in st.session_state.results
                    sel_cls = "para-span selected" if is_sel else "para-span"
                    preview = html.escape(chunk[:300])
                    if len(chunk) > 300:
                        preview += "…"
                    done_badge = '<span class="done-badge">✓</span>' if has_res else ""

                    st.markdown(
                        f'<div class="{sel_cls}">'
                        f'<span class="para-num">#{i+1}</span>'
                        f'<span class="para-text">{preview}</span>'
                        f"{done_badge}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(f"Select #{i+1}", key=f"tog_{i}", width="stretch"):
                        sel = st.session_state.selected
                        sel.discard(i) if i in sel else sel.add(i)
                        st.rerun()

            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
            if st.button(
                "Extract obligations",
                disabled=(len(st.session_state.selected) == 0),
                width="stretch",
                type="primary",
            ):
                to_process = sorted(st.session_state.selected)
                progress = st.progress(0, text="Extracting obligations…")
                for step, idx in enumerate(to_process):
                    progress.progress(
                        (step + 1) / len(to_process),
                        text=f"Processing paragraph {idx + 1}… ({step + 1}/{len(to_process)})",
                    )
                    try:
                        obls = extract_obligations(st.session_state.chunks[idx])
                    except Exception as e:
                        logger.error("Extraction failed for chunk %d: %s", idx + 1, e)
                        st.error(f"Paragraph {idx + 1}: extraction failed — {e}")
                        continue
                    logger.info(
                        "Extracted %d obligations from chunk %d", len(obls), idx + 1
                    )
                    spans = [o["span"] for o in obls if o.get("span")]
                    st.session_state.results[idx] = {
                        "obligations": obls,
                        "highlighted_html": highlight_text(
                            st.session_state.chunks[idx], spans
                        ),
                    }
                progress.empty()
                st.rerun()


with right:
    st.markdown(
        '<div class="col-header">Extracted Obligations</div>', unsafe_allow_html=True
    )

    results = st.session_state.results

    if not results:
        st.markdown(
            """<div class="empty-state">
                <p>Select paragraphs on the left<br>then click <strong>Extract obligations</strong></p>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        rows = []
        for idx, res in sorted(results.items()):
            for obl in res["obligations"]:
                rows.append(
                    {
                        "paragraph": idx + 1,
                        "actor": obl.get("actor", ""),
                        "action": obl.get("action", ""),
                        "modality": obl.get("modality", ""),
                        "condition": obl.get("condition", ""),
                        "source_text": obl.get("span", ""),
                    }
                )
        df = pd.DataFrame(rows)

        ec1, ec2 = st.columns([3, 1])
        with ec1:
            total = sum(len(r["obligations"]) for r in results.values())
            st.markdown(
                f'<div class="result-summary">{len(results)} paragraph{"s" if len(results)!=1 else ""} | {total} obligation{"s" if total!=1 else ""}</div>',
                unsafe_allow_html=True,
            )
        with ec2:
            st.download_button(
                "Download as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="obligations.csv",
                mime="text/csv",
                width="stretch",
            )

        with st.container(height=750, border=False):
            for idx, res in sorted(results.items()):
                obls = res["obligations"]
                n = len(obls)

                obl_cards_html = ""
                if not obls:
                    obl_cards_html = '<p class="no-obl">No obligations detected.</p>'
                else:
                    for j, obl in enumerate(obls):
                        cc = j % 5
                        actor = html.escape(obl.get("actor", "-"))
                        action = html.escape(obl.get("action", "-"))
                        modality = html.escape(obl.get("modality", "-"))
                        cond = html.escape(obl.get("condition", ""))
                        span = html.escape(obl.get("span", ""))

                        cond_row = (
                            f"<div class='obl-row'><span class='obl-lbl'>Condition</span>"
                            f"<span class='obl-val'>{cond}</span></div>"
                            if cond
                            else ""
                        )
                        src_row = f"<div class='obl-src'>{span}</div>" if span else ""

                        obl_cards_html += (
                            f"<div class='obl-card obl-c{cc}'>"
                            f"<div class='obl-index'>#{j+1}</div>"
                            f"<div class='obl-body'>"
                            f"<div class='obl-row'><span class='obl-lbl'>Actor</span><span class='obl-val'>{actor}</span></div>"
                            f"<div class='obl-row'><span class='obl-lbl'>Modality</span><span class='obl-val mod-pill'>{modality}</span></div>"
                            f"<div class='obl-row'><span class='obl-lbl'>Action</span><span class='obl-val'>{action}</span></div>"
                            f"{cond_row}"
                            f"{src_row}"
                            f"</div>"
                            f"</div>"
                        )

                st.markdown(
                    f"<div class='result-block'>"
                    f"<div class='result-block-header'>#{idx+1}"
                    f"<span class='obl-count-badge'>{n} obligation{'s' if n != 1 else ''}</span>"
                    f"</div>"
                    f"<div class='chunk-body'>{res['highlighted_html']}</div>"
                    f"{obl_cards_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

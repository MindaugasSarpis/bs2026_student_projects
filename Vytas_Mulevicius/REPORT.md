# ⚛️ Final Project Report: CERN Open Data Explorer
**Module Project Report** | **Author**: Vytas Mulevicius  
**Video Demo**: [Watch on Loom](https://www.loom.com/share/e12fc73e9792457eb3c1232111d3d91b)

---

## 1. Executive Summary

This project started from the very first lecture — finding fundamental particles using muons. A single CSV dataset from the CERN Open Data Portal was enough to prove the existence of a fundamental particle. From there, the idea grew: what if you could freely browse, explore, and visualize any dataset from CERN, not just one?

The CERN Open Data Explorer is the answer to that question. It's an interactive, browser-based dashboard that lets you search the CERN Open Data Portal API, retrieve datasets, and analyse them visually — all in one place. The physics (like Invariant Mass reconstruction) is standard HEP theory, but the real focus of this project was the engineering: turning those raw scientific ideas into something that actually works reliably and feels good to use.

---

## 2. The Iterative Development Journey

The project evolved significantly from its initial proof-of-concept into a modular application, driven by a continuous cycle of building something, finding what broke, and fixing it.

### Phase 1: Prototyping & Structure

The first versions were simple — basic calculations, minimal UI, everything in one file. That stopped working pretty quickly as the codebase grew.

A major refactoring split things into a modular `lib/` directory for physics logic, a `pages/` directory for UI views, and a `scripts/` folder for isolated utilities. This made it possible to unit test individual components without spinning up the entire Streamlit UI every time.

### Phase 2: Building the Explorer and Managing Data

The core of the application is the **CERN Explorer** page, where you can search the live CERN Open Data Portal API and retrieve datasets. Connecting to a live API introduced real problems fast — network latency, unpredictable data formats, and files that were far too large to just download blindly.

The solution was giving users three options for how they interact with a dataset:
- **Download** — pull the file locally for full analysis.
- **Peek** — inspect ROOT/DST file headers remotely without downloading the whole thing.
- **Stream** — a two-phase streaming mechanism built to handle network fragmentation issues that kept appearing with deeply nested HEP files.

This wasn't planned from the start — it evolved as each approach hit its own wall.

### Phase 3: Analysis and Visualisation

The **Analysis page** is where the data actually gets explored. Once a dataset is loaded, you can look at the raw data, inspect column names, and generate 3D event-by-event visualisations alongside standard 2D histograms. The goal was to make it feel less like a physics sandbox and more like a tool you'd actually want to use.

Early versions had UI flicker during page transitions and inconsistent styling. These were fixed by dropping hacky CSS injections and properly configuring Streamlit's native dark mode via `.streamlit/config.toml`. Shared styling, component wrappers, and the sidebar were consolidated into `lib/ui_utils.py` to keep things consistent across pages.

### Phase 4: The Macro Generator (Legacy)

The last page — the **Macro Generator** — is a carry-over from the initial project. It generates DaVinci/Gaudi configuration scripts for processing raw DST/ROOT files using the official LHCb software stack. You pick your dataset, configure the job parameters, and export a macro ready to run on the CERN GRID or a local cluster. It's a legacy feature, but a useful one for anyone wanting to go deeper than what the browser tool offers.

---

## 3. Engineering Practices & Quality Assurance

### Testing

The project has over 100 automated tests running via `pytest`. Pydantic was integrated to enforce strict data schemas when loading datasets — if a CSV is missing critical columns like muon momenta, the app catches it cleanly instead of crashing mid-calculation. All local unit tests currently pass.

### Dependency Management

Standard `pip` was replaced with **Pixi**, which handles deterministic builds and manages complex dependencies like ROOT and XRootD integrations across different operating systems without the usual headaches.

---

## 4. Capabilities and Limitations

### What Works Well
- **Free dataset browsing** via the live CERN Open Data Portal API, with pagination and filtering.
- **Flexible data retrieval** — download, peek, or stream depending on what you need.
- **Fast analysis** using [Polars](https://pola.rs/), which handles millions of collision events significantly faster than Pandas.
- **Visual output** including publication-ready 2D histograms and interactive 3D visualisations.

### Known Limitations
1. **Network dependency** — the Explorer is only as fast as the CERN open data servers, which aren't always responsive.
2. **Memory limits** — Polars is fast, but loading 10M+ events directly into Streamlit will cause lag. The UI nudges users toward sample limits to avoid this.
3. **Data format support** — currently only CSV is handled properly. JSON and similar formats are not supported, and any new format the CERN portal introduces could silently break things.
4. **Column inconsistency** — this is the deeper problem. Different datasets come with completely different column names and meanings. There's no universal schema, so the application can't always know what it's looking at. Handling multiple datasets in very different forms, with no shared structure to rely on, remains an open and unsolved problem.

### Conclusion

What started as a single CSV and a particle detection exercise turned into a full, modular data exploration tool. The physics was the starting point, but the interesting work was everything around it — the API integration, the streaming pipeline, the UI consistency, the test coverage. It's not perfect, but it's stable, usable, and something I'd actually want to hand to someone else to use.
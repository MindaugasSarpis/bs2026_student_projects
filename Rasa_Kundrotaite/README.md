# Artificial Intelligence and Data Analytics project
## Legal Obligation Extraction
### Overview

This project focuses on extracting legal obligations from regulatory text using Large Language Models (LLMs).

The system chunks the uploaded document into text chunks, processes them with LLM, and returns structured outputs in a predefined schema, enabling downstream analysis such as:

- obligation classification
- semantic clustering
- actor → action mapping

---

### Tech Stack
- Python 3.12
- Streamlit 
- Hugging Face (transformers, huggingface_hub)
- Pydantic (structured validation)
- Conda (environment management)

Full tech stack can be found in `env.yml`

---

### Approach
**Input**

Text document chunked into raw legal text chunks.

**Processing**
1. Prompt LLM with extraction instructions
2. Enforce structured JSON output
3. Parse response
4. Validate using Pydantic schema

**Output**  
Structured list of obligations
```
{
  "obligations": [
    {
      "actor": "...",
      "action": "...",
      "condition": "...",
      "modality": "..."
    }
  ]
}
```
---

### Project Structure
```
|-- ui/styles.css               # UI 
|-- utils/
│   |-- extraction_logic.py     # core extraction function
│   |-- highlighter.py          # highlighting logic
│   |-- chunker.py              # chunking logic
|-- pages/
|   |-- Analysis.py             # data analysis page
|-- env.yml                     # conda environment
|-- models.py                   # Pydantic models
|-- app.py                      # main app
```
---

### Setup
1. Create environment
```
conda env create -f env.yml
conda activate lo_extraction
```
2. Run the application
```
streamlit run app.py
```
3. Upload the document, extract obligations, and do data analysis

---

### Project demo
[Link to video](https://drive.google.com/file/d/1Mc3VpebAsqfJjUeYfF4SdICG3B3gyxcX/view?usp=sharing)

---

### Author
© Rasa Kundrotaite, 2026
import math
import json
import urllib.request
from typing import Any, TypedDict
import streamlit as st


class CernFileInfo(TypedDict, total=False):
    key: str
    size: int
    uri: str
    checksum: str
    type: str


QUICK_PICKS = {
    "⚛️ J/psi (Jpsimumu)": "Jpsimumu",
    "⚛️ Z Boson (Zmumu)": "Zmumu",
    "⚛️ Upsilon (Ymumu)": "Ymumu",
    "⚛️ DoubleMu (Mixed)": "DoubleMu",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_cern_data(query: str, only_csv: bool = True, size: int = 15, page: int = 1) -> dict[str, Any]:
    """
    Queries the CERN Open Data REST API and returns the parsed JSON response.

    When only_csv=True the request is filtered to CSV-format datasets. Results are
    cached for 1 hour. Returns {'error': <message>} instead of raising on network
    or parse failures.
    """
    try:
        api_url = f"https://opendata.cern.ch/api/records/?q={query.replace(' ', '+')}&size={size}&page={page}"
        if only_csv:
            api_url += "&f=file_format:CSV&f=type:Dataset"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


def format_size(size_bytes: int | None) -> str:
    """Converts a raw byte count to a human-readable string (e.g. '1.5 MB'). Returns 'Unknown Size' for None or 0."""
    if not size_bytes or size_bytes == 0:
        return "Unknown Size"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    return f"{round(size_bytes / p, 2)} {size_name[i]}"

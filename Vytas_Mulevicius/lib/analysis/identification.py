import numpy as np
import pandas as pd
from typing import Optional, Tuple


# Known PDG resonances for dimuon analysis (in GeV)
RESONANCE_DATA = [
    {"name": "J/ψ", "mass": 3.0969, "tolerance": 0.2},
    {"name": "ψ(2S)", "mass": 3.686, "tolerance": 0.2},
    {"name": "Υ(1S)", "mass": 9.460, "tolerance": 0.3},
    {"name": "Υ(2S)", "mass": 10.023, "tolerance": 0.3},
    {"name": "Υ(3S)", "mass": 10.355, "tolerance": 0.3},
    {"name": "Z", "mass": 91.1876, "tolerance": 5.0},
    {"name": "W", "mass": 80.38, "tolerance": 5.0},
    {"name": "B±", "mass": 5.279, "tolerance": 0.1},
    {"name": "B0", "mass": 5.279, "tolerance": 0.1},
    {"name": "Bs", "mass": 5.366, "tolerance": 0.1},
]


def find_primary_peak(df: pd.DataFrame, bins: int = 200) -> Optional[float]:
    """
    Finds the most significant peak in the 'Calculated_M' distribution.
    Uses a standard histogram-mode approach.
    """
    if df.empty or 'Calculated_M' not in df.columns:
        return None

    data = df['Calculated_M'].dropna()
    if len(data) < 10:
        return None

    # Use a histogram to find the mode (peak)
    counts, bin_edges = np.histogram(data, bins=bins)
    max_idx = np.argmax(counts)

    # Return the center of the bin with the most counts
    peak_mass = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2
    return float(peak_mass)


def match_particle(mass: float) -> Tuple[str, float]:
    """
    Matches a detected mass against known resonances.
    Returns (particle_name, pdg_mass).
    If no match is found, returns ('Custom', detected_mass).
    """
    best_match = None
    min_diff = float('inf')

    for res in RESONANCE_DATA:
        diff = abs(mass - res["mass"])
        if diff < res["tolerance"] and diff < min_diff:
            min_diff = diff
            best_match = res

    if best_match:
        return best_match["name"], best_match["mass"]

    return "Custom", mass

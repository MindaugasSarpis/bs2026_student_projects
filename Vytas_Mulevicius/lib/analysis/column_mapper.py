import streamlit as st
import polars as pl

_MUON_MASS_GEV = 0.105658


def map_columns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Detects experiment format (LHCb, ATLAS, CMS) and normalizes columns.
    Returns a DataFrame with standardized columns including 'Calculated_M'.
    """
    cols = df.columns

    if 'muplus_PX' in cols and 'muminus_PX' in cols:
        df = _map_lhcb(df, cols)
        cols = df.columns

    if 'lep_pt' in cols and 'lep_eta' in cols:
        df = _map_atlas(df, cols)
        cols = df.columns

    if ('Muon_Px' in cols and 'NMuon' in cols) or ('Electron_Px' in cols and 'NElectron' in cols):
        df = _map_cms(df, cols)
        cols = df.columns

    if 'Calculated_M' not in df.columns:
        df = _compute_invariant_mass(df, cols)

    return df


def _map_lhcb(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    st.info("💡 **Format Detected:** LHCb NTuple. Mapping particle branches...")
    with st.spinner("Refactoring LHCb columnar data..."):
        mapping = {
            'muplus_PX': 'px1', 'muplus_PY': 'py1', 'muplus_PZ': 'pz1', 'muplus_PT': 'pt1',
            'muminus_PX': 'px2', 'muminus_PY': 'py2', 'muminus_PZ': 'pz2', 'muminus_PT': 'pt2',
        }
        for old_name, new_name in mapping.items():
            if old_name in cols:
                df = df.with_columns((pl.col(old_name) / 1000.0).alias(new_name))

        if 'muplus_PE' in cols:
            df = df.with_columns((pl.col('muplus_PE') / 1000.0).alias('E1'))
        if 'muminus_PE' in cols:
            df = df.with_columns((pl.col('muminus_PE') / 1000.0).alias('E2'))

        if 'E1' not in df.columns:
            df = df.with_columns(
                ((pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2 + _MUON_MASS_GEV**2).sqrt()).alias('E1')
            )
        if 'E2' not in df.columns:
            df = df.with_columns(
                ((pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2 + _MUON_MASS_GEV**2).sqrt()).alias('E2')
            )

        if 'eta1' not in df.columns:
            df = df.with_columns([
                (pl.col('pz1') / (pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2).sqrt()).clip(-0.999, 0.999).arctanh().alias('eta1'),
                (pl.col('pz2') / (pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2).sqrt()).clip(-0.999, 0.999).arctanh().alias('eta2'),
            ])

        if 'muplus_ID' in cols:
            df = df.with_columns([
                pl.col('muplus_ID').alias('Q1'),
                pl.col('muminus_ID').alias('Q2'),
            ])

        parent_mass_col = next(
            (c for c in cols if c.endswith(('_MM', '_M')) and not any(p in c for p in ('muplus', 'muminus', 'Kplus'))),
            None
        )
        if parent_mass_col:
            st.success(f"💎 **High Precision Branch Found:** Using `{parent_mass_col}` (converted to GeV) for mass distribution.")
            df = df.with_columns((pl.col(parent_mass_col) / 1000.0).alias('Calculated_M'))

    return df


def _map_atlas(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    with st.spinner("Extracting ATLAS leptons and converting MeV -> GeV..."):
        n_before = len(df)
        df = df.filter(pl.col('lep_pt').list.len() >= 2)
        n_after = len(df)
        if n_after == 0:
            st.warning(
                f"⚠️ **Single-lepton dataset detected:** all {n_before:,} events have fewer than 2 leptons. "
                "This file is likely a 1-lepton channel sample (e.g. W+jets) and cannot be used for "
                "di-lepton invariant mass analysis. Try a **2lep** dataset instead."
            )
            st.stop()
        elif n_after < n_before:
            st.info(f"ℹ️ Dropped {n_before - n_after:,} events with < 2 leptons ({n_after:,} remain).")
        df = df.with_columns([
            (pl.col('lep_pt').list.get(0) / 1000.0).alias('pt1'),
            (pl.col('lep_pt').list.get(1) / 1000.0).alias('pt2'),
            pl.col('lep_eta').list.get(0).alias('eta1'),
            pl.col('lep_eta').list.get(1).alias('eta2'),
            pl.col('lep_phi').list.get(0).alias('phi1'),
            pl.col('lep_phi').list.get(1).alias('phi2'),
        ])
        if 'lep_E' in cols:
            df = df.with_columns([
                (pl.col('lep_E').list.get(0) / 1000.0).alias('E1'),
                (pl.col('lep_E').list.get(1) / 1000.0).alias('E2'),
            ])
        if 'met_et' in cols:
            df = df.with_columns([
                (pl.col('met_et') / 1000.0).alias('met'),
                pl.col('met_phi').alias('met_phi_val'),
            ])
        if 'lep_charge' in cols:
            df = df.with_columns([
                pl.col('lep_charge').list.get(0).alias('Q1'),
                pl.col('lep_charge').list.get(1).alias('Q2'),
            ])
        df = df.drop_nulls(subset=['pt1', 'pt2'])
    return df


def _map_cms(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """
    CMS format: NMuon/NElectron scalars + Muon_Px/Py/Pz/E and Electron_Px/Py/Pz/E
    as variable-length List columns (units: GeV). Prefers dimuon if ≥ 2 muons
    exist in any event, otherwise falls back to dielectron.
    """
    with st.spinner("Extracting CMS leptons..."):
        has_dimuon = 'Muon_Px' in cols and df.filter(pl.col('NMuon') >= 2).height > 0
        has_dielectron = 'Electron_Px' in cols and df.filter(pl.col('NElectron') >= 2).height > 0

        if has_dimuon:
            lepton = 'Muon'
            count_col = 'NMuon'
        elif has_dielectron:
            lepton = 'Electron'
            count_col = 'NElectron'
        else:
            st.warning("⚠️ No events with ≥ 2 muons or electrons found in this CMS dataset.")
            st.stop()
            return df

        n_before = len(df)
        df = df.filter(pl.col(count_col) >= 2)
        n_after = len(df)
        if n_after < n_before:
            st.info(f"ℹ️ Kept {n_after:,} {lepton.lower()} events (dropped {n_before - n_after:,} with < 2).")

        df = df.with_columns([
            pl.col(f'{lepton}_Px').list.get(0).alias('px1'),
            pl.col(f'{lepton}_Py').list.get(0).alias('py1'),
            pl.col(f'{lepton}_Pz').list.get(0).alias('pz1'),
            pl.col(f'{lepton}_E').list.get(0).alias('E1'),
            pl.col(f'{lepton}_Px').list.get(1).alias('px2'),
            pl.col(f'{lepton}_Py').list.get(1).alias('py2'),
            pl.col(f'{lepton}_Pz').list.get(1).alias('pz2'),
            pl.col(f'{lepton}_E').list.get(1).alias('E2'),
        ])
        charge_col = f'{lepton}_Charge'
        if charge_col in cols:
            df = df.with_columns([
                pl.col(charge_col).list.get(0).alias('Q1'),
                pl.col(charge_col).list.get(1).alias('Q2'),
            ])
    return df


def _lorentz_mass(df: pl.DataFrame) -> pl.DataFrame:
    """Compute invariant mass from E1/E2/px1/px2/py1/py2/pz1/pz2 columns."""
    return df.with_columns(
        ((pl.col('E1') + pl.col('E2'))**2 - (
            (pl.col('px1') + pl.col('px2'))**2 +
            (pl.col('py1') + pl.col('py2'))**2 +
            (pl.col('pz1') + pl.col('pz2'))**2
        )).clip(lower_bound=0).sqrt().alias('Calculated_M')
    )


def _compute_invariant_mass(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    if 'E1' in cols and 'px1' in cols:
        df = _lorentz_mass(df)

    elif 'pt1' in cols and 'eta1' in cols:
        df = df.with_columns([
            (pl.col('pt1') * pl.col('phi1').cos()).alias('px1'),
            (pl.col('pt1') * pl.col('phi1').sin()).alias('py1'),
            (pl.col('pt1') * pl.col('eta1').sinh()).alias('pz1'),
            (pl.col('pt2') * pl.col('phi2').cos()).alias('px2'),
            (pl.col('pt2') * pl.col('phi2').sin()).alias('py2'),
            (pl.col('pt2') * pl.col('eta2').sinh()).alias('pz2'),
        ])
        df = df.with_columns([
            ((pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2 + _MUON_MASS_GEV**2).sqrt()).alias('E1'),
            ((pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2 + _MUON_MASS_GEV**2).sqrt()).alias('E2'),
        ])
        df = _lorentz_mass(df)

    elif 'pt' in cols and 'MET' in cols:
        st.info("💡 **Format Detected:** Single-particle event with Missing Transverse Energy (MET). Calculating **Transverse Mass ($M_T$)**.")
        df = df.with_columns(
            ((2 * pl.col('pt') * pl.col('MET') * (1 - (pl.col('phi') - pl.col('phiMET')).cos())).sqrt()).alias('Calculated_M')
        )
        # Standardize cartesian coordinates for 3D visualization
        df = df.with_columns([
            (pl.col('pt') * pl.col('phi').cos()).alias('px'),
            (pl.col('pt') * pl.col('phi').sin()).alias('py'),
            (pl.col('MET') * pl.col('phiMET').cos()).alias('pxMET'),
            (pl.col('MET') * pl.col('phiMET').sin()).alias('pyMET'),
        ])
        if 'eta' in cols:
            df = df.with_columns((pl.col('pt') * pl.col('eta').sinh()).alias('pz'))
        else:
            df = df.with_columns(pl.lit(0.0).alias('pz'))

    elif 'M' in cols:
        df = df.with_columns(pl.col('M').alias('Calculated_M'))

    else:
        # Check if this looks like a RAW dataset (mostly framework/HLT branches)
        is_raw = any('HLT' in c or 'source' in c or 'edm' in c for c in df.columns)
        if is_raw:
            st.error("⚠️ **RAW Dataset Detected:** This file contains low-level detector signals rather than physics objects (Muons/Electrons).")
            st.info(
                "**Recommendation:** RAW data is not directly usable for invariant mass analysis. "
                "Please search the **CERN Explorer** for the **AOD** or **MINIAOD** version of this dataset, "
                "which contains the reconstructed leptons you need."
            )
        else:
            st.error(f"Dataset columns {df.columns} are not recognized for invariant mass calculation.")
        st.stop()

    return df

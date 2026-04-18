from functools import reduce
import polars as pl


def apply_kinematic_filters(
    df: pl.DataFrame,
    mass_range: tuple[float, float],
    pt_min: float,
    eta_max: float,
    require_opposite_charge: bool,
) -> pl.DataFrame:
    """
    Applies sequential kinematic cuts to a standardized Polars DataFrame.

    mass_range is an inclusive window on 'Calculated_M'. pt_min and eta_max apply
    to pt1/pt2 and eta1/eta2 (dimuon events) or single pt/eta (W-like single-lepton
    events). eta is compared as absolute value. The opposite-charge cut is silently
    skipped when Q1/Q2 columns are absent.
    """
    cols = df.columns

    filter_exprs = [
        (pl.col('Calculated_M') >= mass_range[0]) & (pl.col('Calculated_M') <= mass_range[1])
    ]

    if 'pt1' in cols:
        filter_exprs.append((pl.col('pt1') >= pt_min) & (pl.col('pt2') >= pt_min))
        filter_exprs.append((pl.col('eta1').abs() <= eta_max) & (pl.col('eta2').abs() <= eta_max))
    elif 'pt' in cols:
        filter_exprs.append(pl.col('pt') >= pt_min)
        filter_exprs.append(pl.col('eta').abs() <= eta_max)

    if require_opposite_charge and 'Q1' in cols and 'Q2' in cols:
        filter_exprs.append(pl.col('Q1') != pl.col('Q2'))

    return df.filter(reduce(lambda a, b: a & b, filter_exprs))

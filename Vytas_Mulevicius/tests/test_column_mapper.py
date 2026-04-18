import math
import pytest
import polars as pl
from lib.analysis.column_mapper import _compute_invariant_mass


# ---------------------------------------------------------------------------
# Cartesian format: (E1, px1, py1, pz1, E2, px2, py2, pz2)
# ---------------------------------------------------------------------------

class TestCartesianInvariantMass:
    def test_two_particles_at_rest_gives_summed_energy(self):
        """Two particles at rest, E=1 each → M = 2."""
        df = pl.DataFrame({
            'E1': [1.0], 'E2': [1.0],
            'px1': [0.0], 'py1': [0.0], 'pz1': [0.0],
            'px2': [0.0], 'py2': [0.0], 'pz2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(2.0)

    def test_back_to_back_z_boson_like(self):
        """E=45.6, px back-to-back → net momentum zero → M = 2*45.6 = 91.2."""
        df = pl.DataFrame({
            'E1': [45.6], 'E2': [45.6],
            'px1': [45.6], 'py1': [0.0], 'pz1': [0.0],
            'px2': [-45.6], 'py2': [0.0], 'pz2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(91.2, rel=1e-5)

    def test_collinear_particles_reduce_mass(self):
        """Same-direction momenta reduce invariant mass below 2E."""
        df = pl.DataFrame({
            'E1': [10.0], 'E2': [10.0],
            'px1': [9.9], 'py1': [0.0], 'pz1': [0.0],
            'px2': [9.9], 'py2': [0.0], 'pz2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] < 20.0

    def test_unphysical_kinematics_clipped_to_zero(self):
        """Slightly unphysical input (M² < 0) must not raise — clipped to 0."""
        df = pl.DataFrame({
            'E1': [1.0], 'E2': [1.0],
            'px1': [1.5], 'py1': [0.0], 'pz1': [0.0],
            'px2': [1.5], 'py2': [0.0], 'pz2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] >= 0.0

    def test_multiple_rows_computed_independently(self):
        df = pl.DataFrame({
            'E1': [1.0, 2.0], 'E2': [1.0, 2.0],
            'px1': [0.0, 0.0], 'py1': [0.0, 0.0], 'pz1': [0.0, 0.0],
            'px2': [0.0, 0.0], 'py2': [0.0, 0.0], 'pz2': [0.0, 0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(2.0)
        assert result['Calculated_M'][1] == pytest.approx(4.0)

    def test_calculated_m_present(self):
        df = pl.DataFrame({
            'E1': [1.0], 'E2': [1.0],
            'px1': [0.0], 'py1': [0.0], 'pz1': [0.0],
            'px2': [0.0], 'py2': [0.0], 'pz2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert 'Calculated_M' in result.columns
        assert result['Calculated_M'][0] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Transverse format: (pt1, eta1, phi1, pt2, eta2, phi2)
# ---------------------------------------------------------------------------

class TestTransverseInvariantMass:
    def test_back_to_back_muons_at_zero_rapidity(self):
        """
        pt=1, eta=0, phi back-to-back (0 vs π).
        px cancel → M = 2 * sqrt(pt² + m_mu²).
        """
        m_mu = 0.105658
        expected = 2.0 * math.sqrt(1.0 + m_mu ** 2)
        df = pl.DataFrame({
            'pt1': [1.0], 'eta1': [0.0], 'phi1': [0.0],
            'pt2': [1.0], 'eta2': [0.0], 'phi2': [math.pi],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(expected, rel=1e-5)

    def test_collinear_muons_reduce_invariant_mass(self):
        """Same phi → momenta add → lower invariant mass than back-to-back."""
        m_mu = 0.105658
        back_to_back = 2.0 * math.sqrt(1.0 + m_mu ** 2)
        df = pl.DataFrame({
            'pt1': [1.0], 'eta1': [0.0], 'phi1': [0.0],
            'pt2': [1.0], 'eta2': [0.0], 'phi2': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] < back_to_back

    def test_cartesian_components_are_computed(self):
        df = pl.DataFrame({
            'pt1': [1.0], 'eta1': [0.0], 'phi1': [0.0],
            'pt2': [1.0], 'eta2': [0.0], 'phi2': [math.pi],
        })
        result = _compute_invariant_mass(df, df.columns)
        for col in ('px1', 'py1', 'pz1', 'px2', 'py2', 'pz2', 'E1', 'E2'):
            assert col in result.columns

    def test_phi1_zero_gives_px1_equal_pt1(self):
        """phi=0 → px = pt * cos(0) = pt."""
        df = pl.DataFrame({
            'pt1': [5.0], 'eta1': [0.0], 'phi1': [0.0],
            'pt2': [5.0], 'eta2': [0.0], 'phi2': [math.pi],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['px1'][0] == pytest.approx(5.0, rel=1e-6)


# ---------------------------------------------------------------------------
# W boson / single-lepton + MET → transverse mass
# ---------------------------------------------------------------------------

class TestTransverseMass:
    def test_w_boson_back_to_back_gives_80_gev(self):
        """
        pt=40, MET=40, dphi=π → MT = sqrt(2*40*40*(1-cos(π))) = sqrt(6400) = 80.
        """
        df = pl.DataFrame({
            'pt': [40.0], 'MET': [40.0],
            'phi': [0.0], 'phiMET': [math.pi],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(80.0, rel=1e-5)

    def test_collinear_lepton_and_met_gives_zero_mt(self):
        """dphi=0 → MT = 0 (lepton and MET aligned)."""
        df = pl.DataFrame({
            'pt': [40.0], 'MET': [40.0],
            'phi': [0.0], 'phiMET': [0.0],
        })
        result = _compute_invariant_mass(df, df.columns)
        assert result['Calculated_M'][0] == pytest.approx(0.0, abs=1e-6)

    def test_mt_scales_with_pt(self):
        """Doubling pt (with MET fixed, dphi=π) should double MT."""
        df1 = pl.DataFrame({'pt': [20.0], 'MET': [20.0], 'phi': [0.0], 'phiMET': [math.pi]})
        df2 = pl.DataFrame({'pt': [40.0], 'MET': [40.0], 'phi': [0.0], 'phiMET': [math.pi]})
        mt1 = _compute_invariant_mass(df1, df1.columns)['Calculated_M'][0]
        mt2 = _compute_invariant_mass(df2, df2.columns)['Calculated_M'][0]
        assert mt2 == pytest.approx(2.0 * mt1, rel=1e-5)


# ---------------------------------------------------------------------------
# Pre-computed M column passthrough
# ---------------------------------------------------------------------------

class TestPrecomputedMass:
    def test_aliases_m_column_to_calculated_m(self):
        df = pl.DataFrame({'M': [91.2, 3.096, 9.46]})
        result = _compute_invariant_mass(df, df.columns)
        assert 'Calculated_M' in result.columns
        assert result['Calculated_M'].to_list() == pytest.approx([91.2, 3.096, 9.46])

    def test_original_m_column_still_present(self):
        df = pl.DataFrame({'M': [91.2]})
        result = _compute_invariant_mass(df, df.columns)
        assert 'M' in result.columns

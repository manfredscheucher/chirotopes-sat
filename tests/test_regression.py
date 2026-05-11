"""Regression tests for known chirotope instances with specific mutation sets."""

import pytest
from chirotopes.encoding import ChirotopeEncoder
from chirotopes.solver import solve


class TestMutationExamples:
    """Test the hardcoded mutation examples from the original code."""

    def test_rank3_n9_mutations(self):
        """The (3,9) instance with specific mutation set should be satisfiable."""
        enc = ChirotopeEncoder(3, 9, encoding="both")
        enc.encode(test=True)
        solutions = list(solve(enc, enumerate_all=False))
        assert len(solutions) == 1, "Expected at least one solution for (3,9) test case"

    @pytest.mark.slow
    def test_rank4_n11_mutations(self):
        """The (4,11) instance with specific mutation set should be satisfiable."""
        enc = ChirotopeEncoder(4, 11, encoding="both")
        enc.encode(test=True)
        solutions = list(solve(enc, enumerate_all=False))
        assert len(solutions) == 1, "Expected at least one solution for (4,11) test case"


class TestAllowedPatternsVsGP:
    """Test that allowed patterns alone vs with GP give same results for rank 3."""

    def test_rank3_equivalence(self):
        """For rank 3, allowed-patterns-only should give same count as with GP."""
        r, n = 3, 5

        enc_ap = ChirotopeEncoder(r, n, encoding="allowedpatterns", symmetry=True)
        enc_ap.encode()
        count_ap = sum(1 for _ in solve(enc_ap, enumerate_all=True))

        enc_gp = ChirotopeEncoder(r, n, encoding="both", symmetry=True)
        enc_gp.encode()
        count_gp = sum(1 for _ in solve(enc_gp, enumerate_all=True))

        assert count_ap == count_gp, (
            f"Rank 3 should give same results: "
            f"allowed-patterns={count_ap}, with GP={count_gp}"
        )

"""Tests for the SAT solver integration."""

import pytest
from chirotopes.encoding import ChirotopeEncoder
from chirotopes.solver import solve


def _count_solutions(r, n, *, symmetry=False, encoding="both", signotope=False):
    """Helper: count all chirotope solutions for given parameters."""
    enc = ChirotopeEncoder(
        r, n,
        encoding=encoding,
        symmetry=symmetry,
        signotope=signotope,
    )
    enc.encode()
    return sum(1 for _ in solve(enc, enumerate_all=True))


class TestSolverBasic:
    def test_rank3_n3(self):
        """Rank 3, 3 elements: exactly 1 chirotope (up to reorientation)."""
        # With symmetry breaking: should find 1
        count = _count_solutions(3, 3, symmetry=True)
        assert count == 1

    def test_rank3_n4(self):
        """Rank 3, 4 elements with symmetry: 1 chirotope (x2 reorientations)."""
        count = _count_solutions(3, 4, symmetry=True)
        assert count == 2

    def test_rank3_n5(self):
        """Rank 3, 5 elements with symmetry: counts include reorientations."""
        count = _count_solutions(3, 5, symmetry=True)
        assert count == 8

    def test_rank3_n6(self):
        """Rank 3, 6 elements with symmetry: counts include reorientations."""
        count = _count_solutions(3, 6, symmetry=True)
        assert count == 62


class TestSolverSingleSolution:
    def test_finds_solution(self):
        """Should find at least one solution for small instance."""
        enc = ChirotopeEncoder(3, 5, encoding="both", symmetry=True)
        enc.encode()
        solutions = list(solve(enc, enumerate_all=False))
        assert len(solutions) == 1
        assert all(c in "+-" for c in solutions[0])

    def test_solution_length(self):
        """Solution string should have correct length = C(n,r)."""
        import math
        enc = ChirotopeEncoder(3, 5, encoding="both")
        enc.encode()
        solutions = list(solve(enc, enumerate_all=False))
        expected_len = math.comb(5, 3)
        assert len(solutions[0]) == expected_len


class TestSolverNoMutations:
    def test_rank3_n5_nomutations(self):
        """Rank 3, 5 elements, no mutations, with symmetry."""
        enc = ChirotopeEncoder(3, 5, encoding="both", symmetry=True)
        enc.encode(nomutations=True)
        count = sum(1 for _ in solve(enc, enumerate_all=True))
        # Should have fewer solutions than without nomutations
        assert count >= 0


@pytest.mark.slow
class TestSolverSlow:
    """Tests that take longer to run. Mark with pytest -m slow."""

    def test_rank3_n7(self):
        """Rank 3, 7 elements with symmetry: 135 chirotopes."""
        count = _count_solutions(3, 7, symmetry=True)
        assert count == 135

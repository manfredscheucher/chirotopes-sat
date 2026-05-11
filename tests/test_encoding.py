"""Tests for the SAT encoding."""

import pytest
from chirotopes.encoding import ChirotopeEncoder


class TestChirotopeEncoder:
    def test_creation_rank3_n5(self):
        enc = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        assert enc.r == 3
        assert enc.n == 5
        assert enc.packet_size == 5
        assert len(enc.allowed_patterns) == 384

    def test_creation_rank3_n5_signotope(self):
        enc = ChirotopeEncoder(3, 5, signotope=True, encoding="allowedpatterns")
        assert enc.packet_size == 4

    def test_var_sign_sorted(self):
        enc = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        v = enc.var_sign(0, 1, 2)
        assert isinstance(v, int)
        assert v > 0

    def test_var_sign_permutation(self):
        enc = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        v_sorted = enc.var_sign(0, 1, 2)
        v_swapped = enc.var_sign(1, 0, 2)
        assert v_swapped == -v_sorted

    def test_encode_produces_constraints(self):
        enc = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        enc.encode()
        assert enc.num_clauses > 0
        assert enc.num_vars > 0

    def test_allowedpatterns_has_flippability_constraints(self):
        """allowedpatterns adds flippability variables beyond grassmannpluecker."""
        enc_gp = ChirotopeEncoder(3, 5, encoding="grassmannpluecker")
        enc_gp.encode()

        enc_ap = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        enc_ap.encode()

        # allowedpatterns has extra flippability constraints
        assert enc_ap.num_clauses > enc_gp.num_clauses
        assert enc_ap.num_vars > enc_gp.num_vars

    def test_symmetry_adds_constraints(self):
        enc_no_sym = ChirotopeEncoder(3, 5, encoding="allowedpatterns")
        enc_no_sym.encode()

        enc_sym = ChirotopeEncoder(3, 5, encoding="allowedpatterns", symmetry=True)
        enc_sym.encode()

        assert enc_sym.num_clauses > enc_no_sym.num_clauses

    def test_write_cnf(self, tmp_path):
        enc = ChirotopeEncoder(3, 4, encoding="allowedpatterns")
        enc.encode()
        cnf_file = tmp_path / "test.cnf"
        enc.write_cnf(str(cnf_file))

        content = cnf_file.read_text()
        assert content.startswith("p cnf")
        lines = content.strip().split("\n")
        # First line is header, rest are clauses
        assert len(lines) == enc.num_clauses + 1

        # Check vars file was created
        vars_file = tmp_path / "test.cnf.vars"
        assert vars_file.exists()

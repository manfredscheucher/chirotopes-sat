"""Tests for core chirotope functions."""

import pytest
from chirotopes.core import (
    perm_sign,
    pattern_to_signs,
    evaluate_chirotope,
    satisfies_3term_gp,
    compute_allowed_patterns,
    flip_sign_at,
    local_to_global_indices,
)


class TestPermSign:
    def test_identity(self):
        assert perm_sign((0, 1, 2), (0, 1, 2)) == 1

    def test_single_swap(self):
        assert perm_sign((1, 0, 2), (0, 1, 2)) == -1

    def test_double_swap(self):
        assert perm_sign((1, 2, 0), (0, 1, 2)) == 1

    def test_two_elements(self):
        assert perm_sign((0, 1), (0, 1)) == 1
        assert perm_sign((1, 0), (0, 1)) == -1

    def test_reverse_three(self):
        # (2,1,0) has 3 inversions -> odd -> -1
        assert perm_sign((2, 1, 0), (0, 1, 2)) == -1


class TestPatternToSigns:
    def test_all_plus(self):
        assert pattern_to_signs("+++") == [1, 1, 1]

    def test_mixed(self):
        assert pattern_to_signs("+-+") == [1, -1, 1]

    def test_all_minus(self):
        assert pattern_to_signs("--") == [-1, -1]


class TestEvaluateChirotope:
    def test_sorted_tuple(self):
        # Pattern "+++" for 3 elements of rank 2, packet_range = [0,1,2,3]
        # C(4,2) = 6 r-tuples, so pattern has length 6
        val = evaluate_chirotope((0, 1), "++++++", list(range(4)), 2)
        assert val == 1

    def test_permutation_sign(self):
        # Swapping should flip the sign
        val_sorted = evaluate_chirotope((0, 1), "++++++", list(range(4)), 2)
        val_swapped = evaluate_chirotope((1, 0), "++++++", list(range(4)), 2)
        assert val_sorted == -val_swapped


class TestSatisfies3termGP:
    def test_all_plus_rank3(self):
        # All-plus pattern should satisfy GP for rank 3
        # packet_size = 5, packet_len = C(5,3) = 10
        assert satisfies_3term_gp("+" * 10, list(range(5)), 3) is True

    def test_known_invalid_pattern(self):
        # A pattern not in the allowed list should fail GP
        # "+-+++-+-+-" is not among the 384 allowed patterns for rank 3
        assert satisfies_3term_gp("++++++++-+", list(range(5)), 3) is False


class TestComputeAllowedPatterns:
    def test_rank3_count(self):
        patterns = compute_allowed_patterns(3)
        assert len(patterns) == 384

    def test_rank4_count(self):
        patterns = compute_allowed_patterns(4)
        assert len(patterns) == 3584

    def test_rank3_all_satisfy_gp(self):
        patterns = compute_allowed_patterns(3)
        packet_range = list(range(5))
        for p in patterns:
            assert satisfies_3term_gp(p, packet_range, 3), f"Pattern {p} fails GP check"


class TestFlipSignAt:
    def test_flip_plus(self):
        assert flip_sign_at("+++", 1) == "+-+"

    def test_flip_minus(self):
        assert flip_sign_at("+-+", 1) == "+++"

    def test_flip_first(self):
        assert flip_sign_at("-++", 0) == "+++"

    def test_flip_last(self):
        assert flip_sign_at("+++", 2) == "++-"


class TestLocalToGlobalIndices:
    def test_identity_mapping(self):
        assert local_to_global_indices((0, 1, 2), (0, 1, 2, 3, 4)) == (0, 1, 2)

    def test_offset_mapping(self):
        assert local_to_global_indices((0, 2), (3, 5, 7)) == (3, 7)

    def test_single(self):
        assert local_to_global_indices((1,), (10, 20, 30)) == (20,)

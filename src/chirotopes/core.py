"""Core chirotope functions: permutation signs, pattern validation, GP relations."""

from itertools import combinations, permutations, product
import math
import os
from pathlib import Path


def perm_sign(P: tuple, L: tuple) -> int:
    """Compute the sign of the permutation that sorts P into order L.

    Counts inversions: pairs (i,j) with i<j but P[i]>P[j].
    Returns +1 or -1.
    """
    c = 0
    n = len(L)
    for i in range(n):
        for j in range(i + 1, n):
            if P[i] > P[j]:
                c += 1
    return (-1) ** (c % 2)


def pattern_to_signs(t: str) -> list[int]:
    """Convert a pattern string like '++-+' to a sign vector [+1,+1,-1,+1]."""
    return [+1 if x == '+' else -1 for x in t]


def evaluate_chirotope(P: tuple, c: str, packet_range: list[int], r: int) -> int:
    """Evaluate chirotope pattern c at permutation P.

    The encoding stores signs for sorted r-subsets only.
    For unsorted tuples, multiply by the permutation sign (alternating axiom).
    """
    I = tuple(sorted(P))
    sign = perm_sign(P, I)
    vector = pattern_to_signs(c)
    i = 0
    for J in combinations(packet_range, r):
        if I == J:
            if vector[i] == sign:
                return 1
            else:
                return -1
        i += 1


def satisfies_3term_gp(c: str, packet_range: list[int], r: int) -> bool:
    """Check whether pattern c satisfies all 3-term Grassmann-Pluecker relations.

    For each pair of elements b1, b2 in packet_range and rest a = a1,...,a_r,
    checks: if chi(b1, a2,...) == chi(a1, b2, a3,...) and
            chi(b2, a2,...) == chi(b1, a1, a3,...),
    then chi(a1,...,a_r) == chi(b1, b2, a3,...).
    """
    for i in packet_range:
        for j in packet_range:
            if i == j:
                continue
            rest = tuple(set(packet_range) - {i, j})
            for P in permutations(rest):
                if (evaluate_chirotope((i,) + P[1:], c, packet_range, r) ==
                        evaluate_chirotope((P[0], j) + P[2:], c, packet_range, r) and
                        evaluate_chirotope((j,) + P[1:], c, packet_range, r) ==
                        evaluate_chirotope((i, P[0]) + P[2:], c, packet_range, r)):
                    if not (evaluate_chirotope(P, c, packet_range, r) ==
                            evaluate_chirotope((i, j) + P[2:], c, packet_range, r)):
                        return False
    return True


def compute_allowed_patterns(r: int, signotope: bool = False) -> list[str]:
    """Compute or load cached allowed patterns for rank r.

    For chirotopes: patterns satisfying 3-term GP relations within (r+2)-subsets.
    For signotopes: patterns with at most one sign change between consecutive positions.

    Returns list of pattern strings.
    """
    packet_size = r + 1 if signotope else r + 2
    packet_len = math.comb(packet_size, r)
    packet_range = list(range(packet_size))

    # Try to load from package data
    if signotope:
        name = f"allowed_patterns_signotopes{r}.txt"
    else:
        name = f"allowed_patterns{r}.txt"

    data_dir = Path(__file__).parent / "data"
    fp = data_dir / name

    if fp.is_file():
        return [s.strip() for s in fp.read_text().splitlines() if s.strip()]

    # Generate from scratch
    if signotope:
        patterns = [
            s for s in ["".join(s) for s in product("+-", repeat=packet_size)]
            if s.count("+-") + s.count("-+") <= 1
        ]
    else:
        patterns = [
            s for s in ["".join(s) for s in product("+-", repeat=packet_len)]
            if satisfies_3term_gp(s, packet_range, r)
        ]

    # Cache for future use
    data_dir.mkdir(parents=True, exist_ok=True)
    fp.write_text("\n".join(patterns) + "\n")

    return patterns


def flip_sign_at(t: str, i: int) -> str:
    """Flip the sign at position i in pattern string t."""
    return t[:i] + ('+' if t[i] == '-' else '-') + t[i + 1:]


def local_to_global_indices(I_prime: tuple, J: tuple) -> tuple:
    """Map local indices within packet J to global element indices.

    I_prime contains indices into J; returns the corresponding elements of J.
    """
    return tuple(J[k] for k in I_prime)

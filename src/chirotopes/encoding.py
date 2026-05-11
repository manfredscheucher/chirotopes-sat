"""SAT encoding for chirotope enumeration."""

import math
from itertools import combinations, permutations

from pysat.formula import IDPool

from .core import (
    compute_allowed_patterns,
    flip_sign_at,
    local_to_global_indices,
    pattern_to_signs,
)


class ChirotopeEncoder:
    """Encodes chirotope constraints as a SAT instance.

    Parameters
    ----------
    r : int
        Rank of the chirotope.
    n : int
        Number of elements {0, ..., n-1}.
    signotope : bool
        If True, encode signotopes instead of chirotopes.
    encoding : str
        Which encoding to use:
        - ``"grassmannpluecker"`` (default): allowed-pattern constraints on
          (r+2)-element subsets, which encode the Grassmann-Pluecker
          relations.  Correct for all ranks.
        - ``"allowedpatterns"``: same pattern constraints plus flippability
          variables (needed for mutation/coloring analysis).
        - ``"both"``: alias for ``"allowedpatterns"`` (kept for
          backwards-compatibility).
    allow_cyclic : bool
        If True, allow cyclic chirotopes. Default is False (acyclic only).
    symmetry : bool
        If True, add symmetry-breaking constraints.
    bva : bool
        If True, add Bounded Variable Addition optimization.
    """

    ENCODINGS = ("allowedpatterns", "grassmannpluecker", "both")

    def __init__(self, r: int, n: int, *,
                 signotope: bool = False,
                 encoding: str = "grassmannpluecker",
                 allow_cyclic: bool = False,
                 symmetry: bool = False,
                 bva: bool = False):
        if encoding not in self.ENCODINGS:
            raise ValueError(
                f"encoding must be one of {self.ENCODINGS}, got {encoding!r}")
        self.r = r
        self.n = n
        self.signotope = signotope
        self.encoding = encoding
        self.allow_cyclic = allow_cyclic
        self.symmetry = symmetry
        self.bva = bva

        self.packet_size = r + 1 if signotope else r + 2
        self.packet_len = math.comb(self.packet_size, r)
        self.packet_range = list(range(self.packet_size))
        self.N = list(range(n))
        self.R = list(range(r))

        # Flippability variables are only needed for mutation/coloring analysis.
        self.use_allowed_patterns = encoding in ("allowedpatterns", "both")
        self.use_grassmann_pluecker = encoding in ("grassmannpluecker", "both")

        # Allowed patterns are needed for the pattern encoding and flippability
        self.allowed_patterns = compute_allowed_patterns(r, signotope)

        # Build r-tuple index mapping
        self.r_tuple_index = {}
        self.r_tuples = []
        for i, I in enumerate(combinations(self.packet_range, r)):
            self.r_tuple_index[I] = i
            self.r_tuples.append(I)

        # Precompute flippable patterns per r-tuple
        self.allowed_patterns_with_flippable_I = {
            I: [t for t in self.allowed_patterns
                if flip_sign_at(t, self.r_tuple_index[I]) in self.allowed_patterns]
            for I in combinations(self.packet_range, r)
        }

        # Setup variable pool
        self.vpool = IDPool()
        self.constraints = []
        self._setup_variables()

    def _setup_variables(self):
        """Create SAT variables."""
        r, n = self.r, self.n
        N = self.N

        # Sign variables: var_sign_[I] for sorted r-subsets
        self._var_sign = {
            I: self.vpool.id(f'S_{I}')
            for I in combinations(N, r)
        }
        self._sign_set = set(self._var_sign.keys())

        # Allowed-pattern variables (always needed — the pattern constraints
        # are the core encoding of the chirotope axioms for all ranks).
        self._var_allowed_pattern = {
            (I, t): self.vpool.id(f'A_{I}_{t}')
            for I in combinations(N, self.packet_size)
            for t in self.allowed_patterns
        }

        if self.use_allowed_patterns:
            # Flippable-in-J variables (only for mutation analysis)
            self._var_flippable_I_J = {
                (I, J): self.vpool.id(f'G_{I}_{J}')
                for J in combinations(N, self.packet_size)
                for I in combinations(J, r)
            }

        # Globally flippable variables (always needed for mutation constraints)
        self._var_flippable = {
            I: self.vpool.id(f'F_{I}')
            for I in combinations(N, r)
        }

        # BVA pair sign variables
        if self.bva:
            self._setup_bva_variables()

    def _setup_bva_variables(self):
        """Create BVA optimization variables."""
        N = self.N
        packet_len = self.packet_len

        if not self.signotope:
            self._var_pair_signs = {
                (J, i, p): self.vpool.id()
                for p in ["++", "--", "+-", "-+"]
                for J in combinations(N, self.packet_size)
                for i in range(0, packet_len - 1, 2)
            }
        else:
            self._var_pair_signs = {}
            if self.packet_size % 2 == 0:
                for p in ["++", "--"]:
                    for J in combinations(N, self.packet_size):
                        for i in range(0, packet_len - 1, 2):
                            self._var_pair_signs[(J, i, p)] = self.vpool.id()
            else:
                for J in combinations(N, self.packet_size):
                    self._var_pair_signs[(J, 0, "+++")] = self.vpool.id()
                    self._var_pair_signs[(J, 0, "---")] = self.vpool.id()
                    for i in range(3, packet_len - 1, 2):
                        self._var_pair_signs[(J, i, "++")] = self.vpool.id()
                        self._var_pair_signs[(J, i, "--")] = self.vpool.id()

    def var_sign(self, *I) -> int:
        """Get SAT variable for the sign of chi(I), handling permutation signs."""
        if I not in self._sign_set:
            I0 = tuple(sorted(I))
            inversions = len([(a, b) for a, b in combinations(I, 2) if a > b])
            self._var_sign[I] = (-1) ** inversions * self._var_sign[I0]
        return self._var_sign[I]

    def var_allowed_pattern(self, J, t) -> int:
        return self._var_allowed_pattern[(J, t)]

    def var_flippable_I_J(self, I, J) -> int:
        return self._var_flippable_I_J[(I, J)]

    def var_flippable(self, I) -> int:
        return self._var_flippable[I]

    def encode(self, *,
               nomutations: bool = False,
               isolatedone: bool = False,
               isolatedonetwo: bool = False,
               colorwithonered: bool = False,
               colorwithtwored: bool = False,
               test: bool = False,
               extendable_file: str | None = None):
        """Build all SAT constraints.

        Call this after construction to generate the full encoding.
        """
        needs_mutations = (nomutations or isolatedone or isolatedonetwo
                           or colorwithonered or colorwithtwored or test)
        if needs_mutations and not self.use_allowed_patterns:
            raise ValueError(
                "Mutation/coloring/test constraints require allowed-pattern "
                "encoding. Use --encoding allowedpatterns or --encoding both.")

        # Pattern constraints encode the chirotope axioms via precomputed
        # allowed sign patterns on (r+2)-element subsets.  This is used
        # for ALL encodings — the exchange-axiom SAT clauses alone are
        # insufficient for rank >= 4.
        self._add_pattern_constraints()
        if self.use_allowed_patterns:
            self._add_flippability_constraints()

        if not self.allow_cyclic:
            self._add_acyclicity_constraints()
        if self.symmetry:
            self._add_symmetry_breaking()

        if nomutations:
            self._add_no_mutations()
        if isolatedone:
            self._add_isolated_element(1)
        if isolatedonetwo:
            self._add_isolated_element(1)
            self._add_isolated_element(2)
        if colorwithonered:
            self._add_coloring_constraints(min_red=1)
        if colorwithtwored:
            self._add_coloring_constraints(min_red=2)
        if test:
            self._add_test_constraints()

    def _add_pattern_constraints(self):
        """Add allowed-pattern assignment constraints."""
        N, r = self.N, self.r
        packet_size = self.packet_size
        packet_range = self.packet_range
        packet_len = self.packet_len
        r_tuple_index = self.r_tuple_index
        r_tuples = self.r_tuples

        # Each packet-subset has exactly one allowed pattern
        for I in combinations(N, packet_size):
            self.constraints.append(
                [+self.var_allowed_pattern(I, t) for t in self.allowed_patterns]
            )

        # Pattern-to-sign consistency
        for J in combinations(N, packet_size):
            for t in self.allowed_patterns:
                tv = pattern_to_signs(t)
                if not self.bva:
                    for I_prime in combinations(packet_range, r):
                        self.constraints.append([
                            -self.var_allowed_pattern(J, t),
                            +tv[r_tuple_index[I_prime]] *
                            self.var_sign(*local_to_global_indices(I_prime, J))
                        ])
                self.constraints.append(
                    [+self.var_allowed_pattern(J, t)] +
                    [-tv[r_tuple_index[I_prime]] *
                     self.var_sign(*local_to_global_indices(I_prime, J))
                     for I_prime in combinations(packet_range, r)]
                )

            if self.bva:
                self._add_bva_for_packet(J)

    def _add_bva_for_packet(self, J):
        """Add BVA optimization constraints for packet J."""
        r = self.r
        packet_range = self.packet_range
        packet_len = self.packet_len
        r_tuples = self.r_tuples

        if not self.signotope:
            for i in range(0, packet_len - 1, 2):
                I = local_to_global_indices(r_tuples[i], J)
                I_next = local_to_global_indices(r_tuples[i + 1], J)
                for p in ["++", "--", "+-", "-+"]:
                    pv = pattern_to_signs(p)
                    self.constraints.append(
                        [-self._var_pair_signs[(J, i, p)], pv[0] * self.var_sign(*I)])
                    self.constraints.append(
                        [-self._var_pair_signs[(J, i, p)], pv[1] * self.var_sign(*I_next)])
                    for t in self.allowed_patterns:
                        if t[i] == p[0] and t[i + 1] == p[1]:
                            self.constraints.append(
                                [self._var_pair_signs[(J, i, p)],
                                 -self.var_allowed_pattern(J, t)])
        else:
            I_fst = local_to_global_indices(r_tuples[0], J)
            I_snd = local_to_global_indices(r_tuples[1], J)
            if self.packet_size % 2 == 1:
                I_trd = local_to_global_indices(r_tuples[2], J)
                start = 3
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "+++")], self.var_sign(*I_fst)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "+++")], self.var_sign(*I_snd)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "+++")], self.var_sign(*I_trd)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "---")], -self.var_sign(*I_fst)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "---")], -self.var_sign(*I_snd)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "---")], -self.var_sign(*I_trd)])
            else:
                start = 2
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "++")], self.var_sign(*I_fst)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "++")], self.var_sign(*I_snd)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "--")], -self.var_sign(*I_fst)])
                self.constraints.append(
                    [-self._var_pair_signs[(J, 0, "--")], -self.var_sign(*I_snd)])

            for i in range(start, packet_len - 1, 2):
                I = local_to_global_indices(r_tuples[i], J)
                I_next = local_to_global_indices(r_tuples[i + 1], J)
                for p in ["++", "--"]:
                    pv = pattern_to_signs(p)
                    self.constraints.append(
                        [-self._var_pair_signs[(J, i, p)], pv[0] * self.var_sign(*I)])
                    self.constraints.append(
                        [-self._var_pair_signs[(J, i, p)], pv[1] * self.var_sign(*I_next)])
                    for t in self.allowed_patterns:
                        if t[i] == p[0] and t[i + 1] == p[1]:
                            self.constraints.append(
                                [self._var_pair_signs[(J, i, p)],
                                 -self.var_allowed_pattern(J, t)])

    def _add_flippability_constraints(self):
        """Add flippability variable assignment constraints."""
        N, r = self.N, self.r
        packet_range = self.packet_range

        # Assign flippable_I_J variables
        for J in combinations(N, self.packet_size):
            for I_prime in combinations(packet_range, r):
                I = local_to_global_indices(I_prime, J)
                self.constraints.append(
                    [-self.var_flippable_I_J(I, J)] +
                    [+self.var_allowed_pattern(J, t)
                     for t in self.allowed_patterns_with_flippable_I[I_prime]]
                )
                for t in self.allowed_patterns_with_flippable_I[I_prime]:
                    self.constraints.append(
                        [+self.var_flippable_I_J(I, J),
                         -self.var_allowed_pattern(J, t)]
                    )

        # Assign global flippable variables
        for I in combinations(N, r):
            ext_count = 1 if self.signotope else 2
            I_extensions = [
                tuple(sorted(set(K) | set(I)))
                for K in combinations(set(N) - set(I), ext_count)
            ]
            for J in I_extensions:
                self.constraints.append(
                    [-self.var_flippable(I), +self.var_flippable_I_J(I, J)]
                )
            self.constraints.append(
                [+self.var_flippable(I)] +
                [-self.var_flippable_I_J(I, J) for J in I_extensions]
            )

    def _add_acyclicity_constraints(self):
        """Forbid the antipodal of a point in a simplex (acyclic oriented matroids)."""
        N, r = self.N, self.r
        for X in permutations(N, r + 1):
            for s in [+1, -1]:
                self.constraints.append([
                    +s * ((-1) ** i) * self.var_sign(*I)
                    for i, I in enumerate(combinations(X, r))
                ])

    def _add_symmetry_breaking(self):
        """Break symmetries: 0,...,r-3 on convex hull boundary, others sorted."""
        r, n = self.r, self.n
        for i, j in combinations(range(r - 2, n), 2):
            self.constraints.append([self.var_sign(*range(r - 2), i, j)])

    def _add_no_mutations(self):
        """Forbid all mutations."""
        for I in combinations(self.N, self.r):
            self.constraints.append([-self.var_flippable(I)])

    def _add_isolated_element(self, elem: int):
        """Forbid mutations involving a specific element."""
        for I in combinations(self.N, self.r):
            if elem in I:
                self.constraints.append([-self.var_flippable(I)])

    def _add_coloring_constraints(self, min_red: int):
        """Add 2-coloring constraints for mutation analysis."""
        N, r, n = self.N, self.r, self.n

        # Create red/blue variables
        self._var_red = {x: self.vpool.id() for x in N}

        if min_red == 1:
            # At least one red and one blue
            self.constraints.append([self._var_red[i] for i in range(n)])
            self.constraints.append([-self._var_red[i] for i in range(n)])
        elif min_red == 2:
            from pysat.card import CardEnc
            literals_red = [self._var_red[i] for i in range(n)]
            literals_notred = [-self._var_red[i] for i in range(n)]
            self.constraints += CardEnc.atleast(
                literals_red, bound=2, vpool=self.vpool).clauses
            self.constraints += CardEnc.atleast(
                literals_notred, bound=2, vpool=self.vpool).clauses

        # Mutation coloring: flippable tuples must be monochromatic
        for I in combinations(N, r):
            for x, y in permutations(I, 2):
                for s in [-1, 1]:
                    self.constraints.append([
                        -self.var_flippable(I),
                        s * self._var_red[x],
                        -s * self._var_red[y]
                    ])

    def _add_test_constraints(self):
        """Add hardcoded test mutation sets for known instances."""
        r, n = self.r, self.n
        N = self.N

        if r == 3 and n == 9:
            mutations = [
                (0, 1, 2), (0, 5, 6), (0, 3, 4), (0, 7, 8),
                (1, 4, 6), (1, 5, 8), (4, 5, 7), (3, 6, 8),
                (2, 6, 7), (2, 3, 5)
            ]
        elif r == 4 and n == 11:
            mutations = [
                (1, 2, 4, 5), (1, 2, 8, 9), (1, 3, 4, 6), (1, 3, 7, 8),
                (2, 3, 5, 6), (2, 3, 7, 9), (0, 4, 7, 10), (0, 5, 8, 10),
                (0, 6, 9, 10)
            ]
        else:
            return

        for I in combinations(N, r):
            if I in mutations:
                self.constraints.append([self.var_flippable(I)])
            else:
                self.constraints.append([-self.var_flippable(I)])

    def add_extension_constraints(self, chirotope_file: str):
        """Add constraints for extending chirotopes from n-1 to n elements.

        Reads chirotopes on n-1 elements from file and tries to extend each.
        Returns list of (chirotope_str, I, J, solutions) tuples.
        """
        r, n = self.r, self.n
        N = self.N
        N_minus_one = list(range(n - 1))
        results = []

        with open(chirotope_file) as f:
            for line in f:
                ch = pattern_to_signs(line.strip())
                constraints_ch = []
                i = 0
                for I in combinations(N_minus_one, r):
                    constraints_ch.append([ch[i] * self.var_sign(*I)])
                    i += 1

                for I_pair in combinations(N_minus_one, r - 1):
                    for J_pair in combinations(N_minus_one, r - 1):
                        if set(I_pair) & set(J_pair):
                            continue
                        I_ext = I_pair + (n - 1,)
                        J_ext = J_pair + (n - 1,)
                        constraints_IJ = [
                            [self.var_flippable(I_ext)],
                            [self.var_flippable(J_ext)],
                        ]
                        results.append((
                            self.constraints + constraints_ch + constraints_IJ,
                            I_ext, J_ext
                        ))

        return results

    def get_clauses(self) -> list[list[int]]:
        """Return the list of all clauses."""
        return self.constraints

    def write_cnf(self, filepath: str):
        """Write constraints in DIMACS CNF format."""
        with open(filepath, "w") as f:
            f.write(f"p cnf {self.vpool.top} {len(self.constraints)}\n")
            for c in self.constraints:
                f.write(" ".join(str(v) for v in c) + " 0\n")

        fp_vars = filepath + ".vars"
        with open(fp_vars, "w") as f:
            f.write(str(self.vpool.id2obj) + "\n")

    @property
    def num_vars(self) -> int:
        return self.vpool.top

    @property
    def num_clauses(self) -> int:
        return len(self.constraints)

    def sign_variable_ids(self) -> dict[tuple, int]:
        """Return mapping from sorted r-tuples to their sign variable IDs."""
        return {
            I: self._var_sign[I]
            for I in combinations(self.N, self.r)
        }

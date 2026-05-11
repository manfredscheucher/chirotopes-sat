"""SAT solving and solution enumeration for chirotope instances."""

from itertools import combinations

from .encoding import ChirotopeEncoder


def _make_solver():
    """Create a CaDiCaL SAT solver instance."""
    try:
        from pysat.solvers import Cadical153
        return Cadical153()
    except ImportError:
        from pysat.solvers import Cadical
        return Cadical()


def solve(encoder: ChirotopeEncoder, *, enumerate_all: bool = False):
    """Solve the encoded SAT instance and yield chirotope strings.

    Parameters
    ----------
    encoder : ChirotopeEncoder
        The encoder with constraints already built (call encode() first).
    enumerate_all : bool
        If True, enumerate all solutions. Otherwise yield at most one.

    Yields
    ------
    str
        Chirotope string of '+' and '-' characters for each solution.
    """
    solver = _make_solver()
    for c in encoder.get_clauses():
        solver.add_clause(c)

    N = encoder.N
    r = encoder.r

    while solver.solve():
        sol = set(solver.get_model())
        chi = {
            I: (+1 if encoder.var_sign(*I) in sol else -1)
            for I in combinations(N, r)
        }
        chi_str = "".join("+" if chi[I] == +1 else "-" for I in combinations(N, r))
        yield chi_str

        if not enumerate_all:
            break

        # Block this solution
        solver.add_clause([
            -chi[I] * encoder.var_sign(*I) for I in combinations(N, r)
        ])

    solver.delete()


def solve_extension(encoder: ChirotopeEncoder, chirotope_file: str, *,
                    enumerate_all: bool = False):
    """Solve extension problems: extend chirotopes from n-1 to n elements.

    Yields (I, J, chirotope_str) tuples for each solution found.
    """
    N = encoder.N
    r = encoder.r
    results = encoder.add_extension_constraints(chirotope_file)

    for clauses, I_ext, J_ext in results:
        solver = _make_solver()
        for c in clauses:
            solver.add_clause(c)

        ct = 0
        while solver.solve():
            sol = set(solver.get_model())
            chi_str = "".join(
                "+" if encoder.var_sign(*I) in sol else "-"
                for I in combinations(N, r)
            )
            ct += 1
            yield I_ext, J_ext, chi_str

            if not enumerate_all:
                break

            solver.add_clause([
                -(+1 if encoder.var_sign(*I) in sol else -1) * encoder.var_sign(*I)
                for I in combinations(N, r)
            ])

        solver.delete()


def write_solutions(solutions: list[str], filepath: str):
    """Write solution strings to a file."""
    with open(filepath, "w") as f:
        for s in solutions:
            f.write(s + "\n")

"""CNF file utilities: reading, unit propagation, proof verification."""

from ast import literal_eval
import random


def read_cnf(filepath: str) -> list[list[int]]:
    """Read a DIMACS CNF file and return list of clauses."""
    cnf = []
    with open(filepath) as f:
        for line in f:
            if not line.strip():
                continue
            if line[0] in ('c', 'p', 'a'):
                continue
            clause = [int(x) for x in line.split()]
            assert clause[-1] == 0
            del clause[-1]
            cnf.append(clause)
    return cnf


def read_proof(filepath: str) -> list[list[int]]:
    """Read a proof file (skipping deletion lines) and return list of clauses."""
    cnf = []
    with open(filepath) as f:
        for line in f:
            if not line.strip():
                continue
            if line[0] == 'd':
                continue
            clause = [int(x) for x in line.split()]
            assert clause[-1] == 0
            del clause[-1]
            cnf.append(clause)
    return cnf


def unit_propagate(cnf: list[list[int]]) -> list[list[int]]:
    """Perform unit propagation on a CNF formula.

    Modifies cnf in place. Returns the simplified CNF.
    Returns None if a conflict (empty clause) is found.
    """
    units = [c[0] for c in cnf if len(c) == 1]
    while units:
        x = units.pop(0)
        i = 0
        while i < len(cnf):
            if x in cnf[i] and cnf[i] != [x]:
                del cnf[i]
            elif -x in cnf[i]:
                cnf[i] = [y for y in cnf[i] if y != -x]
                if len(cnf[i]) == 1:
                    units.append(cnf[i][0])
                if len(cnf[i]) == 0:
                    return None
                i += 1
            else:
                i += 1
    return cnf


def verify_proof(cnf_file: str, proof_file: str, output_file: str, *,
                 var_file: str | None = None, shuffle: bool = False,
                 debug: int = 0):
    """Merge CNF and proof into incremental CNF format for verification.

    For each learned clause, creates a cube (assumptions) to check that the
    clause is implied by the original CNF.
    """
    cnf = read_cnf(cnf_file)
    proof = read_proof(proof_file)

    var = {}
    if var_file:
        var = literal_eval(open(var_file).readline())

    def var_lookup(x, unnamed=None):
        s = '+' if x > 0 else '-'
        a = abs(x)
        if a in var:
            return s + str(var[a])
        elif unnamed:
            return s + 'unnamed' + str(a)
        else:
            return None

    stats = {}
    with open(output_file, "w") as inccnf:
        inccnf.write("p inccnf\n")

        for c in cnf:
            inccnf.write(" ".join(str(x) for x in c) + " 0\n")

        if shuffle:
            random.shuffle(proof)

        for i, c in enumerate(proof):
            l = len(c)

            if debug >= 2:
                c_text = {var_lookup(x) for x in c}
                if None not in c_text and 3 <= l <= 3:
                    print(f"interesting learned clause #{i}: {c} {c_text}")

            if l == 2:
                inccnf.write("a " + " ".join(str(-x) for x in c) + " 0\n")

            if l not in stats:
                stats[l] = 0
            stats[l] += 1

    if debug:
        print("stats", {i: stats[i] for i in sorted(stats)})

    return stats


def cnf_to_inccnf(cnf_file: str, cubes_file: str, output_file: str, *,
                   use_cubevars: bool = False):
    """Convert CNF + cubes to incremental CNF format."""
    cnf = read_cnf(cnf_file)
    cubes = read_cnf(cubes_file)

    stats = {}
    with open(output_file, "w") as inccnf:
        inccnf.write("p inccnf\n")

        for c in cnf:
            inccnf.write(" ".join(str(x) for x in c) + " 0\n")

        for c in cubes:
            l = len(c)
            if l == 2:
                inccnf.write("a " + " ".join(str(-x) for x in c) + " 0\n")

            if l not in stats:
                stats[l] = 0
            stats[l] += 1

    return stats

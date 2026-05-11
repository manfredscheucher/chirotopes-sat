"""Command-line interface for chirotope enumeration."""

import argparse
import sys
from datetime import datetime
from itertools import combinations

from .encoding import ChirotopeEncoder
from .solver import solve, solve_extension, write_solutions
from .cnf_utils import read_cnf, unit_propagate, verify_proof, cnf_to_inccnf


def _log(*args):
    """Print with timestamp."""
    print(f"[{datetime.now()}]", *args)


def cmd_propagate(args):
    """Run unit propagation on a CNF file."""
    cnf = read_cnf(args.file)
    n_before = len(cnf)
    result = unit_propagate(cnf)
    if result is None:
        print(f"CONFLICT detected during unit propagation.")
        print(f"Clauses before: {n_before}")
        sys.exit(1)
    n_after = len(result)
    print(f"Clauses before: {n_before}")
    print(f"Clauses after:  {n_after}")
    print(f"Removed:        {n_before - n_after}")
    if args.output:
        max_var = max(abs(l) for c in result for l in c) if result else 0
        with open(args.output, "w") as f:
            f.write(f"p cnf {max_var} {len(result)}\n")
            for c in result:
                f.write(" ".join(str(l) for l in c) + " 0\n")
        print(f"Written to: {args.output}")


def cmd_verify_proof(args):
    """Merge CNF + DRAT proof into INCCNF for verification."""
    stats = verify_proof(
        args.cnf, args.proof, args.output,
        var_file=args.vars,
        shuffle=args.shuffle,
        debug=args.debug,
    )
    print(f"Written INCCNF to: {args.output}")
    print(f"Clause length distribution: {dict(sorted(stats.items()))}")


def cmd_cubify(args):
    """Convert CNF + cubes into INCCNF for Cube-and-Conquer."""
    stats = cnf_to_inccnf(args.cnf, args.cubes, args.output)
    print(f"Written INCCNF to: {args.output}")
    print(f"Cube length distribution: {dict(sorted(stats.items()))}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SAT-based chirotope enumeration tool"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- propagate subcommand ---
    sp_prop = subparsers.add_parser(
        "propagate", help="run unit propagation on a CNF file"
    )
    sp_prop.add_argument("file", help="input CNF file (DIMACS format)")
    sp_prop.add_argument("-o", "--output", help="write simplified CNF to file")
    sp_prop.set_defaults(func=cmd_propagate)

    # --- verify-proof subcommand ---
    sp_verify = subparsers.add_parser(
        "verify-proof",
        help="merge CNF + DRAT proof into INCCNF for verification",
    )
    sp_verify.add_argument("cnf", help="input CNF file")
    sp_verify.add_argument("proof", help="DRAT proof file")
    sp_verify.add_argument("output", help="output INCCNF file")
    sp_verify.add_argument("--vars", help="variable mapping file")
    sp_verify.add_argument("--shuffle", action="store_true",
                           help="shuffle proof clauses")
    sp_verify.add_argument("--debug", type=int, default=0,
                           help="debug level (0, 1, or 2)")
    sp_verify.set_defaults(func=cmd_verify_proof)

    # --- cubify subcommand ---
    sp_cube = subparsers.add_parser(
        "cubify",
        help="convert CNF + cubes into INCCNF for Cube-and-Conquer",
    )
    sp_cube.add_argument("cnf", help="input CNF file")
    sp_cube.add_argument("cubes", help="cubes file")
    sp_cube.add_argument("output", help="output INCCNF file")
    sp_cube.set_defaults(func=cmd_cubify)

    # --- enumerate subcommand (original main functionality) ---
    sp_enum = subparsers.add_parser(
        "enumerate", help="enumerate chirotopes via SAT solving"
    )
    sp_enum.add_argument("rank", type=int, help="rank of the chirotope")
    sp_enum.add_argument("n", type=int, help="number of elements")
    sp_enum.add_argument("-o", "--instance2file", type=str,
                         help="write CNF instance to file")
    sp_enum.add_argument("-e", "--extendable", type=str,
                         help="chirotope file for extension")
    sp_enum.add_argument("--solve", action='store_true',
                         help="solve the instance")
    sp_enum.add_argument("--nomutations", action='store_true',
                         help="no mutations allowed")
    sp_enum.add_argument("--isolatedone", action='store_true',
                         help="no mutations at element 1")
    sp_enum.add_argument("--isolatedonetwo", action='store_true',
                         help="no mutations at elements 1 or 2")
    sp_enum.add_argument("--colorwithonered", action='store_true',
                         help="2-colored mutations, at least 1 red")
    sp_enum.add_argument("--colorwithtwored", action='store_true',
                         help="2-colored mutations, at least 2 red")
    sp_enum.add_argument("--symmetry", action='store_true',
                         help="enable symmetry breaking")
    sp_enum.add_argument("--encoding",
                         choices=["allowedpatterns", "grassmannpluecker", "both"],
                         default="grassmannpluecker",
                         help="encoding: allowedpatterns (may be incomplete for "
                              "rank >= 4), grassmannpluecker, or both (default)")
    sp_enum.add_argument("--bva", action='store_true',
                         help="enable Bounded Variable Addition optimization")
    sp_enum.add_argument("--allowcyclic", action='store_true',
                         help="allow cyclic chirotopes (default: acyclic only)")
    sp_enum.add_argument("--test", action='store_true',
                         help="use hardcoded test mutation sets")
    sp_enum.add_argument("-a", "--all", action='store_true',
                         help="enumerate all solutions")
    sp_enum.add_argument("--enumerate", action='store_true',
                         help="print solutions during solving")
    sp_enum.add_argument("--signotope", action='store_true',
                         help="solve for signotopes instead of chirotopes")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Dispatch to subcommand handlers
    if args.command in ("propagate", "verify-proof", "cubify"):
        args.func(args)
        return

    # --- enumerate subcommand ---
    if not args.instance2file and not args.solve:
        print("Error: specify --solve or -o/--instance2file", file=sys.stderr)
        sys.exit(1)

    start_time = datetime.now()
    _log("args", args)

    if args.encoding == "allowedpatterns" and args.rank >= 4:
        _log("WARNING: --encoding allowedpatterns may produce incorrect results "
             "for rank >= 4. The allowed-pattern encoding is only proven "
             "sufficient for rank 3.")

    # Build encoder
    encoder = ChirotopeEncoder(
        args.rank, args.n,
        signotope=args.signotope,
        encoding=args.encoding,
        allow_cyclic=args.allowcyclic,
        symmetry=args.symmetry,
        bva=args.bva,
    )

    _log(f"there are {len(encoder.allowed_patterns)} allowed patterns")

    # Encode constraints
    if not args.extendable:
        encoder.encode(
            nomutations=args.nomutations,
            isolatedone=args.isolatedone,
            isolatedonetwo=args.isolatedonetwo,
            colorwithonered=args.colorwithonered,
            colorwithtwored=args.colorwithtwored,
            test=args.test,
        )
        _log(f"cnf was created")
        _log(f"{encoder.num_vars} vars and {encoder.num_clauses} constraints")

    # Write CNF
    if args.instance2file:
        _log("write CNF to file:", args.instance2file)
        encoder.write_cnf(args.instance2file)
        _log("write variables to file:", args.instance2file + ".vars")

    # Build output filename
    of = f"sols_{args.rank}_{args.n}"
    if args.nomutations:
        of += "_nomutations"
    if args.isolatedone:
        of += "_isolatedone"
    if args.isolatedonetwo:
        of += "_isolatedonetwo"
    if args.colorwithonered:
        of += "_coloronered"
    if args.colorwithtwored:
        of += "_coltwored"
    of += ".txt"

    # Solve
    start_solve = datetime.now()
    _log("start solving")
    ct = 0

    if args.solve and not args.extendable:
        solutions = []
        for chi_str in solve(encoder, enumerate_all=args.all):
            ct += 1
            solutions.append(chi_str)
            if args.enumerate:
                _log(f"solution {ct}: {chi_str}")

        if solutions:
            write_solutions(solutions, of)

        _log("finished solving")
        end_solve = datetime.now()
        _log(f"solving took {end_solve - start_solve}")
        _log(f"total time taken was {end_solve - start_time}")
        _log(f"found {ct} solutions")
        if solutions:
            _log("wrote solutions to file:", of)

    elif args.solve and args.extendable:
        encoder.encode(
            nomutations=args.nomutations,
            isolatedone=args.isolatedone,
            isolatedonetwo=args.isolatedonetwo,
            colorwithonered=args.colorwithonered,
            colorwithtwored=args.colorwithtwored,
            test=args.test,
        )
        for I_ext, J_ext, chi_str in solve_extension(
                encoder, args.extendable, enumerate_all=args.all):
            ct += 1
            if args.enumerate:
                _log(f"solution {ct}: I={I_ext} J={J_ext} {chi_str}")

        _log(f"found {ct} extension solutions")

    else:
        _log("instance will not be solved")


if __name__ == "__main__":
    main()

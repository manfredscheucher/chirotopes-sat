"""Command-line interface for chirotope enumeration."""

import argparse
import sys
from datetime import datetime
from itertools import combinations

from .encoding import ChirotopeEncoder
from .solver import solve, solve_extension, write_solutions


def _log(*args):
    """Print with timestamp."""
    print(f"[{datetime.now()}]", *args)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SAT-based chirotope enumeration tool"
    )
    parser.add_argument("rank", type=int, help="rank of the chirotope")
    parser.add_argument("n", type=int, help="number of elements")
    parser.add_argument("-o", "--instance2file", type=str,
                        help="write CNF instance to file")
    parser.add_argument("-e", "--extendable", type=str,
                        help="chirotope file for extension")
    parser.add_argument("--solve", action='store_true',
                        help="solve the instance")
    parser.add_argument("--nomutations", action='store_true',
                        help="no mutations allowed")
    parser.add_argument("--isolatedone", action='store_true',
                        help="no mutations at element 1")
    parser.add_argument("--isolatedonetwo", action='store_true',
                        help="no mutations at elements 1 or 2")
    parser.add_argument("--colorwithonered", action='store_true',
                        help="2-colored mutations, at least 1 red")
    parser.add_argument("--colorwithtwored", action='store_true',
                        help="2-colored mutations, at least 2 red")
    parser.add_argument("--symmetry", action='store_true',
                        help="enable symmetry breaking")
    parser.add_argument("--encoding",
                        choices=["allowedpatterns", "grassmannpluecker", "both"],
                        default="grassmannpluecker",
                        help="encoding: allowedpatterns (may be incomplete for "
                             "rank >= 4), grassmannpluecker, or both (default)")
    parser.add_argument("--bva", action='store_true',
                        help="enable Bounded Variable Addition optimization")
    parser.add_argument("--allowcyclic", action='store_true',
                        help="allow cyclic chirotopes (default: acyclic only)")
    parser.add_argument("--test", action='store_true',
                        help="use hardcoded test mutation sets")
    parser.add_argument("-a", "--all", action='store_true',
                        help="enumerate all solutions")
    parser.add_argument("--enumerate", action='store_true',
                        help="print solutions during solving")
    parser.add_argument("--signotope", action='store_true',
                        help="solve for signotopes instead of chirotopes")

    args = parser.parse_args(argv)

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

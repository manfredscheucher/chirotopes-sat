# Chirotopes

SAT-based enumeration of chirotopes (oriented matroids) using the Grassmann-Pluecker relations.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

Enumerate all acyclic rank-3 chirotopes on 5 elements (with symmetry breaking):

```bash
python -m chirotopes 3 5 --solve --all --symmetry --enumerate
```

Write a CNF instance to a file:

```bash
python -m chirotopes 3 6 -o instance.cnf
```

Find chirotopes without mutations:

```bash
python -m chirotopes 3 7 --solve --all --symmetry --nomutations --enumerate
```

## Usage

```
python -m chirotopes <rank> <n> [options]

positional arguments:
  rank                  rank of the chirotope
  n                     number of elements

options:
  --solve               solve the SAT instance
  -a, --all             enumerate all solutions
  --enumerate           print solutions during solving
  -o FILE               write CNF to DIMACS file
  --symmetry            enable symmetry breaking (fixes labeling)
  --grassmannpluecker   add global GP relations (default: on)
  --no-grassmannpluecker  use allowed patterns only (sufficient for rank 3)
  --nomutations         forbid all mutations
  --isolatedone         forbid mutations involving element 1
  --isolatedonetwo      forbid mutations involving elements 1 or 2
  --colorwithonered     2-coloring with at least 1 red element
  --colorwithtwored     2-coloring with at least 2 red elements
  --bva                 Bounded Variable Addition optimization
  --allowcyclic         allow cyclic chirotopes (default: acyclic only)
  --signotope           solve for signotopes instead of chirotopes
  --test                use hardcoded test mutation sets
  -e FILE               extend chirotopes from file
```

## SAT Encoding

The encoding assigns a sign variable `chi(I) in {+1, -1}` for each sorted r-subset I of {0,...,n-1}. For each (r+2)-subset J, the local pattern of signs must be one of the precomputed *allowed patterns* satisfying 3-term Grassmann-Pluecker relations.

By default, global GP relations are also added (`--grassmannpluecker`), which is the correct/complete encoding for all ranks. The allowed-pattern-only optimization (`--no-grassmannpluecker`) is sufficient for rank 3 but may be incomplete for rank >= 4.

## Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/ -v -m slow  # include slow tests
```

## Documentation

Mathematical background and detailed encoding description are in `docs/main.tex`.

## License

MIT

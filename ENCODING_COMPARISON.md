# Encoding Comparison: allowed patterns vs Grassmann-Pluecker

## Summary

Three encoding modes: `allowedpatterns`, `grassmannpluecker`, `both`.

All modes now use the same core mechanism: precomputed allowed sign patterns
on (r+2)-element subsets. The difference is that `allowedpatterns` (and `both`)
additionally creates flippability variables needed for mutation/coloring analysis.

All counts below are with `--symmetry` (relabeling broken) but **including reorientations**.
To compare with Finschi/Fukuda or OEIS, one must additionally factor out reorientation.

## Rank 3

| n | count |
|---|---|
| 3 | 1 |
| 4 | 2 |
| 5 | 8 |
| 6 | 62 |
| 7 | 908 |

The sequence 1, 2, 8, 62, 908 (with `--symmetry`, including reorientations)
corresponds to 2x the OEIS sequence https://oeis.org/A006245 (1, 1, 4, 31, 454, ...),
which counts acyclic rank-3 oriented matroids up to relabeling AND reorientation.

## Rank 4

| n | count |
|---|---|
| 4 | 1 |
| 5 | 4 |
| 6 | 80 |
| 7 | 5800 |

Finschi/Fukuda database: 11 non-degenerate (uniform) isomorphism classes for
rank 4, n=7 (up to relabeling AND reorientation). Our 5800 includes
reorientations and uses only partial symmetry breaking.

## Technical notes

### Allowed patterns

For rank r, the allowed patterns are precomputed sign configurations on
(r+2)-element subsets. These are stored in `src/chirotopes/data/`:

- `allowed_patterns3.txt`: 384 patterns (rank 3)
- `allowed_patterns4.txt`: 3584 patterns (rank 4)

### Exchange axiom vs allowed patterns for rank 4

The chirotope exchange axiom (B2') generates 3840 patterns for rank 4, but
only 3584 of those are valid chirotope patterns. The extra 256 patterns pass
the exchange axiom but violate the Grassmann-Pluecker relations. Using the
exchange axiom alone gives 9080 solutions for rank 4 n=7 instead of the
correct 5800.

The allowed-pattern files encode the correct, complete set of valid patterns.

## Default encoding

Default is `grassmannpluecker`. All encodings now give correct results for
all ranks.

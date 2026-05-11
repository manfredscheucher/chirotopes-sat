"""SAT-based chirotope enumeration tool."""

__version__ = "0.1.0"

from .core import (
    perm_sign,
    pattern_to_signs,
    evaluate_chirotope,
    satisfies_3term_gp,
    compute_allowed_patterns,
    flip_sign_at,
    local_to_global_indices,
)
from .encoding import ChirotopeEncoder
from .solver import solve, write_solutions

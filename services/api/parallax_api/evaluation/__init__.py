"""Protected evaluation spine for Parallax 2.0.

Optimizer-facing code should use ``load_optimizer_suite`` and development
metrics only. Promotion thresholds and decisions live in ``promotion.py`` and
must not be imported into optimizer-controlled DSPy programs.
"""

from .loader import load_optimizer_suite, load_suite
from .runner import evaluate_recorded_candidate

__all__ = ["evaluate_recorded_candidate", "load_optimizer_suite", "load_suite"]

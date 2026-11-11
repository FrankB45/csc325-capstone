"""Commit selection rules (pure logic, no Django/Mongo imports).

`history` is a list of full commit SHAs ordered oldest -> newest.
"""

MIN_SELECTED = 1
MAX_SELECTED = 10
RULE_MESSAGE = "Select between 1 and 10 commits to start capture."


class SelectionError(ValueError):
    def __init__(self, code, message=RULE_MESSAGE):
        super().__init__(message)
        self.code = code
        self.message = message


def default_selection(history):
    """AC1/AC2: up to 10 distinct commits spread across the history,
    always including first and last. <=10 commits -> all of them."""
    n = len(history)
    if n <= MAX_SELECTED:
        return list(history)
    # Evenly spaced indices, round-half-up using integers. Spacing is
    # (n-1)/9 >= 10/9 for n >= 11, so the 10 indices are always distinct.
    steps = MAX_SELECTED - 1
    indices = [(2 * i * (n - 1) + steps) // (2 * steps) for i in range(MAX_SELECTED)]
    return [history[i] for i in indices]


def validate_selection(selected, history):
    """AC4: enforce 1-10 distinct commits that belong to `history`.
    Returns the selection in history order."""
    if not isinstance(selected, list) or len(selected) < MIN_SELECTED:
        raise SelectionError("selection_empty")
    if len(selected) > MAX_SELECTED:
        raise SelectionError("selection_too_many")
    if len(set(selected)) != len(selected):
        raise SelectionError("selection_duplicate", "Each commit can only be selected once.")
    known = set(history)
    unknown = [s for s in selected if s not in known]
    if unknown:
        raise SelectionError("unknown_commit", "Selected commit is not part of this repository's history.")
    chosen = set(selected)
    return [sha for sha in history if sha in chosen]
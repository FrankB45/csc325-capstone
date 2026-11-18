# Git Gallery Commit Comparison Evaluation

This isolated, standard-library-only suite currently evaluates one AI feature:
comparing two selected commits using their before/after screenshots and
associated repository data. Commit grouping, individual summaries,
recommendations, and open-ended chat are outside the current evaluation scope.

## Files and prompt

- `golden_set.json` — 20 controlled, synthetic before/after commit fixtures
  with manually authored expected structured responses.
- `test_hallucination.py` — validates the comparison response structure,
  selected commit pair, required visible facts and limitations, and
  case-specific forbidden claims.
- `test_consistency.py` — compares three repeated analyses of the same pair.
- `llm_adapter.py` — single integration point; deterministic mock now and a
  future real adapter after the feature contract is finalized.
- `run_evaluation.py` — validates fixtures, runs both checks, reports
  thresholds, and returns a failing exit code when needed.
- `test_evaluation_logic.py` — focused infrastructure tests.
- System prompt: `backend/git_gallery_app/prompts/system_prompt.txt`.

## Structured response format

The golden set uses this proposed shape:

```json
{
  "before_commit_sha": "selected before commit",
  "after_commit_sha": "selected after commit",
  "changes": [
    {
      "element": "affected visible element",
      "before": "appearance in before screenshot",
      "after": "appearance in after screenshot",
      "evidence": "support from supplied screenshot observations"
    }
  ],
  "limitations": ["missing evidence or uncertainty"]
}
```

An empty `changes` list is appropriate when no visual difference is supported;
the output must explain that result or state the relevant limitation. The
project requirements call for descriptions of affected elements and their
visible before/after states, and explicit handling of no-difference results.
They do not define exact API field names, so this response schema remains a
proposal pending confirmation from the feature owner. The suite does not add
coordinates or image-highlight metadata because the repository does not
specify a structured location format.

## Evaluation checks

### Hallucination / grounding — 90% threshold

Checks that each response uses the proposed structure and identifies the exact
selected commit pair. It rejects unsupported commit identifiers, verifies
that reported before/after states match the manually defined reference, checks
case-specific visible differences and limitations, and flags listed
unacceptable claims. Incomplete screenshot or diff evidence should be reported
as a limitation rather than guessed or followed by a question.

Phrase-based checks are not a general semantic model and can miss unanticipated
fabrications. They do not prove that the provided screenshot observations
themselves are accurate. Human review remains necessary for actual model
results.

### Consistency — 80% threshold

Each pair is submitted three times with identical task and repository data.
The first response is reused for the grounding check. All three responses must
be grounded and agree on the selected commit pair, changed elements,
before/after states, and limitations. Change ordering is ignored. The check
does not require identical prose, but normalized structured values are a
lightweight approximation of semantic equivalence.

## Run

From the repository root, run the complete suite with one command:

```powershell
python backend\git_gallery_app\evaluation\run_evaluation.py
```

The default mock returns the manually authored expected outputs. A mock PASS
validates the evaluation infrastructure only; it is **not a real LLM result**.
Real mode fails explicitly until the feature owner provides an integration:

```powershell
python backend\git_gallery_app\evaluation\run_evaluation.py --mode real
```

Run the evaluation logic tests:

```powershell
python -m unittest discover -s backend\git_gallery_app\evaluation -p "test_*.py" -v
```

## Integration TODO

The feature owner still needs to confirm the request and structured response
contract. Then implement the real adapter in `llm_adapter.py` to pass the
selected pair and its repository/screenshot context, plus the prompt at
`backend/git_gallery_app/prompts/system_prompt.txt`. Keep credentials outside
source control, surface integration errors, and never fall back to mock
responses for real evaluation.

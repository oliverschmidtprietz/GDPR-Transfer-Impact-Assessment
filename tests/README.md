# TIA ↔ RoPA interchange contract tests

Executable contract for the delta format TIA emits and RoPA consumes. These
tests are the reason the two skills can be released independently without the
contract silently drifting apart.

## Running them

The suite needs `pytest` and `jsonschema`. There is no dependency manifest in
this repo, so the reliable invocation is:

```bash
uv run --with pytest --with jsonschema python -m pytest skills/ropa/validator skills/tia/tests -q
```

Run from the repository root. A bare `python3 -m pytest` fails with
`ModuleNotFoundError: No module named 'jsonschema'` unless that package happens
to be installed in the active environment.

Expected: **127 passed** (100 RoPA validator + 27 interchange contract).

## What these tests guard

Under inbound schema **2.0**:

- `add` **upserts** — it writes regardless of leaf presence, and `replace` is an
  exact synonym. The producer never reads RoPA's sidecar to choose an operation,
  and a re-sent delta is idempotent.
- **The allowed-path set is the primary guard.** Because `add` is permissive,
  the path pattern in `ropa/references/interchange-inbound-schema.json` is the
  only thing preventing a stale producer from writing unrecognised fields into a
  user's register.
- **`expected_post_state` is a precondition**, not a warning. A mismatch rejects
  the whole delta. This is where determinism lives.

Every assertion about what TIA emits is derived from the **documented example**
in `tia/references/interchange-delta.md` — the artifact a model actually copies
at runtime — and that example is applied through the applier. Asserting over
test-only fixtures would be a tautology over test data, which is exactly how the
previous version of this suite stayed green while the defect it targeted was
live.

## Proving the suite can fail

A green suite is not evidence on its own. Before trusting a change here, mutate
the contract and confirm the suite goes red:

1. **Corrupt a path.** In `interchange-delta.md`, change a patch `path` to one
   outside the allowed-path set (e.g. `/transfers/0/tia_review_date`).
   → expect ~10 failures.
2. **Break a precondition.** Change an `expected_post_state.values` entry to a
   value the base fixture does not hold (e.g. `mechanism` → `adequacy`).
   → expect ~5 failures.

Restore the file afterwards. Flipping `add` ↔ `replace` is **not** a valid probe
any more: under 2.0 those operations are deliberately equivalent.

# TIA → RoPA Interchange Delta Format

This file documents how the TIA skill optionally emits delta files that update RoPA's register. It conforms to RoPA's `interchange-inbound-schema.json` **v2.0** (defined in `skills/ropa/references/interchange-inbound-schema.md`). A TIA remains a complete standalone assessment when no RoPA exchange is requested.

The TIA skill produces ONE delta file per assessed transfer that is linked to a RoPA activity.

---

## File Location and Naming

Delta files are written to:

```
skills/ropa-workspace/<org-slug>/inbound/tia-<target-activity-id>-<timestamp>.delta.json
```

Where:
- `<org-slug>` — slug for the organisation (e.g. `acme-gmbh`)
- `<target-activity-id>` — UUID of the RoPA ActivityEntry / ProcessorEntry being updated
- `<timestamp>` — ISO 8601 with hour-minute precision (e.g. `2026-05-28T1430+0200`)

Example: `tia-9a7fa4c8-3b0a-4f9d-a5d6-8e2b7a0f9c12-2026-05-28T1430+0200.delta.json`

---

## Delta File Structure

```json
{
  "schema_version": "2.0",
  "source_skill": "tia v<X.Y>",
  "produced_at": "2026-05-28T14:30:00+02:00",
  "target_activity_id": "9a7fa4c8-3b0a-4f9d-a5d6-8e2b7a0f9c12",
  "target_entry_type": "controller_activity",
  "patches": [
    {
      "op": "add",
      "path": "/transfers/0/tia_ref",
      "value": "TIA-US-2026-001",
      "field_label": "TIA reference"
    },
    {
      "op": "add",
      "path": "/transfers/0/tia_date",
      "value": "2026-05-28",
      "field_label": "TIA completion date"
    }
  ],
  "context": {
    "summary": "TIA completed for US transfer via SCCs Module 2. Step 3 conclusion: transfer tool not effective, supplementary measures required. Proceed with TM-1 + CM-1 + CM-2.",
    "rationale_doc": "skills/tia-workspace/acme-gmbh/TIA-US-2026-001.docx",
    "rationale_doc_sha256": "3b8c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e",
    "output_links": [
      "skills/tia-workspace/acme-gmbh/TIA-US-2026-001.md"
    ]
  },
  "expected_post_state": {
    "values": {
      "/transfers/0/tia_ref": "TIA-US-2026-001",
      "/transfers/0/mechanism": "sccs"
    }
  }
}
```

---

## Field Reference

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | Always `"2.0"` for the current RoPA inbound schema |
| `source_skill` | yes | `"tia v<X.Y>"` — `<X.Y>` read from this skill's own `SKILL.md` frontmatter `version:` at emission time, never hardcoded (Producer-Side Responsibilities #2) |
| `produced_at` | yes | Envelope timestamp: ISO 8601 with timezone. RoPA derives inbound provenance date as `produced_at[0:10]`. |
| `target_activity_id` | yes | UUID — must exist in target RoPA sidecar |
| `target_entry_type` | no | `controller_activity` (default) or `processor_activity` |
| `patches` | yes | RFC 6902 subset. Emit `add` for every leaf — it upserts. |
| `context.summary` | yes | One sentence — surfaces in RoPA docx and session log |
| `context.rationale_doc` | yes | Path to the formal TIA .docx |
| `context.rationale_doc_sha256` | recommended | Tamper-evidence |
| `context.output_links` | optional | Additional artefacts (e.g. markdown report) |
| `expected_post_state` | recommended | Precondition. A mismatch rejects the whole delta — see below. |

---

## Canonical RoPA Fields and Write Semantics

TIA emits exactly two transfer patches:

- `/transfers/N/tia_ref` — pointer to the completed TIA artifact.
- `/transfers/N/tia_date` — ISO date on which that assessment was completed.

**Always emit `add`.** Under inbound schema 2.0 `add` upserts: it writes the value whether or not the leaf is already there. There is no first-write / later-write distinction and no need to inspect the target transfer to choose an operation. A re-assessment emits exactly the same two `add` patches with updated values; re-sending an unchanged delta is idempotent.

(`replace` is accepted by RoPA as an exact synonym, so a delta built by a standard JSON-Patch library still applies. Prefer `add`.)

TIA status, next-review date, and supplementary-measure detail are intentionally not duplicated into RoPA transfer fields. Keep them in the signed TIA artifact and surface the decision in `context.summary` and supporting links. **These paths are outside RoPA's allowed-path set — emitting them rejects the whole delta.** The retired fields are `/transfers/N/tia_status`, `/transfers/N/supplementary_measures`, `/transfers/N/tia_completed_date` and `/transfers/N/tia_review_date`; `tia` v1.1 emitted all four.

## Preconditions

`expected_post_state.values` maps a JSON Pointer to the value expected after the patches apply. RoPA rejects the whole delta on any mismatch. Determinism lives here, not in the operation name.

Include the canonical leaves the delta sets, and — when the TIA was based on a sidecar read — one field the delta does *not* patch (e.g. `/transfers/0/mechanism`). That second form is the concurrent-edit check: if the register changed between the read and the merge, the delta is rejected instead of applied over a moved target.

---

## Producer-Side Responsibilities

The TIA skill:
1. Reads the RoPA sidecar to confirm the `target_activity_id` exists and to identify the transfer index `N`.
2. Sets the envelope's `source_skill` to `"tia v<X.Y>"` where `<X.Y>` is read from **this skill's own `SKILL.md` frontmatter `version:` field at the moment of emission** — never a hardcoded or remembered literal, and never copied from a historical mention elsewhere in this document (e.g. the "retired fields" note below cites what a past shipped version, `tia v1.1`, used to emit — that is a fact about history, not a template to reuse). A stale literal here (run-4 defect: a delta emitted while running `tia v1.7` declared `source_skill: "tia v1.1"`) propagates verbatim into RoPA's `transfers_provenance.source`, permanently misrecording the producer version on the register side, and nothing on either validator side checks it.
3. Emits `add` for each canonical leaf. It does **not** inspect leaf presence — `add` upserts, so the producer stays stateless with respect to RoPA's current values.
4. Emits the delta only after the TIA is signed off (Section 6 of the .docx complete). `tia_date` is that sign-off's completion date — `step5_6.sign_off.dpo.date` in the sidecar, not the assessment's start date or any other date on the form.
5. Writes the file atomically (temp file + rename).
6. Computes the SHA-256 of the rationale doc and includes it in the delta.
7. Does NOT delete or modify any prior deltas.
8. Sets the TIA sidecar's own `ropa_delta.emitted: true` and `ropa_delta.delta_ref` to the exact path of the file just written (relative to the sidecar's own directory — an absolute path is also accepted and taken as-is), BEFORE running the validator with `--delta` pointed at that same file. `delta_ref` must resolve to the real file passed via `--delta`; it is never a description of one. DELTA-FILE-REQUIRED (rejection, non-overridable) checks this at validation time: an `emitted: true` claim with no `--delta` supplied, or a `delta_ref` that does not resolve to the file actually passed, blocks the run outright. This was previously a warning (`DELTA-REF-MISSING`) — as of 2026-09-18 it is a mandatory, non-overridable gate.

Once written, the delta is owned by RoPA. RoPA's merge mode will read, validate, apply, and move the file to `inbound/applied/` or `inbound/rejected/` accordingly. RoPA's own `TRANS-TIA-DELTA` rule independently requires this same delta to exist, in `inbound/` or `inbound/applied/`, before it will accept a new or changed `tia_ref`/`tia_date` on the register side — the file is checked at BOTH ends of the handoff, not just this one.

**The `applied/` move does not make `delta_ref` stale (fixed 2026-09-24, run-4 defect).** After a successful merge, ropa moves the file from `<inbound>/X.delta.json` to `<inbound>/applied/X.delta.json` — the sidecar's own documented behaviour, not something the TIA producer can prevent. `DELTA-FILE-REQUIRED` tolerates exactly this move: it also passes when the `--delta` path supplied is `<delta_ref's directory>/applied/<same filename>`, or, symmetrically, when `delta_ref` already names the `applied/` location and `--delta` is re-run against the original pre-move path. There is no need, and no separate instruction, to edit `delta_ref` after the move — the tolerance is filename-scoped to that one `applied/` sibling only; a different filename, or any other sibling directory, still rejects.

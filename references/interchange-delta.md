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
| `source_skill` | yes | `"tia v<X.Y>"` |
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
2. Emits `add` for each canonical leaf. It does **not** inspect leaf presence — `add` upserts, so the producer stays stateless with respect to RoPA's current values.
3. Emits the delta only after the TIA is signed off (Section 6 of the .docx complete).
4. Writes the file atomically (temp file + rename).
5. Computes the SHA-256 of the rationale doc and includes it in the delta.
6. Does NOT delete or modify any prior deltas.

Once written, the delta is owned by RoPA. RoPA's merge mode will read, validate, apply, and move the file to `inbound/applied/` or `inbound/rejected/` accordingly.

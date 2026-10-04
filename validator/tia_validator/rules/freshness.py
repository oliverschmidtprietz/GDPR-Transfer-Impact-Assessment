"""Freshness rules 13-15 (DPF-EVIDENCE, REVIEW-DATE, SRC-FRESH) — spec §5.1
rows 13-15.

All three rules are severity "warning" — aging/currency concerns never gate
(design spec §5.1: "aging ⇒ warning (13-15)"; §12 confirms rule 12's
downgrade did not touch 13-15). Documentation-not-correctness still applies:
these rules check that currency/review evidence is recorded, never whether
the underlying legal conclusion is still right.

SRC-FRESH ports toms-art32's SRC-1 (validator/tia_validator/rules/sources.py
in that skill — see its module docstring), which itself mirrors ropa's
M-FRESH-SOURCES. All rules are pure functions (sidecar, ctx) -> list[Finding]
and tolerate arbitrarily malformed input via .get() chains / isinstance
guards / try-except around date parsing — they must never raise.
"""
import datetime as _dt
import json
from pathlib import Path

from ..findings import Finding
from ..registry import rule

_SPEC_DPF = "SKILL.md#legal-precision-points"
_SPEC_REVIEW = "references/tia-template.md#section-6"
_SPEC_SRC_FRESH = "sources.lock.json#freshness"

_REVIEW_MAX_DAYS = 366
_STALE_AFTER_DAYS = 365


def _non_empty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


@rule(id="DPF-EVIDENCE", severity="warning", category="freshness",
      description="step2.dpf_reliance, if present, carries non-empty "
                  "scope_evidence and currency_evidence — not a bare "
                  "assertion of DPF coverage. Also fires when mechanism is "
                  "'adequacy', destination_country is 'US', and no "
                  "dpf_reliance block is present at all: the EU has no "
                  "general US adequacy decision, only the Data Privacy "
                  "Framework for certified recipients (Implementing Decision "
                  "(EU) 2023/1795), so an 'adequacy' claim for the US with no "
                  "DPF block is a bare assertion by omission, not just an "
                  "incomplete one (break-it 2026-10-02, fixes a short-circuit "
                  "where dpf_reliance is None was treated as 'nothing to "
                  "check' regardless of mechanism/destination).",
      spec_anchor=_SPEC_DPF)
def dpf_evidence(sidecar, ctx):
    step2 = sidecar.get("step2") if isinstance(sidecar, dict) else None
    step2 = step2 if isinstance(step2, dict) else {}
    dpf = step2.get("dpf_reliance")

    if dpf is None:
        step1 = sidecar.get("step1") if isinstance(sidecar, dict) else None
        step1 = step1 if isinstance(step1, dict) else {}
        destination = step1.get("destination_country")
        is_us_adequacy_claim = (
            step2.get("mechanism") == "adequacy"
            and isinstance(destination, str)
            and destination.strip().upper() == "US")
        if not is_us_adequacy_claim:
            return []
        return [Finding(
            rule_id="DPF-EVIDENCE", category="freshness", severity="warning",
            message="step2.mechanism is 'adequacy' with destination_country "
                    "'US' but step2.dpf_reliance is absent — the EU has no "
                    "general US adequacy decision, only the Data Privacy "
                    "Framework for certified recipients; record the "
                    "dpf_reliance block with scope_evidence and "
                    "currency_evidence, not a bare 'US adequacy' claim.",
            spec_anchor=_SPEC_DPF, field="dpf_reliance")]

    dpf = dpf if isinstance(dpf, dict) else {}
    missing = [f for f in ("scope_evidence", "currency_evidence")
               if not _non_empty_str(dpf.get(f))]
    if missing:
        return [Finding(
            rule_id="DPF-EVIDENCE", category="freshness", severity="warning",
            message=f"step2.dpf_reliance is present but missing: "
                    f"{', '.join(missing)} — a bare assertion of DPF "
                    "coverage without evidence.",
            spec_anchor=_SPEC_DPF, field=missing[0])]
    return []


@rule(id="REVIEW-DATE", severity="warning", category="freshness",
      description="step5_6.next_review_date is present and on or after "
                  "cover.date (a negative interval is a rejection); an "
                  "interval of more than 12 months since cover.date "
                  "requires a recorded review_interval_rationale.",
      spec_anchor=_SPEC_REVIEW)
def review_date(sidecar, ctx):
    step5_6 = sidecar.get("step5_6") if isinstance(sidecar, dict) else None
    step5_6 = step5_6 if isinstance(step5_6, dict) else {}
    next_review = step5_6.get("next_review_date")

    if not _non_empty_str(next_review):
        return [Finding(
            rule_id="REVIEW-DATE", category="freshness", severity="warning",
            message="step5_6.next_review_date is missing or empty.",
            spec_anchor=_SPEC_REVIEW, field="next_review_date")]

    cover = sidecar.get("cover") if isinstance(sidecar, dict) else None
    cover = cover if isinstance(cover, dict) else {}
    cover_date = cover.get("date")

    try:
        review_d = _dt.date.fromisoformat(next_review)
        cover_d = _dt.date.fromisoformat(cover_date)
    except (TypeError, ValueError):
        return [Finding(
            rule_id="REVIEW-DATE", category="freshness", severity="warning",
            message=f"step5_6.next_review_date {next_review!r} or "
                    f"cover.date {cover_date!r} is not a parseable ISO date "
                    "— cannot compute the review interval.",
            spec_anchor=_SPEC_REVIEW, field="next_review_date")]

    interval_days = (review_d - cover_d).days
    if interval_days < 0:
        return [Finding(
            rule_id="REVIEW-DATE", category="freshness", severity="rejection",
            message=f"step5_6.next_review_date {next_review} is "
                    f"{-interval_days} day(s) before cover.date {cover_date} "
                    "— a review scheduled before the assessment it reviews.",
            spec_anchor=_SPEC_REVIEW, field="next_review_date")]
    if interval_days > _REVIEW_MAX_DAYS:
        rationale = step5_6.get("review_interval_rationale")
        if not _non_empty_str(rationale):
            return [Finding(
                rule_id="REVIEW-DATE", category="freshness", severity="warning",
                message=f"step5_6.next_review_date is {interval_days} days "
                        f"after cover.date (> {_REVIEW_MAX_DAYS}) with no "
                        "recorded review_interval_rationale.",
                spec_anchor=_SPEC_REVIEW, field="review_interval_rationale")]
    return []


def _default_manifest_path(ctx) -> Path:
    return ctx.references_dir.parent / "sources.lock.json"


def _validate_shape(manifest, source_desc):
    """A parsed manifest is only usable if it is a JSON object, and its
    "files" key (when present) is itself a JSON object — .keys()/.items()
    are called on both below, so a bare list (or any other non-dict shape)
    must be rejected here, before use, rather than allowed to raise
    AttributeError deeper in the rule (mirrors toms-art32 SRC-1)."""
    if not isinstance(manifest, dict):
        return None, f"{source_desc} is not a JSON object (got {type(manifest).__name__})"
    files = manifest.get("files")
    if files is not None and not isinstance(files, dict):
        return None, f"{source_desc}['files'] is not a JSON object (got {type(files).__name__})"
    return manifest, None


def _load_manifest(ctx):
    """Returns (manifest_dict_or_None, error_message_or_None).
    ctx.sources_lock_override (fixture testing) takes precedence over the
    on-disk sources.lock.json. Malformed shape is treated the same as
    missing/unreadable — reported as an error, never returned as usable —
    for both paths."""
    override = getattr(ctx, "sources_lock_override", None)
    if override is not None:
        return _validate_shape(override, "ctx.sources_lock_override")
    manifest_path = _default_manifest_path(ctx)
    if not manifest_path.exists():
        return None, f"sources.lock.json not found at {manifest_path}"
    try:
        parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"sources.lock.json at {manifest_path} could not be read/parsed: {exc}"
    return _validate_shape(parsed, str(manifest_path))


def _on_disk_reference_keys(ctx):
    """references/<relpath> keys for every *.md file under
    ctx.references_dir, recursive (so references/country-profiles/*.md is
    included alongside the top-level files)."""
    if not ctx.references_dir.exists():
        return set()
    keys = set()
    for path in ctx.references_dir.rglob("*.md"):
        rel = path.relative_to(ctx.references_dir)
        keys.add(f"references/{rel.as_posix()}")
    return keys


@rule(id="SRC-FRESH", severity="warning", category="freshness",
      description="sources.lock.json must declare every on-disk "
                  "references/**/*.md file, and every declared entry's "
                  "last_verified must be within the last 12 months. "
                  "Mirrors ropa's M-FRESH-SOURCES / toms-art32's SRC-1.",
      spec_anchor=_SPEC_SRC_FRESH)
def src_fresh(sidecar, ctx):
    out = []
    manifest, error = _load_manifest(ctx)
    if manifest is None:
        out.append(Finding(
            rule_id="SRC-FRESH", category="freshness", severity="warning",
            message=f"sources.lock.json could not be loaded: {error}",
            spec_anchor=_SPEC_SRC_FRESH,
            fix_hint="Author skills/tia/sources.lock.json (mirrors ropa's / "
                     "toms-art32's shape) covering every references/**/*.md "
                     "file."))
        return out

    declared = set((manifest.get("files") or {}).keys())
    on_disk = _on_disk_reference_keys(ctx)

    for missing in sorted(on_disk - declared):
        out.append(Finding(
            rule_id="SRC-FRESH", category="freshness", severity="warning",
            entry_type="reference_file", entry_id=missing, field="files",
            message=f"{missing} exists on disk but has no entry in "
                    "sources.lock.json.",
            spec_anchor=_SPEC_SRC_FRESH,
            fix_hint=f"Add a files['{missing}'] entry to sources.lock.json "
                     "(source_type, jurisdiction, url, last_verified, "
                     "confidence, owner)."))

    today = _dt.date.today()
    threshold = today - _dt.timedelta(days=_STALE_AFTER_DAYS)
    for path, entry in (manifest.get("files") or {}).items():
        if not isinstance(entry, dict):
            continue  # a malformed entry is a shape problem, not this rule's concern
        last_verified = entry.get("last_verified")
        if not isinstance(last_verified, str):
            continue
        try:
            verified_date = _dt.date.fromisoformat(last_verified)
        except ValueError:
            continue
        if verified_date < threshold:
            age_days = (today - verified_date).days
            out.append(Finding(
                rule_id="SRC-FRESH", category="freshness", severity="warning",
                entry_type="manifest_entry", entry_id=path, field="last_verified",
                message=(f"sources.lock.json entry '{path}' has "
                          f"last_verified={last_verified} ({age_days} days "
                          f"ago, > {_STALE_AFTER_DAYS}-day threshold)."),
                spec_anchor=_SPEC_SRC_FRESH,
                fix_hint=f"Re-verify {path} against its source and update "
                         f"sources.lock.json files['{path}'].last_verified."))
    return out

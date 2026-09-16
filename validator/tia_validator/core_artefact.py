"""Project a native tia sidecar into the portfolio core artefact (task 9).

A PROJECTION, not a rewrite (D-WS3-06): the native sidecar is never modified
or restructured. This mirrors ropa's and toms-art32's adapters in structure
and signature — `to_core_artefact(sidecar, *, skill_version) -> dict` — but
diverges from both in two ways design spec §6 calls out explicitly:

1. tia emits `artefact_schema_version: "1.1"` with a **typed subject**
   (`type: "transfer"`) — it is the format's first 1.1 emitter. The two
   shipped adapters still emit "1.0" without a type; that is untouched here.
2. tia populates `sources[]`, `handoffs[]` and `unknowns[]` from day one.
   Both shipped adapters emit empty literals there (a disclosed gap in the
   standard, gap 8) — a new adopter must meet the written §6/§7 requirement
   rather than inherit the gap.

`handoffs[]` names `ropa` only when `ropa_delta.emitted` is true AND
`delta_ref` is a non-empty string (amendment 2026-08-11): an emission claim
without a reference is never advertised as a handoff — it already surfaces
as the DELTA-REF-MISSING warning, which the projection carries in gaps[]
via the live validation.findings[] block. "Parcel sent" needs a parcel
reference.

The core artefact is always writable, even when the document is blocked
(spec §5.3) — a `blocked` artefact is itself a legitimate handoff signal.
Sign-off gates only the ropa interchange delta (rule 6), never this
emission, so every function here tolerates arbitrarily malformed input via
.get() chains / isinstance guards and must never raise.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ARTEFACT_SCHEMA_VERSION = "1.1"
SKILL_NAME = "tia"

_OUTCOME_BY_VALIDATION_STATUS = {
    "passed": "complete",
    "passed_with_warnings": "provisional",
    "passed_with_override": "provisional",
    "failed": "blocked",
}
# skill-artefact-1.1.schema.json's outcome.status enum is exactly
# ["complete", "provisional", "blocked"] — there is no dedicated
# conditional/incomplete value (task brief, 2026-09-15: do not edit the
# standard's schema for this). A `proceed_with_conditions` decision with any
# open conditions[] entry is therefore mapped to the closest existing
# non-complete value, "provisional" — reached via the ordinary mapping
# above because DECISION-CONDITIONS reports open conditions at severity
# "warning" (validation.status "passed_with_warnings"), not because of any
# special case here. A controller wanting a real "conditional" outcome
# value would need to extend the standard's schema; that is out of scope
# for this skill's projection.

_UNKNOWN_TRANSFER_ID = "unknown-transfer"

# Destination-country -> country-profile lock key stem (task-9-brief.md).
# "US" is handled separately (us-dpf vs us-non-dpf, keyed off step2.dpf_reliance);
# any unmapped country falls back to "generic-assessment".
_PROFILE_BY_COUNTRY = {
    "AE": "ae", "AU": "au", "BR": "br", "CN": "cn", "IN": "in", "RU": "ru",
    "SG": "sg", "TR": "tr", "ZA": "za", "GB": "uk-post-adequacy",
}

_HANDOFF_REASON = ("TIA outcome recorded against the RoPA transfer row via "
                    "the inbound-schema-2.0 delta.")

_ONWARD_UNKNOWN_QUESTION = (
    "Onward transfer declared but no child assessment ref recorded — each "
    "hop needs its own Chapter V analysis.")

_MECHANISM_UNKNOWN_QUESTION = (
    "Transfer mechanism is not yet documented — the Chapter V basis must "
    "be resolved before sign-off.")


def _now() -> str:
    return (datetime.now(timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _dict_or_empty(value) -> dict:
    return value if isinstance(value, dict) else {}


def _non_empty_str(value) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _slugify(value: str) -> str:
    """Portfolio slugify convention (PORTFOLIO-STANDARD.md, "the slugify
    convention"): lowercase; collapse every run of non-alphanumeric
    characters to a single `-`; strip leading/trailing `-`. Identity on
    already-conforming values, so a well-formed org_slug is unchanged.
    Deliberately a local equivalent, not an import from toms-art32's
    `_slugify` — skills stay independent."""
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _subject(sidecar: dict) -> dict:
    cover = _dict_or_empty(sidecar.get("cover"))
    subject_id = _non_empty_str(cover.get("tia_ref")) or _UNKNOWN_TRANSFER_ID
    label = _non_empty_str(cover.get("title")) or subject_id
    subject = {"id": subject_id, "label": label, "type": "transfer"}
    org_slug = _non_empty_str(cover.get("org_slug"))
    if org_slug:
        slug = _slugify(org_slug)
        if slug:
            subject["org"] = slug
    return subject


def _outcome(sidecar: dict) -> dict:
    validation = _dict_or_empty(sidecar.get("validation"))
    status = validation.get("status")
    outcome_status = _OUTCOME_BY_VALIDATION_STATUS.get(status, "blocked")

    cover = _dict_or_empty(sidecar.get("cover"))
    step1 = _dict_or_empty(sidecar.get("step1"))
    step2 = _dict_or_empty(sidecar.get("step2"))
    tia_ref = _non_empty_str(cover.get("tia_ref")) or _UNKNOWN_TRANSFER_ID
    status_word = _non_empty_str(status) or "unknown"
    country = _non_empty_str(step1.get("destination_country")) or "unknown"
    mechanism = _non_empty_str(step2.get("mechanism")) or "unknown"
    summary = (f"TIA {tia_ref}: {status_word} — {country} transfer via "
              f"{mechanism}.")
    return {"status": outcome_status, "summary": summary}


def _gaps(sidecar: dict) -> list:
    validation = _dict_or_empty(sidecar.get("validation"))
    out = []
    for f in validation.get("findings") or []:
        if not isinstance(f, dict):
            continue
        item = {
            "id": f.get("rule_id") or "gap",
            "severity": f.get("severity", "info"),
            "message": f.get("message", ""),
        }
        fix_hint = _non_empty_str(f.get("fix_hint"))
        if fix_hint:
            item["fix_hint"] = fix_hint
        out.append(item)
    return out


def _load_lock_files() -> dict:
    lock_path = Path(__file__).resolve().parents[2] / "sources.lock.json"
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _dict_or_empty(data.get("files"))


def _selected_source_keys(sidecar: dict) -> list:
    step1 = _dict_or_empty(sidecar.get("step1"))
    step2 = _dict_or_empty(sidecar.get("step2"))

    country = _non_empty_str(step1.get("destination_country"))
    country = country.strip().upper() if country else ""
    if country == "US":
        profile = "us-dpf" if step2.get("dpf_reliance") is not None else "us-non-dpf"
    else:
        profile = _PROFILE_BY_COUNTRY.get(country, "generic-assessment")
    profile_key = f"references/country-profiles/{profile}.md"

    mechanism = step2.get("mechanism")
    mechanism_key = ("references/art49-derogations.md" if mechanism == "art49"
                     else "references/edpb-six-steps.md")

    keys = [profile_key]
    if mechanism_key not in keys:
        keys.append(mechanism_key)
    return keys


def _sources(sidecar: dict) -> list:
    lock_files = _load_lock_files()
    out = []
    for key in _selected_source_keys(sidecar):
        entry = lock_files.get(key)
        if not isinstance(entry, dict):
            continue  # a selected key absent from the lock is skipped, never invented
        url = entry.get("url")
        citation = key + (f" — {url}" if url else "")
        out.append({
            "id": key,
            "citation": citation,
            "last_verified": entry.get("last_verified", ""),
        })
    return out


def _handoffs(sidecar: dict) -> list:
    ropa_delta = _dict_or_empty(sidecar.get("ropa_delta"))
    delta_ref = _non_empty_str(ropa_delta.get("delta_ref"))
    if ropa_delta.get("emitted") is True and delta_ref:
        return [{
            "sibling_skill": "ropa",
            "reason": _HANDOFF_REASON,
            "payload_ref": delta_ref,
        }]
    return []


def _unknowns(sidecar: dict) -> list:
    out = []

    step1 = _dict_or_empty(sidecar.get("step1"))
    onward = _dict_or_empty(step1.get("onward_transfers"))
    if onward.get("present") == "yes" and not _non_empty_str(onward.get("child_assessment_ref")):
        out.append({
            "id": "onward-child-assessment",
            "question": _ONWARD_UNKNOWN_QUESTION,
            "blocking": False,
        })

    # v1.1 (adversarial review findings 11/12, task 2c): surface an
    # undocumented "unknown" mechanism and every open conditions[] entry as
    # unknowns[] too — same "legitimately not resolved yet, not an error"
    # framing as onward-child-assessment. blocking=False here mirrors
    # MECHANISM-UNKNOWN's own severity while the document is still a draft;
    # blocking=True on an open condition reflects that the transfer must
    # not start (and the assessment does not read as complete) while it
    # stands open.
    step2 = _dict_or_empty(sidecar.get("step2"))
    if step2.get("mechanism") == "unknown":
        out.append({
            "id": "mechanism-unknown",
            "question": _MECHANISM_UNKNOWN_QUESTION,
            "blocking": False,
        })

    conditions = sidecar.get("conditions") if isinstance(sidecar, dict) else None
    conditions = conditions if isinstance(conditions, list) else []
    for condition in conditions:
        if not isinstance(condition, dict) or condition.get("status") != "open":
            continue
        cond_id = _non_empty_str(condition.get("id")) or "condition"
        text = _non_empty_str(condition.get("text")) or "unspecified condition"
        out.append({
            "id": f"condition-open-{cond_id}",
            "question": f"Open condition: {text}",
            "blocking": True,
        })

    return out


def to_core_artefact(sidecar: dict, *, skill_version: str) -> dict:
    return {
        "artefact_schema_version": ARTEFACT_SCHEMA_VERSION,
        "skill": SKILL_NAME,
        "skill_version": skill_version,
        "generated_at": _now(),
        "subject": _subject(sidecar),
        "outcome": _outcome(sidecar),
        "gaps": _gaps(sidecar),
        "sources": _sources(sidecar),
        "handoffs": _handoffs(sidecar),
        "unknowns": _unknowns(sidecar),
    }

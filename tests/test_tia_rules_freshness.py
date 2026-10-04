"""Freshness rules 13-15 (DPF-EVIDENCE, REVIEW-DATE, SRC-FRESH) — task 5.

Anti-rot note (task-5-report.md has the full account): _fresh_manifest()'s
last_verified/generated_at values are computed relative to *today* (30 days
back) rather than a literal calendar date, so this fixture never drifts into
"stale" territory (> 365 days) no matter how long after 2026-08-11 the suite
runs. The single explicitly-stale date used below ("2024-01-01") only ever
grows staler with time, so it never needs to rot in the other direction
either. Both properties are true "explicit dates", never a same-run
`today - threshold` computation that would make a rule look permanently
quiet by construction.
"""
import datetime as _dt
import json
import sys
from pathlib import Path

TIA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TIA_ROOT / "validator"))

import tia_validator.rules                                      # noqa: E402,F401
from tia_validator.runner import Context, validate              # noqa: E402

FIXTURES = TIA_ROOT / "validator" / "fixtures" / "must_pass"


def _ctx(**kw):
    return Context(schema_path=TIA_ROOT / "references" / "tia-sidecar-schema.json",
                   references_dir=TIA_ROOT / "references", **kw)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fired(result):
    return {f.rule_id for f in result.findings}


def _fresh_manifest():
    """Override manifest covering every on-disk references/**/*.md, all fresh."""
    refs = TIA_ROOT / "references"
    fresh_date = (_dt.date.today() - _dt.timedelta(days=30)).isoformat()
    files = {f"references/{p.relative_to(refs).as_posix()}":
             {"source_type": "ai-drafted", "jurisdiction": "EU", "url": None,
              "last_verified": fresh_date, "confidence": "high", "owner": "t"}
             for p in refs.rglob("*.md")}
    return {"schema_version": "1.0", "generated_at": fresh_date, "files": files}


# ---------------------------------------------------------------------------
# DPF-EVIDENCE
# ---------------------------------------------------------------------------

def test_dpf_evidence_fires_on_bare_assertion():
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["dpf_reliance"] = {"scope_evidence": "", "currency_evidence": ""}
    result = validate(doc, _ctx(sources_lock_override=_fresh_manifest()))
    f = next(f for f in result.findings if f.rule_id == "DPF-EVIDENCE")
    assert f.severity == "warning"


def test_dpf_evidence_quiet_when_both_evidence_fields_substantive():
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["dpf_reliance"] = {
        "scope_evidence": "Certification covers HR data; FTC jurisdiction.",
        "currency_evidence": "Active listing checked at dataprivacyframework.gov 2026-08-01."}
    assert "DPF-EVIDENCE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_dpf_evidence_does_not_fire_when_dpf_reliance_is_null():
    # Must-not-fire that would catch an over-broad predicate: a rule keyed
    # only on step2 presence (ignoring dpf_reliance itself being null) would
    # wrongly fire on the fixture's default mechanism (sccs, dpf_reliance: null).
    doc = load_fixture("minimal-signed.json")
    assert doc["step2"]["dpf_reliance"] is None
    assert "DPF-EVIDENCE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_dpf_evidence_fires_on_adequacy_us_with_no_dpf_block():
    # Break-it 2026-10-02 probe2: "mechanism: adequacy" + destination_country
    # "US" + dpf_reliance: null used to short-circuit silently — the EU has
    # no general US adequacy decision, only the DPF for certified recipients,
    # so an "adequacy" claim for the US with no dpf_reliance block at all is
    # a bare, unevidenced claim and must fire exactly like an empty one.
    doc = load_fixture("adequacy-fast-track.json")
    doc["step1"]["destination_country"] = "US"
    doc["step2"]["dpf_reliance"] = None
    result = validate(doc, _ctx(sources_lock_override=_fresh_manifest()))
    f = next(f for f in result.findings if f.rule_id == "DPF-EVIDENCE")
    assert f.severity == "warning"


def test_dpf_evidence_does_not_fire_on_adequacy_for_a_non_us_country():
    # Must-not-fire: a real Art. 45 adequacy decision (e.g. UK) needs no DPF
    # evidence block at all — only the US "adequacy" special case does.
    doc = load_fixture("adequacy-fast-track.json")
    assert doc["step1"]["destination_country"] == "GB"
    assert doc["step2"]["dpf_reliance"] is None
    assert "DPF-EVIDENCE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_dpf_evidence_does_not_fire_on_us_with_a_non_adequacy_mechanism():
    # Must-not-fire: the short-circuit fix is scoped to mechanism=="adequacy";
    # a plain SCCs transfer to the US with no DPF reliance is not making an
    # adequacy claim at all.
    doc = load_fixture("minimal-signed.json")
    assert doc["step1"]["destination_country"] == "US"
    assert doc["step2"]["mechanism"] == "sccs"
    assert doc["step2"]["dpf_reliance"] is None
    assert "DPF-EVIDENCE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


# ---------------------------------------------------------------------------
# REVIEW-DATE
# ---------------------------------------------------------------------------

def test_review_date_fires_when_missing_and_when_interval_exceeds_12_months():
    doc = load_fixture("minimal-signed.json")
    del doc["step5_6"]["next_review_date"]
    assert "REVIEW-DATE" in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))

    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["next_review_date"] = "2028-01-01"        # > 366 days after cover.date
    assert "REVIEW-DATE" in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))

    doc["step5_6"]["review_interval_rationale"] = "Low-risk transfer; SA guidance stable."
    assert "REVIEW-DATE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_review_date_does_not_fire_within_the_12_month_default():
    # Must-not-fire that would catch an over-broad predicate: the fixture's
    # own next_review_date (2027-08-01) is exactly 365 days after cover.date
    # (2026-08-01) — inside the 366-day threshold — and carries no rationale,
    # so a rule that fired on "no rationale" alone (ignoring the interval)
    # would wrongly trip here.
    doc = load_fixture("minimal-signed.json")
    assert "review_interval_rationale" not in doc["step5_6"]
    assert "REVIEW-DATE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_review_date_unparseable_dates_yield_one_warning_never_raise():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["next_review_date"] = "not-a-date"
    result = validate(doc, _ctx(sources_lock_override=_fresh_manifest()))
    review_findings = [f for f in result.findings if f.rule_id == "REVIEW-DATE"]
    assert len(review_findings) == 1
    assert review_findings[0].severity == "warning"


def test_review_date_before_cover_date_is_a_rejection():
    # Adversarial review finding 5: the rule only bounded the interval from
    # above (> 366 days); a next_review_date BEFORE cover.date (negative
    # interval — a review scheduled before the assessment it reviews) passed
    # with zero findings. cover.date is 2026-08-01 in the fixture.
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["next_review_date"] = "2020-01-01"
    result = validate(doc, _ctx(sources_lock_override=_fresh_manifest()))
    review_findings = [f for f in result.findings if f.rule_id == "REVIEW-DATE"]
    assert len(review_findings) == 1
    assert review_findings[0].severity == "rejection"
    assert result.status == "failed"


def test_review_date_equal_to_cover_date_does_not_fire():
    # Boundary: a same-day interval (0 days) is not "before" cover.date and
    # must not be swept up by the negative-interval rejection.
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["next_review_date"] = doc["cover"]["date"]
    assert "REVIEW-DATE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_review_date_sane_interval_no_finding():
    # A sane, positive interval within the 12-month default fires nothing —
    # already covered by test_review_date_does_not_fire_within_the_12_month_default
    # above; kept here as an explicit named case per the fix task's 3-case list
    # (negative / >366 days / sane interval).
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["next_review_date"] = "2027-01-15"
    assert "REVIEW-DATE" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


# ---------------------------------------------------------------------------
# SRC-FRESH
# ---------------------------------------------------------------------------

def test_src_fresh_fires_on_stale_entry_and_on_missing_coverage():
    stale = _fresh_manifest()
    stale["files"]["references/sources.md"]["last_verified"] = "2024-01-01"
    doc = load_fixture("minimal-signed.json")
    assert "SRC-FRESH" in fired(validate(doc, _ctx(sources_lock_override=stale)))

    gap = _fresh_manifest()
    del gap["files"]["references/country-profiles/us-dpf.md"]
    assert "SRC-FRESH" in fired(validate(doc, _ctx(sources_lock_override=gap)))


def test_src_fresh_does_not_fire_when_manifest_covers_everything_and_is_fresh():
    # Must-not-fire that would catch an over-broad predicate: a rule that
    # fired unconditionally (or whenever any manifest is supplied) would trip
    # here even though _fresh_manifest() covers every on-disk file with a
    # recent last_verified.
    doc = load_fixture("minimal-signed.json")
    assert "SRC-FRESH" not in fired(validate(doc, _ctx(sources_lock_override=_fresh_manifest())))


def test_src_fresh_reports_a_warning_on_a_malformed_manifest():
    doc = load_fixture("minimal-signed.json")
    result = validate(doc, _ctx(sources_lock_override=["not", "a", "dict"]))
    f = next(f for f in result.findings if f.rule_id == "SRC-FRESH")
    assert f.severity == "warning"

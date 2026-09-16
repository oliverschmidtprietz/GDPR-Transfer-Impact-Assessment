"""skills/tia/sources.lock.json — shape, coverage and freshness at build
time (task 5). Complements test_tia_rules_freshness.py, which tests the
SRC-FRESH rule's logic in isolation against synthetic manifests; this file
tests the real, committed lock artefact itself.
"""
import datetime as _dt
import json
import sys
from pathlib import Path

TIA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TIA_ROOT / "validator"))

import tia_validator.rules                                      # noqa: E402,F401
from tia_validator.runner import Context, validate              # noqa: E402

LOCK_PATH = TIA_ROOT / "sources.lock.json"
FIXTURES = TIA_ROOT / "validator" / "fixtures" / "must_pass"

_REQUIRED_ENTRY_KEYS = {"source_type", "jurisdiction", "url", "last_verified",
                         "confidence", "owner"}


def _ctx(**kw):
    return Context(schema_path=TIA_ROOT / "references" / "tia-sidecar-schema.json",
                   references_dir=TIA_ROOT / "references", **kw)


def _load_lock():
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def test_lock_parses_and_has_exactly_the_three_top_level_keys():
    lock = _load_lock()
    assert set(lock.keys()) == {"schema_version", "generated_at", "files"}


def test_lock_covers_exactly_the_on_disk_reference_files():
    # A future added reference file fails this test until sources.lock.json
    # is updated to declare it — the coverage discipline is enforced here,
    # not just by the (warning-only) SRC-FRESH rule.
    lock = _load_lock()
    refs = TIA_ROOT / "references"
    on_disk = {f"references/{p.relative_to(refs).as_posix()}"
               for p in refs.rglob("*.md")}
    assert set(lock["files"].keys()) == on_disk


def test_lock_covers_exactly_22_files():
    lock = _load_lock()
    assert len(lock["files"]) == 22


def test_every_entry_carries_the_six_required_keys():
    lock = _load_lock()
    for path, entry in lock["files"].items():
        missing = _REQUIRED_ENTRY_KEYS - set(entry.keys())
        assert not missing, (path, missing)


def test_every_last_verified_parses_as_an_iso_date():
    lock = _load_lock()
    for path, entry in lock["files"].items():
        _dt.date.fromisoformat(entry["last_verified"])   # raises ValueError if malformed


def test_real_lock_yields_a_clean_validate_with_no_src_fresh_firing():
    doc = json.loads((FIXTURES / "minimal-signed.json").read_text(encoding="utf-8"))
    result = validate(doc, _ctx())    # no override -> loads the real lock from disk
    assert result.status == "passed", [f.rule_id for f in result.findings]

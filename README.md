# GDPR Transfer Impact Assessment (TIA) — Deployment Guide

![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)
![Skill version: v1.0](https://img.shields.io/badge/skill-v1.0-green.svg)
![For: Claude](https://img.shields.io/badge/for-Claude-orange.svg)

See [CHANGELOG.md](CHANGELOG.md) for version history. Canonical source: the private monorepo `oliverschmidtprietz/claude-skills` (`skills/tia/`).

## Overview

`tia` is a structured **GDPR Chapter V Transfer Impact Assessment** skill for Claude. Given an international data transfer (or a whole transfer inventory), it walks the EDPB six-step methodology and produces an audit-ready assessment with a clear verdict.

It combines:

- **EDPB Recommendations 01/2020** — the six-step methodology as the backbone.
- **CNIL TIA Guide** (final version, January 2025) — structured assessment tables and the three-way Step 3 conclusion (effective / supplementary measures needed / no realistic basis to believe the problematic law applies in practice).
- **EDPB Recommendations 02/2020** — the four essential guarantees, applied to each relevant surveillance/access law.
- **EDPB Guidelines 05/2021** — the three cumulative criteria for the transfer-qualification gate, with the 12 example scenarios.
- **Balanced Art. 49 treatment** — the EDPB restrictive position (Guidelines 2/2018) *and* the judicial counter-position (OLG München 21 U 3882/25 e, 11 May 2026; CJEU rapporteur von Danwitz's remarks), so the practitioner makes an informed risk-appetite choice.
- **12 pre-built country profiles** + a generic questionnaire for everywhere else.

## What this skill does

- **Transfer qualification gate** — applies the three cumulative criteria (EDPB Guidelines 05/2021) before any TIA, so direct collection, intra-controller employee access, and EU-processor-with-third-country-parent scenarios are correctly handled (Examples 8, 11, 12) rather than over- or under-classified.
- **Mechanism routing** — adequacy (Art. 45) → lightweight assessment; Art. 49 derogation → balanced derogation analysis; Art. 46 tool (SCCs/BCRs) → full six-step TIA. A TIA is only required for Art. 46 transfers; the skill does not over-produce.
- **Step 3 country-law assessment** — Block A (data-protection framework), Block B (surveillance/access laws rated against the four essential guarantees), Block C (Rosenthal-inspired realistic-risk lens on *this* data, *this* importer).
- **Supplementary measures** — auto-suggested against identified gaps, each with an honest "when NOT effective" condition (e.g. encryption with exporter-held keys does nothing if the importer must decrypt to function).
- **Onward transfers** — each hop in the chain (controller → processor → sub-processor) is flagged and assessed separately, with continuing Art. 28 controller responsibility surfaced.
- **RoPA interchange** — imports a RoPA sidecar to find third-country transfers, and emits a JSON delta per assessed transfer for re-ingestion.

## File structure

```
GDPR-Transfer-Impact-Assessment/
├── SKILL.md                              # Main skill instructions (deploy this)
├── CHANGELOG.md                          # Version history
├── LICENSE.txt                           # AGPL-3.0
├── evals/
│   └── evals.json                        # 12 behavioural test cases (89 expectations)
└── references/
    ├── edpb-six-steps.md                 # EDPB Rec 01/2020 methodology
    ├── essential-guarantees.md           # EDPB Rec 02/2020 four-pillar framework
    ├── transfer-qualification.md         # EDPB Guidelines 05/2021 — 3 criteria + 12 examples
    ├── art49-derogations.md              # Art. 49 balanced assessment (EDPB + judicial)
    ├── supplementary-measures.md         # Catalog (technical / contractual / organisational)
    ├── schrems-ii-holdings.md            # C-311/18 key holdings + implications
    ├── tia-template.md                   # Formal-document template structure
    ├── interchange-delta.md              # RoPA delta format
    ├── sources.md                        # Regulatory source references
    └── country-profiles/                 # 12 jurisdictions + generic questionnaire
        ├── us-non-dpf.md   us-dpf.md   uk-post-adequacy.md
        ├── in.md   cn.md   br.md   au.md   sg.md   tr.md
        ├── ae.md (DIFC / ADGM / mainland)   za.md   ru.md
        └── generic-assessment.md         # Guided questionnaire for unlisted countries
```

## Deployment

### Claude.ai (User Skills)

1. Open **Settings → Profile → Custom Skills** (or the equivalent Claude.ai skills entry point).
2. Upload the entire repo contents, preserving `SKILL.md` at the root and the `references/` and `evals/` subdirectories.
3. The skill auto-triggers on phrases such as "TIA", "Transfer Impact Assessment", "Schrems II", "third-country transfer", "Art. 46 / Art. 49", "do I need supplementary measures", "transfer to [country]", "Drittlandsübermittlung".

### Claude Code (`~/.claude/skills/`)

```bash
git clone https://github.com/oliverschmidtprietz/GDPR-Transfer-Impact-Assessment.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/GDPR-Transfer-Impact-Assessment" ~/.claude/skills/tia
```

(Or `cp -r` the folder if you prefer not to symlink.) Claude Code discovers the skill on next start.

### Claude API / Anthropic SDK

Load `SKILL.md` into context as the entry point; the skill uses progressive disclosure, so reference files (including the relevant country profile) are loaded only when the routing table points to them.

## Usage

### Trigger phrases

- "Run a TIA / Transfer Impact Assessment"
- "Is this a Chapter V transfer?"
- "We use SCCs to transfer to [country] — do we need supplementary measures?"
- "Can we rely on the DPF for this US vendor?"
- "Can we use Art. 49(1)(b) for our global SaaS data flows?"
- "Assess our transfers from this RoPA"
- DE: "Drittlandsübermittlung", "Drittlandtransfer", "Angemessenheitsbeschluss"

### Sample prompt

> "We're an Italian retailer using a US-based marketing-analytics SaaS that is **not** DPF-certified. They process customer event data including IP addresses, and we have SCCs Module 2 signed. What does our TIA need to cover, and what supplementary measures should we adopt?"

The skill confirms a full Art. 46 TIA is required, assesses FISA 702 / EO 12333 / CLOUD Act against the four essential guarantees, suggests encryption-with-exporter-held-keys and pre-export pseudonymisation (honestly flagging when they cannot close the gap if the SaaS needs plaintext), adds transparency/challenge clauses, and sets re-assessment triggers.

## Outputs

| Format | Purpose |
|---|---|
| Markdown TIA report | In-session preview / working document (mirrors Steps 1–6) |
| .docx formal TIA document | Compliance file — CNIL-style tables, cover page, assessor + DPO sign-off block |
| JSON interchange delta | RoPA hand-off — patches `tia_ref`, `tia_status`, `supplementary_measures[]`, review dates |
| Transfer Risk Summary | One-page executive overview for batch assessments |

## Regulatory basis

| Document | Reference |
|---|---|
| GDPR Chapter V | Arts. 44–49 |
| Schrems II | CJEU C-311/18 (16 July 2020) — adequacy + TIA obligation |
| EDPB Recommendations 01/2020 | v2.0 — six-step methodology |
| EDPB Recommendations 02/2020 | Four essential guarantees |
| EDPB Guidelines 05/2021 | v2.0 — transfer qualification (3 criteria + 12 examples) |
| EDPB Guidelines 2/2018 | Art. 49 derogations (EDPB restrictive view) |
| CNIL TIA Guide | January 2025 (final) — structured tables, three-way Step 3 conclusion |
| OLG München, 21 U 3882/25 e | 11 May 2026 — Art. 49(1)(b) for inherently international services |
| Implementing Decision (EU) 2023/1795 | EU-US Data Privacy Framework adequacy |

## Benchmark (v1.0 release)

`/skill-creator` iteration-1 sweep — 12 behavioural cases (89 expectations), 1 run per configuration, graded against each eval's expectations:

| Metric | With skill | No-skill baseline | Δ |
|---|---|---|---|
| Pass rate | 100.0% ± 0% | 68.8% ± 27% | **+31.2pp** |
| Wall-clock | 148.9s ± 36.8s | 85.3s ± 9.7s | +63.6s |
| Tokens | 50,236 ± 14,591 | 23,905 ± 678 | +26,331 |

The skill passed 12/12 evals at 100% with **no eval under-performing the baseline**. Value-add concentrates in (a) current/emerging case law the base model cannot reproduce (Art. 49 judicial counter-position), (b) the cross-skill RoPA interchange schema and workspace conventions, and (c) named structured frameworks — four-essential-guarantees ratings, supplementary-measure catalogue, the CNIL "no reason to believe" option, and monitoring triggers.

## Disclaimer

This skill provides structured GDPR Chapter V transfer-assessment guidance based on EDPB Recommendations, CNIL guidance, CJEU case law, and emerging national case law. It is **not legal advice**. Involve your DPO and qualified counsel for final decisions, especially where the skill flags a transfer for suspension or restructuring. Country profiles reflect the law and practice as of the "Last verified" date stated in each profile; fast-moving items (e.g. FISA 702 reauthorisation status, the EU-US DPF's political fragility, adequacy-review cycles) should be confirmed against live sources before formal use.

## License

AGPL-3.0 — see [LICENSE.txt](LICENSE.txt).

## Related skills

- **RoPA** — Records of Processing Activities; emits the sidecar this skill imports, and ingests the delta it emits.
- **DPIA Sentinel** — when a transfer's risk profile may meet the Art. 35 threshold, this skill flags it (it does not auto-trigger a DPIA).

---

*Created by Oliver Schmidt-Prietz — OneZero Legal*

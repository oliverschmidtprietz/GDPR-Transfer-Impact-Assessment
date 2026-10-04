# Transfer Qualification — Is This Actually a Transfer Under Chapter V?

Source: EDPB Guidelines 05/2021 on the Interplay between the application of Article 3 and the provisions on international transfers as per Chapter V of the GDPR (Version 2.0, adopted 14 February 2023).

The GDPR contains no legal definition of "transfer." The EDPB filled this gap with three cumulative criteria. The TIA pipeline uses this file as the pre-assessment gate.

---

## The Three Cumulative Criteria

All three must be met for Chapter V to apply.

**Criterion 1 — Exporter subject to the GDPR.**
The exporter (controller or processor) is subject to the GDPR for the processing in question:
- Art. 3(1): established in the EU and processing in the context of that establishment, OR
- Art. 3(2): not established in the EU but offering goods/services to EU data subjects or monitoring their behaviour, OR
- Art. 3(3): EU Member State diplomatic missions / consulates outside the EU.

The test is processing-by-processing, not entity-by-entity.

**Criterion 2 — Disclosure to a separate controller, joint controller, or processor.**
The data is disclosed by transmission or otherwise made available to a *different* entity. This includes:
- Sending data
- Granting remote access
- Creating an account
- Embedding a storage device
- Submitting a password / decryption key

Exclusions:
- Same-entity processing (an employee on a business trip accessing their own employer's data is not a transfer — Example 8).
- Direct collection from the data subject (the data subject is not an "exporter" — Examples 1, 2, 3).

**Criterion 3 — Importer in a third country.**
The importer is geographically located in a country outside the EEA, OR is an international organisation. This applies regardless of whether the GDPR also applies to the importer under Art. 3(2).

---

## EDPB Examples — Pattern Library

| # | Scenario | Transfer? | Why |
|---|---|---|---|
| 1 | EU data subject fills web form on third-country controller's site (Art. 3(2)) | NO | Data subject provides directly — no exporter |
| 2 | Same as 1, but third-country controller uses a third-country processor | NO for 1; YES for 2 | The controller→processor relationship is a transfer |
| 3 | EU data subject books NY hotel (no EU targeting) | NO | Direct collection, no GDPR applicability |
| 4 | EU travel agency books NY hotel for data subject | YES | Agency (EU controller) sends to hotel (third-country controller) |
| 5 | EU controller sends data to third-country processor | YES | Classic controller→processor transfer |
| 6 | EU processor sends data back to its third-country controller | YES | Processor→controller transfer (the controller may also be subject to Art. 3(2)) |
| 7 | EU processor sends to third-country sub-processor on controller's instructions | YES | Both processor and controller have Chapter V responsibility |
| 8 | EU employee on business trip accesses own employer's data from third country | NO | Same controller; employee is part of the controller |
| 9 | EU subsidiary discloses HR data to third-country parent (as processor) | YES | Separate legal entities |
| 10 | EU processor returns data to third-country controller (not EU-established) | YES | Disclosure to entity in third country |
| 11 | Third-country processor remotely accesses data stored in EU | YES | Remote access from third country = transfer |
| 12 | EU subsidiary of third-country parent, subject to extraterritorial law | NOT YET, but Art. 28 risk | Becomes a transfer if/when subsidiary complies with foreign government access request |

---

## Consequences If All Three Criteria Are Met

Chapter V applies. The exporter must:
- Use one of the Chapter V mechanisms (Art. 45 adequacy, Art. 46 safeguards, Art. 47 BCRs, Art. 49 derogations).
- Perform a TIA if relying on Art. 46.
- Document the legal basis for the transfer.

## Consequences If Any Criterion Is Not Met

No Chapter V transfer. Which other GDPR obligations still bite depends on **which** criterion failed:

- **Criterion 1 (exporter subject to GDPR) fails.** The GDPR does not apply
  to this processing at all (Art. 3 is not met for it) — Chapter V is not
  the only thing switched off. Art. 5/24/32 are not "still mandatory" for
  this processing, because nothing in the GDPR governs it in the first
  place. (This is a narrow, processing-specific conclusion: the same
  exporter's *other* processing may independently be subject to the GDPR —
  that is assessed on its own facts, not inherited from this finding.)
- **Criterion 2 or 3 fails, but criterion 1 is met.** The exporter *is*
  subject to the GDPR for this processing (Art. 3 applies) — only the
  Chapter V transfer machinery does not engage, because there is no
  disclosure to a separate entity (criterion 2) or no third-country
  importer (criterion 3). Per Section 4 of the guidelines, the controller
  must still comply with:
  - Art. 5 — principles relating to processing
  - Art. 24 — controller responsibility
  - Art. 32 — security of processing (including risks from third-country laws)
  - Art. 28 — processor due diligence (especially for Example 12 scenarios)

Source check: EDPB Guidelines 05/2021 v2.0 frames this safeguards-still-apply
passage around the criterion-2 scenario by name (same-entity processing
abroad, e.g. an employee travelling or Art. 3(2) direct collection — Section
4, "SAFEGUARDS TO BE PROVIDED IF PERSONAL DATA ARE PROCESSED OUTSIDE THE EEA
BUT NO TRANSFER TAKES PLACE"), which presupposes the controller remains
subject to the GDPR under Art. 3 — i.e. criterion 1 is met. It does not
address what happens when criterion 1 itself fails, because by definition
the GDPR already does not apply to that processing.

The skill outputs a **Transfer Qualification Finding** documenting:
- Which criterion failed and why
- That Chapter V does not apply to this processing
- Whether Art. 5/24/32 remain mandatory (criterion 2/3 failure) or are not
  engaged for this processing at all (criterion 1 failure) — see above
- For Example 12 scenarios: that an Art. 28 assessment of the processor's exposure to extraterritorial law is required

This finding IS a valuable deliverable — it documents that the organisation analysed the question and concluded Chapter V does not apply, with reasoning that can be defended on audit.

---

## Practical Tips

- **"Remote access counts."** Display on a screen in support / troubleshooting / administration is access. If the support team is in a third country and connects to EU-stored data, that's a transfer.
- **"Storage in third-country cloud counts."** Cloud storage outside the EEA is a transfer if the cloud provider is a separate processor.
- **"Same group ≠ same entity."** Intra-group disclosures between separate legal persons are transfers.
- **"Direct collection is not a transfer."** When the data subject provides data directly to a third-country controller, the data subject is not an exporter.
- **"Onward transfers are separate transfers."** Each hop in the chain must be assessed against the three criteria.

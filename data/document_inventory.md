# Document inventory

## Status: to be populated with real documents

**Purpose:** A concrete list of documents you intend to index—typically a small initial batch (on the order of 10–20 items) so metadata and coverage can be reviewed before full ingestion.

**Important:** Fill this with **actual** documents you have or can access. Avoid ingestion until the inventory reflects what you really plan to use.

---

## Inventory format

For each document, capture:

- **Document name** — Human-readable title or label  
- **Type** — e.g. SC judgment, HC judgment, regulation, policy, government order  
- **Authority** — e.g. court, regulator, ministry, state  
- **Date** — `YYYY-MM-DD` when known  
- **Jurisdiction** — Geographic or legal scope  
- **Expected status** — e.g. active, superseded, invalidated  
- **Notes** — Context (e.g. overruled by X, amended in 2021)  
- **Source location** — Path, URL, or repository reference  

---

## Document inventory

| # | Document Name | Type | Authority | Date | Jurisdiction | Expected Status | Notes | Source Location |
|---|---------------|------|-----------|------|--------------|------------------|-------|-----------------|
| 1 | [Document Name] | SC Judgment | Supreme Court | YYYY-MM-DD | India | active | [Notes] | [Path/URL] |
| 2 | [Document Name] | HC Judgment | High Court AP | YYYY-MM-DD | Andhra Pradesh | active | [Notes] | [Path/URL] |
| 3 | [Document Name] | SC Judgment | Supreme Court | YYYY-MM-DD | India | invalidated | Overruled by [Case] | [Path/URL] |
| 4 | [Document Name] | UGC Regulation | UGC | YYYY-MM-DD | India | active | [Notes] | [Path/URL] |
| 5 | [Document Name] | AICTE Regulation | AICTE | YYYY-MM-DD | India | active | [Notes] | [Path/URL] |
| 6 | [Document Name] | Policy Document | Ministry of Education | YYYY-MM-DD | India | active | NEP 2020 | [Path/URL] |
| 7 | [Document Name] | GO | State Govt AP | YYYY-MM-DD | Andhra Pradesh | active | [Notes] | [Path/URL] |
| 8 | [Document Name] | SC Judgment | Supreme Court | YYYY-MM-DD | India | active | Cross-domain: labor + education | [Path/URL] |
| 9 | [Document Name] | HC Judgment | High Court AP | YYYY-MM-DD | Andhra Pradesh | active | [Notes] | [Path/URL] |
| 10 | [Document Name] | UGC Regulation | UGC | YYYY-MM-DD | India | superseded | Superseded by [Regulation] | [Path/URL] |

---

## Suggested mix (initial batch)

### Include:

1. **Supreme Court judgments (2–3)**  
   - At least one overruled or constrained case (if testing judicial hierarchy)  
   - At least one treated as binding for your domain  
   - Complete metadata  

2. **High Court judgments (2–3)**  
   - On-topic for your policy domain  
   - Complete metadata  

3. **Regulations (1–2)**  
   - e.g. regulator body rules where relevant  
   - Complete metadata  

4. **Policy document (1)**  
   - e.g. national or sector policy text  
   - Complete metadata  

5. **Government orders (1–2)**  
   - Active, clearly scoped  
   - Complete metadata  

---

## Validation checklist (before you rely on the list)

- [ ] Document exists and is accessible  
- [ ] Date is known and valid  
- [ ] Authority is clear  
- [ ] Jurisdiction is stated  
- [ ] Status is defensible (active / superseded / invalidated)  
- [ ] For judgments: overruling relationships noted where applicable  
- [ ] For regulations: supersession chain noted where applicable  

---

## Notes

- **Do not normalize canonical IDs here first** — This table is for human validation and planning.  
- **Do not treat this file as ingestion input by itself** — Wire ingestion to your storage and pipeline as documented in the main README.  
- **Populate with real rows** — The template rows are structural examples only.  

---

## Next steps

1. Replace template rows with real documents and sources.  
2. Complete the validation checklist above.  
3. Align with your deployment: configure `.env`, ingestion paths, and vector/index backends as in the repository root `README.md`.  
4. Run ingestion and indexing through your chosen pipeline when metadata and access are confirmed.  

---

## Status

- Inventory template: **ready**  
- Real document population: **pending your data**  

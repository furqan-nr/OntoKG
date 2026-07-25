# Expert evaluation of explanation quality — study protocol and instrument (D3)

A ready-to-run protocol to evaluate whether OntoKG-EQ's provenance-grounded explanations improve
analyst-facing explanation quality over a baseline. Designed to be executed by the authors; this
document is the registered design, instrument, and analysis plan. (Not yet run.)

## 1. Objective and hypotheses

Evaluate the explanations attached to executed CQ results on four constructs: **completeness**,
**correctness/faithfulness**, **inspectability (traceability)**, and **trust**.

- H1: OntoKG-EQ provenance-grounded explanations score higher on completeness, faithfulness,
  inspectability, and trust than a result-only baseline.
- H2: Participants verify a result against its source faster and more accurately with the
  provenance-grounded explanation than with the baseline.

## 2. Conditions (within-subjects)

For each worked CQ result, the participant sees the same result entity under two explanation
conditions, order randomised:

- **A — Result-only baseline:** the returned entity and metric values (what a SQL/notebook answer or
  an ungrounded text answer provides), with no structured evidence/provenance.
- **B — OntoKG-EQ explanation:** the auto-generated `EvidenceBundle` path: result -> supporting
  observations (metric values) -> evidence item (official announcement) -> source -> provenance
  record, plus the SHACL `Conforms` status.

(Optional third condition C — GraphRAG/LLM text answer over the same graph — if an LLM is
instrumented; see D2.)

## 3. Materials (worked cases)

Six real worked cases spanning markets and CQs:
- PSX: OGDC relative-outperformer (CQ3); ENGRO outperformer (CQ3); a CQ4 abnormal-event-reaction.
- MSX: MAXIS fundamentals-market-divergence (CQ1); MAYBANK divergence (CQ1); a CQ2 FX-association case.
Each case is frozen as a one-page stimulus (identical numbers across conditions; only the
explanation scaffolding differs).

## 4. Participants

- Target N = 20-30 (>= 18 needed for the planned within-subject Wilcoxon test at typical effect
  sizes); finance students (senior UG/MSc) and practising analysts.
- Inclusion: basic familiarity with equity fundamentals and market returns; no requirement for
  semantic-web knowledge.
- Recruitment via university finance programmes / professional contacts; informed consent; no
  personally identifying data stored; participation voluntary and anonymised.

## 5. Instrument (per case, per condition)

Five-point Likert (1 = strongly disagree ... 5 = strongly agree):

1. **Completeness** — "The explanation shows all the information needed to understand why this entity
   was returned."
2. **Faithfulness/correctness** — "Every claim in the explanation is backed by the evidence shown."
3. **Inspectability** — "I could trace this result back to an original source if I needed to."
4. **Trust** — "I would be willing to rely on this result in an analyst note."

Objective verification task (per case):
5. **Traceability accuracy** — "Name the official source that supports this result." (scored
   correct/incorrect against the ground-truth source in the graph).
6. **Time-to-verify** — seconds from stimulus shown to answer submitted (captured by the form).

Post-study: short free-text on perceived usefulness and missing information.

## 6. Procedure

Consent -> 2-minute tutorial (one neutral example) -> randomised sequence of (case x condition)
stimuli with the instrument after each -> post-study questions. ~20-25 minutes total. Delivered via a
simple web form or printed booklet; condition/case order counterbalanced (Latin square).

## 7. Analysis plan

- Primary: per-construct scores B vs A, **Wilcoxon signed-rank** (paired, non-parametric), report
  medians, effect size (r), and 95% CIs; Holm correction across the four constructs.
- Traceability accuracy: McNemar's test (paired binary). Time-to-verify: paired comparison
  (Wilcoxon).
- Reliability: Cronbach's alpha across the four Likert items; inter-rater where multiple raters.
- Report all results including null/negative outcomes.

## 8. Threats to validity

- *Construct:* Likert self-report mitigated by the objective traceability + time measures.
- *Internal:* order/learning effects mitigated by randomised counterbalancing.
- *External:* student-heavy sample; report practitioner subgroup separately.
- *Researcher bias:* stimuli frozen and identical across conditions except the explanation layer;
  pre-registered analysis.

## 9. Deliverables

Anonymised response dataset (CSV), analysis script, and a results table/figure for the manuscript's
evaluation section. Stimuli and instrument released in the reproducibility bundle so the study is
replicable.

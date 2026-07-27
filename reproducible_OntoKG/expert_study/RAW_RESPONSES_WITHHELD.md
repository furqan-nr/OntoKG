# Raw participant responses — withheld for privacy

The row-level participant response workbooks (the Google Form exports) are **not
included in this public release**. Participants consented on the basis that their
responses would be reported **only in aggregate**, and the row-level exports carry
quasi-identifiers (per-second timestamps, role, years of experience, and free-text
fields) that could enable indirect re-identification.

What **is** released here, and is sufficient to understand and audit the study:

- the survey instrument and stimuli (`participant_packet.md`, `stimuli.json`,
  `facilitator_protocol.md`, `google_form/`);
- the analysis code (`analyze_expert_study.py`,
  `google_form/analyze_google_form_responses.py`);
- the **aggregate results** (`results.md`, `google_form/results.md`): means,
  participant-bootstrap 95% confidence intervals, and exact participant-level tests
  for n = 17.

The raw exports are retained privately by the authors and can be made available to
editors or reviewers under a confidentiality arrangement approved by the relevant
departmental authority. To reproduce the aggregate results, run
`analyze_expert_study.py` against the retained raw export.

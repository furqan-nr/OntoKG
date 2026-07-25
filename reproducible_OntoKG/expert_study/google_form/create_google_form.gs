/**
 * OntoKG-EQ Expert Study — one-click Google Form builder (Google Apps Script).
 *
 * HOW TO USE (about 2 minutes):
 *   1. Open https://script.google.com  ->  New project.
 *   2. Delete the sample code, paste THIS ENTIRE FILE, then click Save.
 *   3. Make sure the function box shows "buildForm", then click Run.
 *   4. First run only: Review permissions -> your Google account -> Allow.
 *   5. View -> Logs prints the EDIT URL (to review) and the LIVE URL (to send to experts).
 *   6. In the form editor: Responses -> green Sheets icon -> Create spreadsheet (= documented proof).
 *
 * NOTE: re-running buildForm creates a NEW form each time (with new links). Delete any earlier draft.
 */

const ITEMS = [
  {
    "id": "I01",
    "market": "PSX",
    "company": "Engro Holdings Limited",
    "A": "Engro Holdings Limited outperformed both its sector and the broad-market benchmark over the post-report window.",
    "B": "Engro Holdings Limited outperformed both its sector and the broad-market benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = -6.93%\n    - company_1 — post-report window return = 7.72%\n    - sector_classifier_Fertilizer — sector window return = 2.1%\n    - Evidence: FY results announced 2026-02-26 (source: source_20)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I02",
    "market": "PSX",
    "company": "Oil and Gas Development Company Limited",
    "A": "Oil and Gas Development Company Limited outperformed both its sector and the broad-market benchmark over the post-report window.",
    "B": "Oil and Gas Development Company Limited outperformed both its sector and the broad-market benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = -9.11%\n    - company_3 — post-report window return = 8.11%\n    - sector_classifier_Oil_Gas_Exploration — sector window return = 7.28%\n    - Evidence: FY results announced 2026-02-23 (source: source_21)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I03",
    "market": "MSX",
    "company": "Maxis Berhad",
    "A": "Maxis Berhad reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.",
    "B": "Maxis Berhad reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = 0.16%\n    - company_MY_CO_MAXIS — YoY profit growth = 11.82%\n    - company_MY_CO_MAXIS — post-report window return = -6.31%\n    - Evidence: FY results announced 2026-04-16 (source: source_MY_SRC_MAXIS_AR2025)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I04",
    "market": "MSX",
    "company": "Malayan Banking Berhad",
    "A": "Malayan Banking Berhad reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.",
    "B": "Malayan Banking Berhad reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = -0.01%\n    - company_MY_CO_MAYBANK — YoY profit growth = 4.21%\n    - company_MY_CO_MAYBANK — post-report window return = -2.34%\n    - Evidence: FY results announced 2026-04-01 (source: source_MY_SRC_MAYBANK_AR2025)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I05",
    "market": "IDX",
    "company": "PT Bank Mandiri (Persero) Tbk",
    "A": "PT Bank Mandiri (Persero) Tbk outperformed both its sector and the broad-market benchmark over the post-report window.",
    "B": "PT Bank Mandiri (Persero) Tbk outperformed both its sector and the broad-market benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = -13.49%\n    - company_IDX_CO_BMRI — post-report window return = -5.94%\n    - sector_classifier_Banking — sector window return = -13.54%\n    - Evidence: FY results announced 2026-02-06 (source: source_IDX_SRC_BMRI_DISCLOSURE)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I06",
    "market": "IDX",
    "company": "PT Indosat Ooredoo Hutchison Tbk",
    "A": "PT Indosat Ooredoo Hutchison Tbk outperformed both its sector and the broad-market benchmark over the post-report window.",
    "B": "PT Indosat Ooredoo Hutchison Tbk outperformed both its sector and the broad-market benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - market_index_benchmark — benchmark window return = -9.48%\n    - company_IDX_CO_ISAT — post-report window return = -0.74%\n    - sector_classifier_Telecommunications — sector window return = -1.61%\n    - Evidence: FY results announced 2026-02-09 (source: source_IDX_SRC_ISAT_DISCLOSURE)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I07",
    "market": "IDX (64-stock)",
    "company": "PT. Mitra Adiperkasa Tbk",
    "A": "PT. Mitra Adiperkasa Tbk outperformed both its sector and the broad-market benchmark over the post-report window.",
    "B": "PT. Mitra Adiperkasa Tbk outperformed both its sector and the broad-market benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - PT. Mitra Adiperkasa Tbk — post-report window return = 31.64%\n    - sector — window return = 13.42%\n    - benchmark (JCI) — window return = -19.38%\n    - Evidence: FY results announced 2025-12-31 (source: source_IDX_SRC_MAPI)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  },
  {
    "id": "I08",
    "market": "IDX (64-stock)",
    "company": "PT Trimegah Bangun Persada Tbk",
    "A": "PT Trimegah Bangun Persada Tbk reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.",
    "B": "PT Trimegah Bangun Persada Tbk reported stronger fundamentals (positive year-on-year profit growth) but a weaker market response than the benchmark over the post-report window.\n\n  Supporting evidence (from the validated knowledge graph):\n    - PT Trimegah Bangun Persada Tbk — YoY profit growth = 40.32%\n    - PT Trimegah Bangun Persada Tbk — post-report window return = -30.02%\n    - benchmark (JCI) — window return = -19.38%\n    - Evidence: FY results announced 2025-12-31 (source: source_IDX_SRC_NCKL)\n    - Structural check: the knowledge graph passed SHACL validation (Conforms = True)"
  }
];

function buildForm() {
  const form = FormApp.create('OntoKG-EQ Expert Study — Analyst Explanation Evaluation');
  form.setDescription(
    'Thank you for helping with this short PhD study. It takes about 10 minutes and is completely ' +
    'anonymous — there are no right or wrong answers.\n\n' +
    'You will look at 8 short statements about real listed companies. For EACH company the statement ' +
    'appears TWICE:\n' +
    '  - Part 1: the statement on its own, with NO supporting evidence — you rate it based only on what ' +
    'is shown.\n' +
    '  - Part 2: the SAME statement, now WITH its supporting evidence — you rate it again and say which ' +
    'version you would rather receive.\n\n' +
    'We simply want to see whether seeing the evidence changes how much you trust and understand the ' +
    'statement. Please complete Part 1 before moving to Part 2 for each company.');
  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);

  // ---- Page 1: how it works + consent + background ----
  form.addSectionHeaderItem()
      .setTitle('How this works (please read)')
      .setHelpText('Each of the 8 companies is shown on two pages: first the statement WITHOUT its ' +
        'evidence (rate it as shown), then the SAME statement WITH its evidence (rate it again). ' +
        'It is normal to rate the two differently — that is exactly what we are studying. ~10 minutes, anonymous.');
  form.addMultipleChoiceItem()
      .setTitle('Consent')
      .setHelpText('Participation is voluntary and anonymous; no personal identifiers are collected.')
      .setChoiceValues(['I am 18 or older and I consent to participate'])
      .setRequired(true);
  form.addMultipleChoiceItem().setTitle('Your role')
      .setChoiceValues(['Student', 'Analyst / finance professional', 'Academic', 'Other'])
      .showOtherOption(true).setRequired(true);
  form.addTextItem().setTitle('Years of experience reading financial statements / analyst notes').setRequired(false);

  const LO = 'Not at all', HI = 'Completely', C_LO = 'No justification', C_HI = 'Fully sufficient to verify';

  ITEMS.forEach(function (it, i) {
    const n = (i + 1);
    // ---- Part 1: Version A (no evidence) ----
    form.addPageBreakItem().setTitle('Company ' + n + ' of ' + ITEMS.length + '  —  ' + it.company + '   (Part 1 of 2)');
    form.addSectionHeaderItem()
        .setTitle('The statement, on its own — no supporting evidence yet:')
        .setHelpText(it.A + '\n\nBased ONLY on what is shown above, please answer the two questions below, then continue to Part 2.');
    form.addScaleItem().setTitle(it.id + ' - Trust (Version A)').setBounds(1, 7).setLabels(LO, HI)
        .setRequired(true);
    form.addScaleItem().setTitle(it.id + ' - Completeness of justification (Version A)').setBounds(1, 7).setLabels(C_LO, C_HI)
        .setRequired(true);
    form.addParagraphTextItem().setTitle(it.id + ' - What would you need in order to verify this statement? (Version A)').setRequired(false);

    // ---- Part 2: Version B (with evidence) ----
    form.addPageBreakItem().setTitle('Company ' + n + '  —  the SAME statement, now WITH its evidence   (Part 2 of 2)');
    form.addSectionHeaderItem()
        .setTitle('The same statement, now with its supporting evidence:')
        .setHelpText(it.B + '\n\nNow please re-rate the two questions below, and tell us which version you would rather receive.');
    form.addScaleItem().setTitle(it.id + ' - Trust (Version B)').setBounds(1, 7).setLabels(LO, HI)
        .setRequired(true);
    form.addScaleItem().setTitle(it.id + ' - Completeness of justification (Version B)').setBounds(1, 7).setLabels(C_LO, C_HI)
        .setRequired(true);
    form.addMultipleChoiceItem().setTitle(it.id + ' - Which version would you rather receive in an analyst note?')
        .setChoiceValues(['A (no evidence)', 'B (with evidence)', 'No difference']).setRequired(true);
  });

  Logger.log('==============================================');
  Logger.log('EDIT URL : ' + form.getEditUrl());
  Logger.log('LIVE URL : ' + form.getPublishedUrl());
  Logger.log('==============================================');
}

# Expert study as a Google Form (easy for participants + documented proof)

This turns the paper study into a Google Form your 14–15 experts can fill in about 10 minutes. Every
submission is timestamped and logged to a Google Sheet, giving you auditable, documented proof.

## Files
| File | What it does |
|---|---|
| `create_google_form.gs` | One-click Apps Script that **builds the whole form** from the 8 real items (consent, background, and each statement shown first without evidence, then with it). |
| `analyze_google_form_responses.py` | Deprecated shim; runs the canonical participant-level analysis (`../analyze_expert_study.py`). |

## Step 1 — Create the form (about 2 minutes, once)
1. Go to **https://script.google.com** → **New project**.
2. Delete the sample code, paste **all of `create_google_form.gs`**, click **Save**.
3. Ensure the function box shows **buildForm**, click **Run**.
4. First run only: **Review permissions → your account → Allow** (it only edits Forms you own).
5. Open **View → Logs**. It prints:
   - **EDIT URL** — open to review/adjust wording, add your name/logo, etc.
   - **LIVE URL** — the link you send to participants.

## Step 2 — Turn on response logging (documented proof)
In the form editor: **Responses** tab → the green **Sheets** icon → **Create spreadsheet**. From now on
every submission lands in that Google Sheet with a timestamp. (Keep the sheet; it is your evidence.)

## Step 3 — Collect responses
Send the **LIVE URL** to your 12–20 experts (finance/MBA/CS grads, junior analysts, or colleagues).
The form already enforces the design: participants rate the plain statement (Version A) on one page,
then see the same statement **with its evidence** (Version B) on the next page and rate again + pick a
preference. It is anonymous; an optional Participant ID field lets you track who has completed it.

## Step 4 — Analyse
1. In the linked Google Sheet: **File → Download → Microsoft Excel (.xlsx)**.
2. The collected export in this repository is `../Form responses (17).xlsx`.
3. Run: `pip install openpyxl` then `python ../analyze_expert_study.py "../Form responses (17).xlsx"`.
4. It writes `results.md` with the trust/completeness/preference statistics and a ready-to-paste
   Section 7.6 paragraph. The canonical participant-level analysis is `../analyze_expert_study.py`; `results.md` reproduces the Section 7.6 numbers.

## Notes
- Target **12–20** respondents; 12 is enough if the effect is as large as expected, more is better.
- No coding needed beyond pasting the script; the paper-based `participant_packet.docx` in the parent
  folder remains available as an offline alternative.
- Ethics: obtain your institution's ethics/IRB clearance or exemption before collecting; the form's first
  question is an explicit anonymous-consent item and keeps a record of it.

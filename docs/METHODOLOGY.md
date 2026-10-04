# Evidence and evaluation protocol

1. Define a single task with a discriminating success marker and synthetic inputs. Reset staging data before comparisons.
2. Record the model deployment, task, viewport and budgets. Archive the complete report folder privately.
3. Run all three conditions. Repeat runs when examining variability; do not treat one run as stable evidence.
4. Review every observation against its screenshot and trace. Reproduce suspected service issues manually. Distinguish model mistakes, instrumentation limitations and service failures.
5. Assign severity and acceptance decisions with a human researcher. Pending fields in JSON can support a separate reviewed record; the report generator does not implement a review editor.
6. Compare prioritised hypotheses with moderated or unmoderated research involving recruited users, including disabled users where relevant. Obtain appropriate research consent separately.
7. Present organisational evidence separately for the full Service Standard assessment.

## Suggested evaluation before adoption

Use fixtures with known defects and unaffected controls. Measure false positives, missed issues and repeatability across model runs. Compare findings with expert review and actual participant sessions. Evaluate whether the success marker corresponds to the intended system state. Include model/API failures and blocked dependencies in analysis rather than excluding unsuccessful runs.

## Architecture

CLI configuration → isolated browser context → bounded DOM observation → Foundry decision → action validation → browser action → success check → screenshots and report → human review.

Only the decision step uses a language model. The local runner controls allowed actions, outcome detection and timing. Page text is untrusted input to the model; action validation reduces risk but cannot make arbitrary website execution safe.

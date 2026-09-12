# Model Card — Claim Rejection LightGBM

**Created:** 2026-07-29T00:56:44

## What this model does
Supervised gradient boosting predicting whether a claim will be rejected, using 63
features drawn from 13 openIMIS tables. **The target is rejection, not
fraud.** Most rejections are deterministic eligibility rules the openIMIS engine already enforces
at submission; §19 quantifies how much of the target is reachable.

This model is the **performance ceiling** for the unsupervised methods in the companion
notebooks. It requires labels; they do not.

## Data
- Adjudicated claims only (accepted (16, 32), rejected (1,))
- Temporal split — train 1,949,794 / val 417,813 / test 417,814
- Base rates: population 15.8156%, test 16.2333%
- Imbalance 5.5:1, handled by: 6. focal loss (g=2)
- Policy attributes joined **as-of the service date**, not the latest available row

## Performance (test)
- ROC-AUC 0.9841 (95% CI 0.9767–0.9898, clustered by facility)
- PR-AUC 0.9635 vs no-skill 0.1623 (5.94x)
- At threshold 2.273039: precision 0.9991, recall 0.6502, alert rate 10.56%
- Across 3 seeds: AP 0.9616 ± 0.0016
- Brier 0.0207 raw → 0.0209 calibrated

## Leakage controls
- 35 adjudication-time fields on an explicit deny-list
- Max |corr(feature, label)| 0.3513; max single-feature AUC 0.9439
- Category levels fixed on the training window only
- `PolicyStatus` excluded deliberately: it is current state, not state at claim time

## Known limitations
1. Rejection is a weak proxy for fraud.
2. Requires labels, so it cannot score genuinely novel fraud patterns the unsupervised models might.
3. Facility identity is an input; the model partly encodes provider reputation.
4. Uncalibrated scores should not be read as probabilities — use the isotonic calibrator.
5. Not validated prospectively.

## Intended use
Audit-queue triage alongside the rules engine, and as the benchmark ceiling for the
unsupervised models. Advisory only; all decisions human.

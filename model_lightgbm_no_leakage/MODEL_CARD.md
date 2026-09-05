# Model Card — Claim Rejection LightGBM

**Created:** 2026-09-05T15:19:14

## What this model does
Supervised gradient boosting predicting whether a claim will be rejected, using 51
features drawn from 11 openIMIS tables. **The target is rejection, not
fraud.** Most rejections are deterministic eligibility rules the openIMIS engine already enforces
at submission; §19 quantifies how much of the target is reachable.

This model is the **performance ceiling** for the unsupervised methods in the companion
notebooks. It requires labels; they do not.

## Data
- Adjudicated claims only (accepted (16, 32), rejected (1,))
- Temporal split — train 1,949,794 / val 417,813 / test 417,814
- Base rates: population 15.8156%, test 16.2333%
- Imbalance 5.5:1, handled by: 1. none (baseline)
- Policy attributes joined **as-of the service date**, not the latest available row

## Performance (test)
- ROC-AUC 0.8778 (95% CI 0.8151–0.9205, clustered by facility)
- PR-AUC 0.7604 vs no-skill 0.1623 (4.68x)
- At threshold 0.875123: precision 0.9179, recall 0.5403, alert rate 9.56%
- Across 3 seeds: AP 0.7597 ± 0.0007
- Brier 0.0907 raw → 0.0705 calibrated

## Leakage controls
- 36 adjudication-time fields on an explicit deny-list
- Max |corr(feature, label)| 0.3513; max single-feature AUC 0.7658
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

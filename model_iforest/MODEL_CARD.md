# Model Card — Claim Rejection Isolation Forest

**Created:** 2026-07-28T19:03:37

## What this model does
Scores health insurance claims by Isolation Forest path length. **The target is claim
rejection, not fraud.** Most rejections in openIMIS are deterministic eligibility and rule
violations already caught by the submission-time rules engine; §15 quantifies how much of the
target is reachable at all.

## Configuration
- Trained on: accepted only (1,667,620 rows)
- n_estimators 400, max_samples 512, max_features 1.0
- log1p on monetary features: True
- Split: temporal — train 1,949,796 / val 417,814 / test 417,814

## Performance (test)
- ROC-AUC 0.7235 (95% CI 0.6532–0.7810, clustered by facility)
- PR-AUC 0.4417 vs no-skill 0.1750 (2.52x)
- At threshold 0.644081: precision 0.5744, recall 0.1479, alert rate 4.51%
- Across 5 seeds: AUC 0.7219 ± 0.0012

## Explainability
TreeSHAP gives exact Shapley values per claim in milliseconds. Note these explain the raw
path-length score, not the normalised `score_samples` output; signs are negated in §18 so a
positive contribution means "pushed toward being flagged".

## Known limitations
1. Rejection is a weak proxy for fraud; codes near AUC 0.5 are structurally invisible.
2. Axis-parallel splits miss anomalies defined by correlations between features.
3. Facility risk is an input, so §17 is partly circular.
4. False positives are expected to concentrate on high-complexity facilities. Peer-group
   relative scoring and a fairness audit are required before operational use.
5. Not validated prospectively.

## Intended use
Audit-queue triage alongside the existing rules engine. Advisory only; all decisions human.
**Not** an automated rejection or fraud-determination system.

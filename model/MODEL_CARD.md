# Model Card — Claim Rejection Autoencoder

**Created:** 2026-07-28T18:05:38

## What this model does
Scores health insurance claims by autoencoder reconstruction error, trained on accepted
claims only. **The target is claim rejection, not fraud.** Per the openIMIS rejection
taxonomy, the large majority of rejections are deterministic eligibility and rule violations
already caught by the submission-time rules engine. See §15 for per-code detectability.

## Data
- Adjudicated claims only (accepted (16, 32), rejected (1,))
- Split: temporal — train 1,949,796 / val 417,814 / test 417,814
- Base rates: population 15.8156%, test 17.4997%

## Performance (test)
- ROC-AUC 0.7408 (95% CI 0.6712–0.8015, clustered by facility)
- PR-AUC 0.5074 vs no-skill 0.1750 (2.90x)
- At threshold 0.348160: precision 0.9438, recall 0.0951, alert rate 1.76%
- Across 3 seeds: AUC 0.7368 ± 0.0045

## Leakage controls
- Post-adjudication features: excluded
- All encoders and scalers fitted on the training window only
- Max |corr(feature, label)|: 0.3530

## Known limitations
1. Rejection is a weak proxy for fraud; codes with AUC near 0.5 are structurally invisible.
2. The training "normal" class may still contain undetected historical overbilling.
3. Facility-level `Hfid` risk is an input, so §17 is partly circular.
4. False positives concentrate on high-complexity facilities; peer-group-relative scoring
   and a fairness audit are required before any operational use.
5. Not validated prospectively. A shadow pilot measuring precision against human
   adjudication is required before deployment.

## Intended use
Audit-queue triage alongside the existing rules engine. Advisory only; all decisions human.
**Not** an automated rejection or fraud-determination system.

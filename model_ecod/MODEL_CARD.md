# Model Card — Claim Rejection ECOD

**Created:** 2026-07-28T19:14:35

## What this model does
Scores claims by the summed negative log tail probability of each feature under the empirical
CDF of a reference population. **The target is claim rejection, not fraud.** §15 quantifies
how much of that target is reachable at all.

## Configuration
- Variant ECOD, aggregation 'skew', reference 'accepted only' (1,667,620 rows)
- **No hyperparameters.** Deterministic: refitting reproduces scores bit-for-bit (§11).
- ECOD vs COPOD Spearman rank correlation on this data: 1.0000
- Split: temporal — train 1,949,796 / val 417,814 / test 417,814

## Performance (test)
- ROC-AUC 0.7426 (95% CI 0.6736–0.8002, clustered by facility)
- PR-AUC 0.5238 vs no-skill 0.1750 (2.99x)
- At threshold 45.483717: precision 0.9042, recall 0.1809, alert rate 3.50%

## Explainability
Exact by construction: the score is a sum of per-dimension contributions, each a tail
probability that reads directly as "higher than X% of reference claims". No SHAP needed.

## Known limitations
1. **Dimensions treated as independent.** Anomalies defined by feature *interactions* are
   invisible unless the interaction has been engineered into its own column.
2. Rejection is a weak proxy for fraud; several codes sit near AUC 0.5 by construction.
3. Facility risk is an input feature, so §17 is partly circular.
4. One-hot columns from rare categories contribute a large constant to every claim carrying
   that level.
5. Not validated prospectively.

## Intended use
Audit-queue triage alongside the existing rules engine, and as the **complexity baseline**
every other model must beat. Advisory only; all decisions human.

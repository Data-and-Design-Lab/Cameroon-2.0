# Data Directory

This directory is designated for raw and preprocessed data files from the Cameroon **openIMIS** healthcare claim database.

## ⚠️ Important Note on Large Files
Due to GitHub repository size constraints, raw data files (`*.csv`, `*.parquet`, etc.) are **excluded** from version control via `.gitignore`. The dataset encompasses **14,242,741 claim records** (~6.6 GB uncompressed).

## Expected Dataset Schema & Files
When running notebooks or training pipelines, place the following openIMIS relational tables in this directory:

| Filename | Description | Approx. Records |
| :--- | :--- | :--- |
| `TblClaim.csv` | Primary transaction claim ledger (financials, dates, status, diagnosis) | ~14.24M |
| `TblClaimServices.csv` | Itemized clinical services and procedures billed per claim | ~15.77M |
| `TblClaimItems.csv` | Itemized medical items and consumables billed per claim | ~180K |
| `TblHF.csv` | Health facilities master table (facility care level, regions, districts) | ~2,512 |
| `TblICDCodes.csv` | ICD-10 diagnostic disease codes and descriptions | ~14,000 |
| `TblInsureePolicy.csv` | Beneficiary and policy enrollment linkage | ~1.4M |
| `TblFamilies.csv` | Family and household enrollment structures | ~6.5M |
| `TblServices.csv` | Master procedure catalog with standard pricing | ~5,000 |
| `TblItems.csv` | Master consumable item catalog | ~1,000 |
| `TblLocations.csv` | Geographic hierarchy (regions, districts, communes) | ~15,000 |
| `UvwLocations.csv` | Geographic materialized view | ~3,000 |

## Schema Definitions
For a complete schema breakdown (column data types, null rates, and sample distributions), refer to [`../schemas/full_schema_details.json`](../schemas/full_schema_details.json) and [`../schemas/table_summary.json`](../schemas/table_summary.json).

# Data dictionary

All monetary fields are USD. Costs are kept at source precision; presentation rounds them.

| File | Grain / use |
|---|---|
| billing_records.csv | One row per source record; 135,272 rows. Projected original fields plus derived fields. |
| daily_costs.csv | Charge date, billing month, account ID, account name, service, category, region, department and environment; 4,492 rows. |
| budgets.csv | One row per account ID / billing month; 13 rows of authored monthly assumptions. |
| anomalies.csv | Account / service / day review candidates. Header only for this sample because the rule produced zero candidates. |
| calendar.csv | One row per covered charge date; 19 days. |
| dim_accounts.csv | One row per account ID; display names may repeat. |
| dim_services.csv | One row per service name. |
| dim_departments.csv | One row per parsed department, including Unallocated. |
| cloud_costs.sqlite | Original projected records, daily facts, budgets, candidates and SQL business views. |

| Field | Meaning |
|---|---|
| RecordId | Sequential ingestion ID, not a provider-generated charge ID. |
| ChargeDate | UTC date extracted from ChargePeriodStart. |
| BillingMonth | YYYY-MM from BillingPeriodStart. |
| BilledCost | Net billed amount, including negative charges. |
| EffectiveCost | Separate source measure reflecting effective charge cost; do not substitute for billed cost. |
| ListCost | Source list-price amount. No list-to-billed difference is labelled as realised savings. |
| AbsoluteBilledCost | Sum of absolute record-level billed amounts. It is not the absolute value of an aggregated net cost. |
| UnallocatedAbsoluteCost | Absolute record amount when Department is Unallocated, otherwise zero. |
| RecordCount | Number of original rows in a daily aggregate. |
| Department | Parsed from cost department / department tag; Unallocated when unavailable. |
| Environment | Parsed from env / environment tag; prod/dev normalisation; Unknown when unavailable. |
| CostCenter | Parsed costcenter / cost center tag; Unallocated when unavailable. |
| TagStatus | valid, missing or invalid; malformed JSON is exposed rather than silently labelled valid. |
| MonthlyBudget | Scenario assumption at account/month, not provider data. |
| Previous7DayMean | Mean recorded net cost over the seven preceding calendar days, excluding the scored day. |
| ExcessCost / Ratio | Candidate cost minus baseline / candidate cost divided by baseline. |

The projected original file also retains billing/charge periods, charge category/class/description, provider, service category/name, account ID/name, region, resource ID/name and the original tag JSON. Some projected rows look identical because discarded source columns distinguish them; no projected-row deduplication is applied. Exact duplicates were checked against the complete original source before projection.

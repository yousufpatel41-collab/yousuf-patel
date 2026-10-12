# German Electricity Cost Dashboard

An Analytics / BI portfolio project by Yousuf Patel. **[Open the live dashboard](https://yousufpatel41-collab.github.io/electricity/).** It examines German wholesale price exposure and compares transparent household tariff and flexible-demand scenarios.

The market data is **real published SMARD data** for the Germany/Luxembourg bidding zone. Household consumption, tariffs and equipment availability are assumptions. This project does not contain household meter readings, supplier offers or realised savings.

![Market overview](reports/dashboard_overview.png)

## What the project contains

- `dashboard/index.html`: an offline browser dashboard with market overview, price-pattern heatmap, tariff comparison, flexible-demand analysis and data checks.
- `German_Electricity_Review.xlsx`: editable dates and scenario inputs, financial formulas, two native charts and prepared daily prices.
- `powerbi/Electricity.pbip`: four report pages and a CSV-backed semantic model. Set the DataFolder parameter and refresh in Power BI Desktop. Native Desktop verification remains pending.
- `data/electricity.sqlite`: hourly/daily/monthly tables and reusable SQL views.
- `reports/German_Electricity_Business_Review.pdf`: two-page findings, decisions and method.
- `src`, `sql`, `tests`: reproducible preparation, business queries and validation.
- `data/raw` and `data/source_manifest.json`: preserved weekly source responses and checksums.

Open the dashboard directly in a browser or run `python -m http.server 8742` from this folder and visit `http://localhost:8742/dashboard/`. The dashboard starts at 2026 year to date. Excel initially shows the complete historical window.

## Data and findings

Requested window: **1 January 2024 to 11 October 2026**, retrieved 12 October 2026. There are **24,335 observed hourly prices**, 1,014 available local dates and 34 represented months. The snapshot has 24 missing hours on **10 October 2026**. Missing observations are not imputed as zero.

| Period | Observed hours | Mean EUR/MWh | Negative hourly prices |
|---|---:|---:|---:|
| 2024 | 8,784 | 78.51 | 457 |
| 2025 | 8,760 | 89.32 | 573 |
| 2026 to 11 October, gap excluded | 6,791 | 109.65 | 460 |

The 2025 mean and negative-hour count match [SMARD's official 2025 review](https://www.smard.de/page/en/topic-article/217400/219038). The 2026 row is not a complete-year comparison. The business report separately compares matching available calendar dates in 2025 and 2026.

A wholesale price is not a household tariff. Prices can be negative at the wholesale level while a household still pays grid, levy, supplier and fixed-fee components. No generation or demand series is included, so the project does not attribute price movements to a particular cause.

## Tariff model

Editable defaults: 250 kWh/month, gross flat tariff EUR 0.32/kWh, gross dynamic non-energy adder EUR 0.20/kWh, wholesale gross multiplier 1.19, EUR 10/month fixed fee for either tariff, and 12 flexible kWh/day. These are planning inputs, not live supplier prices or a tax assertion.

```text
Dynamic unit price = Wholesale EUR/MWh / 1,000 × gross multiplier + gross adder
Flat cost          = Same modelled kWh × gross flat rate + prorated fee
Dynamic cost       = Modelled hourly kWh × dynamic unit price + prorated fee
```

Monthly consumption is distributed uniformly across the elapsed hours of each local month. The source preparation stores a consumption weight and wholesale cost coefficient per day. Missing hours receive neither consumption nor fixed-fee weight. A complete month always represents one monthly consumption assumption, including DST months. Negative wholesale values pass through without a floor.

The flexible-demand model compares equal energy in 18:00–22:00 with the four cheapest observed hours of the same local day. Cheapest hours may be non-consecutive. This requires all-day availability and ignores charging/storage losses, power constraints and behavioural restrictions. It is a timing scenario, not an overnight EV plan or achieved savings.

Budget/tariff inputs in the browser persist locally. They do not automatically update Excel or Power BI. Edit `data/tariff_assumptions.csv` and refresh to change the Power BI assumptions.

## Time handling and coverage

UTC timestamp is the unique observation key. Local dates and hours use Europe/Berlin. Spring days have 23 observations and autumn days have 25. The repeated autumn hour is retained as two distinct UTC observations. Market means weight observed hours equally, rather than averaging daily means without duration weights.

The SMARD endpoint supplies published hourly prices. Later quarter-hour market prices are viewed through the source's hourly aggregation. Counts below zero refer to negative hourly-average prices, not the number of negative quarter-hour intervals. Prices are not an actual household consumption-weighted average.

## Rebuild and tests

Python 3.11+:

```text
python -m pip install -r requirements.txt
python src/build_data.py
python src/build_powerbi.py
python src/build_report.py
python -m unittest discover -s tests -v
```

The build reuses the included raw snapshot. To intentionally refresh, use a fresh copy of the project without its raw cache, change the retrieval date/window in the preparation script, and review changes before replacing the baseline. Source revisions can change benchmark values and availability. Extending the data also requires rebuilding the Excel workbook, whose source ranges are bounded.

The Python commands recreate the prepared CSVs, database, dashboard data, Power BI files and PDF. They do not recreate the supplied Excel workbook. An optional workbook authoring script is in `tools`, using the Codex artifact spreadsheet runtime.

Twelve checks cover the financial and time-series model. The interactive dashboard was checked in Edge, including tariff edits, persistence, exports and mobile layout. Excel changes were recalculated and its missing-day guard tested. Power BI JSON passed schema validation; its native rendering and DAX execution are unverified until Desktop refresh.

## Interview explanation

“I used official hourly electricity prices to study market exposure. I kept negative prices, handled daylight saving time using UTC keys, and made missing data visible. I built an interactive dashboard and an Excel model comparing equal consumption under illustrative tariff assumptions. A separate model examines the effect of shifting the same daily energy to cheaper hours.”

Suggested CV bullet: “Analysed 24,335 hourly German electricity prices using Python and SQL; built an interactive dashboard and Excel tariff model with DST handling, source reconciliation and equal-energy demand-shifting scenarios.” Add Power BI to the CV claim after opening and refreshing the included project.

## Source and licence

Attribution: **Bundesnetzagentur | SMARD.de**. Series 4169, DE, hour. [SMARD market data](https://www.smard.de/en), [data-use terms](https://www.smard.de/en/datennutzung), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Raw source URLs and SHA-256 hashes are recorded in `data/source_manifest.json`. Code uses the MIT licence in `LICENSE`; source data remains under CC BY 4.0.

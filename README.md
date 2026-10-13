# Yousuf Patel — analytics portfolio

**[Open the live portfolio and both interactive dashboards](https://yousufpatel41-collab.github.io)**

## Cloud Cost and Budget Dashboard

[Open the live dashboard](https://yousufpatel41-collab.github.io/cloud/) | [View the project files](cloud-cost-dashboard) | [Download the complete package](downloads/Cloud_Cost_Dashboard_Project.zip)

Cloud cost analysis using Python, SQL, Excel and an interactive browser dashboard, with a native Power BI project. The analysis covers 135,272 Microsoft sample billing records, 13 accounts and 36 services.

The project includes editable budget assumptions, allocation analysis, financial checks, screenshots, a business report and reproducible data preparation. Power BI Desktop refresh remains unverified.

![Dashboard preview](cloud-cost-dashboard/reports/dashboard_overview.png)

See the project README for setup, sources, findings and interview notes. The complete package includes the large prepared billing CSV and SQLite database; these can also be recreated with the included scripts.

## German Electricity Cost Dashboard

[Open the live dashboard](https://yousufpatel41-collab.github.io/electricity/) | [View the project files](german-electricity-dashboard) | [Download the complete package](downloads/German_Electricity_Dashboard_Project.zip)

Analysis of 24,335 real published SMARD hourly electricity prices, with an interactive dashboard, editable Excel tariff scenarios, SQL database, raw source snapshot, business report and Power BI project. The model preserves negative prices, daylight saving time and missing data. Household tariffs are illustrative; Power BI Desktop refresh remains pending.

The V2 research upgrade adds 18:00 arrival-time charging, hourly re-planning with published prices, forecasts only for unknown hours, fixed/monthly-retrained LightGBM and Chronos comparisons, and paired confidence intervals. The registered validation gate retains the published-price-only policy. On 93 simulated two-night 2026 sessions it captured 95.05% of the same-constraint oracle opportunity. Personal 15/30/60-minute CSV analysis stays in the browser; English/German import adapters and pilot feedback are available. These are historical simulations, not annual or realised household savings. [V2 evidence](https://yousufpatel41-collab.github.io/electricity/?view=forecast) · [Pre-experiment protocol tag](https://github.com/yousufpatel41-collab/yousuf-patel/releases/tag/v2-protocol-2026-10-13) · [Pilot invitation](https://yousufpatel41-collab.github.io/electricity/?view=pilot). Completed external pilots: 0.

![Electricity dashboard preview](german-electricity-dashboard/reports/dashboard_overview.png)

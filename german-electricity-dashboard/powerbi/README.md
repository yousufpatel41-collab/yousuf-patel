# Power BI setup

Open `Electricity.pbip` in a recent Power BI Desktop version with Power BI project / enhanced report support. Set **Transform data → Manage parameters → DataFolder** to this project's `data` folder, including a trailing `/` or `\`, then apply and refresh.

Four tables: Prices (daily facts), Hourly (hourly facts), Calendar and Scenario. Calendar has one-direction relationships to both fact tables. The Scenario table supplies eleven measures with a single row of assumptions. Edit `data/tariff_assumptions.csv` and refresh to change these assumptions. Browser changes do not update that file.

Four pages: wholesale market, local clock-hour patterns, household tariff scenarios and flexible demand. Calendar date/year slicers filter both fact tables. No available prices on 10 October 2026 means tariff measures return blank for that day. Tariffs are illustrative, 2026 is partial, and negative counts use hourly averages.

The 34 project/report JSON files passed Microsoft schema validation. Source keys and relationships passed automated checks. **Power BI Desktop opening, refresh, rendering and DAX execution remain unverified** in this environment. Use the tested browser/Excel views until you have verified Desktop.

Definitions: `Electricity.SemanticModel/model.bim` and readable `measures.dax`. Rebuild with `python src/build_powerbi.py` from the project root. [Microsoft project format documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview).

# Data dictionary

| File / field | Meaning |
|---|---|
| raw/*.json | Original weekly SMARD responses, including null/future values from the weekly response. Only requested observed hours enter analysis. |
| source_manifest.json | Weekly source URL and SHA-256. |
| hourly_prices.csv | One observed UTC hour. Includes local timestamp with UTC offset, date, month, year, clock hour, weekday, price and derived units/weights. |
| TimestampMs / TimestampUTC | Unique Unix milliseconds / UTC ISO time. |
| LocalTimestamp | Europe/Berlin time with offset, distinguishing repeated autumn hours. |
| PriceEURMWh | Published day-ahead hourly-average wholesale price. Negative values retained. |
| PriceEURKWh / PriceCentKWh | PriceEURMWh divided by 1,000 / 10. Neither includes retail charges. |
| IsNegative | 1 only when published hourly price is strictly below zero. |
| MonthlyConsumptionWeight | One divided by elapsed hours in that local calendar month. Multiply by monthly kWh assumption. |
| daily_prices.csv | One observed local day; means, extrema, negative-hour count, hours and scenario coefficients. |
| SumEURMWh | Sum of hourly price observations used to form duration-weighted means; not a monetary bill. |
| ConsumptionWeight | Daily sum of MonthlyConsumptionWeight. Missing hours add no weight. |
| WholesaleCostPerMonthlyKWh | Sum of PriceEURKWh × MonthlyConsumptionWeight. Multiply by monthly consumption and gross multiplier. |
| EveningMeanEURMWh | Mean for local 18:00, 19:00, 20:00 and 21:00 starts. |
| Cheapest4MeanEURMWh | Mean of four lowest observed prices in that local day; may be non-consecutive. |
| CheapestHours | Local clock labels of cheapest observed hours. UTC IDs still distinguish repeated clock hours. |
| monthly_prices.csv / yearly_prices.csv | Observed-hour means and coverage, including partial 2026 period. |
| hour_profiles.csv | Year, weekday and clock-hour historical means. Browser heatmap computes arbitrary selected dates from hourly records. |
| calendar.csv | Every requested local date, including the missing source day. |
| tariff_assumptions.json / .csv | Authored planning inputs, not supplier offers. Power BI imports the CSV. |
| electricity.sqlite | Prepared tables and SQL views. |

The snapshot lacks all 24 prices on 10 October 2026. They remain unavailable. Expected observations, observed observations, source nulls and reconciliation differences are reported separately in `reports/data_checks.json`.

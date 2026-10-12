CREATE VIEW negative_price_days AS
SELECT Date, Hours, MeanEURMWh, NegativeHours FROM daily_prices WHERE NegativeHours>0;
CREATE VIEW hourly_timing AS
SELECT Hour, AVG(PriceEURMWh) AS MeanEURMWh, COUNT(*) AS Observations
FROM hourly_prices GROUP BY Hour;
CREATE VIEW flexible_load_opportunity AS
SELECT Date, EveningMeanEURMWh, Cheapest4MeanEURMWh,
       (EveningMeanEURMWh-Cheapest4MeanEURMWh)/1000 AS DifferenceEURPerKWh
FROM daily_prices;

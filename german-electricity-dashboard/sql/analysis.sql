-- Average market price weights every observed elapsed hour equally.
SELECT Year, COUNT(*) AS Hours, AVG(PriceEURMWh) AS MeanEURMWh,
 SUM(IsNegative) AS NegativeHours FROM hourly_prices GROUP BY Year;
-- Hourly negative-price exposure, not quarter-hour negative market periods.
SELECT Month, Hours, MeanEURMWh, NegativeHours, NegativeShare FROM monthly_prices;
-- Europe/Berlin clock hours. Repeated autumn hours retain separate UTC IDs.
SELECT * FROM hourly_timing ORDER BY MeanEURMWh;
-- Flexibility is a scenario with equal energy, not realised savings.
SELECT Date, DifferenceEURPerKWh*12*1.19 AS ScenarioDifferenceEUR
FROM flexible_load_opportunity ORDER BY ScenarioDifferenceEUR DESC LIMIT 20;
-- Inspect high prices; these are observed market prices, not data errors.
SELECT LocalTimestamp, PriceEURMWh FROM hourly_prices ORDER BY PriceEURMWh DESC LIMIT 20;

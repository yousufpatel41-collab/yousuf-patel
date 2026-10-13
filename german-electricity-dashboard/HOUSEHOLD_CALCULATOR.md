# Household electricity bill methodology

One household means one electricity account. No person, apartment-size or room-count multiplier is applied.

## Consumption

- Billed annual consumption is used directly; monthly consumption is multiplied by 12.
- Two meter readings: (last kWh − first kWh) ÷ elapsed calendar days × 365. Both readings must be from the same meter; short and seasonal intervals may be unrepresentative.
- Appliances: annual-label kWh + cycle kWh × cycles/week × 52 + daily kWh × 365 + device watts ÷ 1,000 × hours/day × 365. Additional annual kWh covers electric heating, hot water and other use. Starter inputs are examples, not measured data. Heating and hot water start at zero and must be entered where applicable. Avoid duplicate devices.

## Cost

Supplier tariff: annual kWh × VAT-inclusive ct/kWh ÷ 100 + monthly VAT-inclusive fixed charge × 12. Include a separate meter charge in the fixed-charge input. Monthly budget = annual cost ÷ 12. Bonuses, exports, future tariff changes and different payment schedules are excluded.

Benchmark: BDEW household average 37.0 ct/kWh for 2026 to date, published 21 August 2026 and manually checked 13 October 2026. The reference includes apportioned charges for a 3,500 kWh/year household; no second fixed fee is added. Extrapolation to other consumption is indicative. Prices vary by contract and location. This is not a live tariff feed.

Sources: [BDEW electricity price analysis](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/), [Verbraucherzentrale instalment calculator](https://www.verbraucherzentrale.de/wissen/energie/preise-tarife-anbieterwechsel/rechner-das-ist-ihr-passender-abschlag-fuer-strom-gas-oder-fernwaerme-75669).

Historical SMARD tariffs remain a separate analytical scenario. Their missing-hour coverage does not reduce a full-year household budget. The browser calculator does not change the workbook or Power BI model.

## Checkable examples

3,000 kWh/year × EUR 0.32 + EUR 10/month × 12 = EUR 1,080/year = EUR 90/month.

The same consumption at the benchmark is EUR 1,110/year = EUR 92.50/month, with no separately added fixed charge.

A 300-watt device used two hours daily consumes 219 kWh/year.

Inputs are stored locally in the browser; exports include the method, consumption, tariff, fees, estimates and reference dates.

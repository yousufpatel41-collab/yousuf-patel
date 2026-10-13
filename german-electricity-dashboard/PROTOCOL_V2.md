# V2 protocol — arrival-time, published-price rolling experiment

Status: registered before running V2. The V1 protocol and results were committed together; V1 is not presented as externally pre-registered. This V2 document must be committed and tagged before results or implementation changes are published. V1 data and results remain preserved for comparison.

## Question

Does a forecast improve a rolling charging policy beyond using only already-published day-ahead prices? An evening arrival is a scenario assumption, not a claim about all drivers. Compare the same arrivals, deadlines, efficiencies, energy and charger limits.

## Frozen sessions and information

Use the existing hourly SMARD snapshot, 2024–11 October 2026. Starts at 18:00 Europe/Berlin every three calendar days from 2 January 2025. Two cases: overnight arrival-to-next-day 07:00, 20 battery kWh; two-night arrival-to-second-day 07:00, cumulative 8 battery kWh due at the first departure and 20 total due at the second. Connection only 18:00–07:00, 7.4 kW, 90% efficiency. No extra energy created at negative prices. Session intervals do not overlap within a case; both cases from the same start are dependent and analysed separately. Exclude missing prices/context, retain DST elapsed durations.

At each decision, assume the current and next local delivery day's day-ahead prices have been published by 16:00 Europe/Berlin. Before 16:00 only the current day is known. This is an explicit publication-time convention, not a verified historic publication log. Charge using the first hourly action, then re-plan hourly with remaining energy and cumulative deadlines. Known slots use published actual prices; models predict only hours after that publication boundary. No future realised weather, demand or generation features.

## Strategies

1. Immediate feasible charging: earliest connected slots, respecting all cumulative targets.
2. Known-only rolling: optimise over published-price slots; ignore unknown slots until publication. If known slots cannot meet a mandatory deadline, report infeasibility rather than invent a forecast. In this specified session matrix there is enough known-slot capacity.
3. Seasonal-naive rolling: known prices plus previous-week prices for unknown slots.
4. Fixed-2024 LightGBM rolling: same quantile settings as V1, trained only on 2024.
5. Monthly-retrained LightGBM rolling: expanding past observations; refit at the first encountered decision of each month, training labels strictly before that month's boundary or the decision, whichever is earlier. Hyperparameters unchanged and no test-driven tuning.
6. Chronos-Bolt tiny rolling: checkpoint `f6ff2d2ba9168d498c015bc8dd07e3b395b31b3f`, 512-hour published-price context; no fine-tuning.
7. Same-constraint full-future-price oracle: lower bound, never deployed as an operational strategy.

Hourly allocation is continuous, with nested cumulative minimum-energy deadlines. Validate the allocation against an independent LP including those deadlines. It is a simulation, not a real device controller or battery/trip telemetry model.

## Splits, calibration and promotion

LightGBM initial training: 2024. January–March 2025: interval calibration on unknown-price first-decision forecasts only. April–December 2025: model selection. January–October 2026: test. Monthly refitting during validation/test is permitted only by the predeclared past-only rule. Seasonal-naive residual bands are empirically calibrated; LightGBM/Chronos use non-negative split-conformal expansion. Measure unknown-hour MAE, pinball loss, nominal 80% coverage/width and inference latency. Time dependence and drift preclude guaranteed coverage.

For each case, promotion beyond known-only requires >=2% lower aggregate validation charging cost, no additional deadline/terminal shortfalls, unknown-hour coverage >=75%, median forecast latency <5 seconds, and a positive lower bound for the paired 95% CI on incremental per-session savings versus known-only. If none pass, retain known-only. Test results do not change the selected policy.

## Uncertainty and outcomes

Use deterministic paired moving-block bootstrap: 5,000 resamples, seed 41, consecutive blocks of three sessions (approximately nine days), separately within each case and split. Report mean EUR/session savings and 95% percentile CI versus immediate and versus known-only, oracle gap, aggregate oracle capture when opportunity > EUR 0.01, total euros, monthly downside and misses. Report paired Chronos-minus-monthly-LightGBM savings CI. These intervals describe sampling variability in the historical scenario, not population-level German household effects. Do not clip negative outcomes or reverse the comparator to manufacture significance.

Single-night case is a sanity check: all prices are already published at an 18:00 arrival, so forecasting must have zero incremental operational value relative to the identical known-price schedule.

## Import and external pilot

Support 15/30/60-minute interval energy, complete-hour aggregation only, explicit timestamp/energy mappings, separated German date/time columns, semicolon decimal-comma files and unit selection for interval kWh or Wh. Require timezone/offset or explicit Europe/Berlin conversion; ambiguous autumn timestamps require offsets or an explicit sequence convention, otherwise reject. Cumulative meters and kW power are not silently interpreted as interval energy. Adapters are format mappings, not blanket certification of a named supplier's exports.

Prepare a bilingual invitation and device-local feedback questionnaire/export. No testers are currently available. Record pilot count as zero until real, consented responses exist; no invented users, testimonials or measured real-world savings. External recruitment or messages require the user's chosen destination and explicit authorization.
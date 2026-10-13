# Frozen experiment protocol — 13 October 2026

This protocol is written before viewing the first results of this upgrade.

Train price models on 2024. Calibrate intervals on January–March 2025. Select between seasonal-naive, LightGBM quantile regression and Chronos-Bolt tiny on April–December 2025. Evaluate the selected model once on January–October 2026, an incomplete year. No test-driven tuning. Weekly 48-hour forecast blocks, disjoint, skip blocks with unavailable actual prices, lags or contiguous foundation-model context. No invented prices.

Issue-time convention: the scenario begins at 00:00 UTC; the forecast was issued at 16:00 Europe/Berlin two local calendar days before the first target local date. Only prices through the preceding local delivery day are assumed published. The UTC boundary is checked against that information cutoff. Features use calendar variables and price lags 168/336/504 hours; no future realised weather, demand or renewable production. No weather-forecast archive is available in this release. Hourly SMARD prices remain an approximation to later quarter-hour retail contracts.

Evaluation: MAE and mean pinball loss in EUR/MWh, empirical coverage and width of nominal 80% intervals, wall-clock inference latency and charging cost. Non-negative split-conformal expansion is calibrated on the earlier calibration blocks, with no future test residuals. Time dependence/distribution shift preclude a blanket coverage guarantee. P10/P90 are raw model quantiles; calibrated bounds are separately named.

Synthetic EV evaluation: 20 battery kWh required, 7.4 kW maximum, 90% charging efficiency, available at local hours 18:00–07:00 over each 48-hour block. Same feasible set and delivered energy across all strategies. No claim these are measured German EV sessions. This is a one-shot forecast-driven cost-minimising allocation, not MPC, reinforcement learning or a real device controller. Greedy sorted allocation is exactly optimal for this divisible-energy linear problem; extra LP complexity has no benefit here.

The forecast experiment has a single terminal energy target at the end of its 48 elapsed hours, repeated daily availability, and overnight carry-in availability at the first midnight. Intermediate departures do not impose a second energy target. No trip demand or battery state-of-charge trajectory is assumed. The published-price planner instead covers one arrival-to-departure window with its target due at that departure.

Baseline: charge immediately when available. Operational comparison: cheapest feasible seasonal-naive schedule. Challenger: LightGBM or Chronos forecast-ranked schedule. Hindsight lower bound: same constraints with actual future prices. Gross costs use illustrative 1.19 wholesale multiplier plus EUR 0.20/kWh non-energy charges. Identical fixed fees cancel for charging-only comparison. Oracle capture = aggregate (immediate − model)/(immediate − oracle); undefined when opportunity <= EUR 0.01. Report negative captures without clipping. Also report euros saved, oracle gap, largest monthly extra cost, and target misses.

Promotion gate: validation charging cost improves versus seasonal-naive by at least 2%; no extra missed targets; calibrated 80% interval coverage at least 75%; per-block inference below 5 seconds on this CPU. Among qualifying challengers select lowest validation charging cost; otherwise retain seasonal-naive. Test outcomes may revoke confidence but do not cause a new selection. Forecast error is secondary to decision cost.

Personal CSV evaluation uses the user's own chronological observations only. It does not imply unseen-household generalisation. The included demo is synthetic and labelled. External user feedback is a pending study, not completed validation. The London dataset is a possible later external household benchmark; it is not silently transferred into German claims. Causal inference, NILM, heat-pump control and solar/battery optimisation remain outside this release.

## Checkpoint provenance

Chronos-Bolt tiny is pinned to Hugging Face revision `f6ff2d2ba9168d498c015bc8dd07e3b395b31b3f` (28 November 2024), before the evaluation windows. Its safetensors SHA-256 is `75068728d376d2bec670379eeef4bfb4d24c0cfe24d957451f8d19b447030a32`. The initially retrieved current revision has the identical weight hash; subsequent model-card edits do not change weights. Pretraining is external and its complete dataset provenance is not independently audited.

The seasonal-naive residual band is an empirical calibration-band baseline. LightGBM and Chronos intervals receive a non-negative split-conformal expansion using the earlier calibration residuals. Dependence between hours and market shifts prevent a universal coverage guarantee.

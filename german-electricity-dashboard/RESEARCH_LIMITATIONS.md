# Research limits and measured lessons

The model choice was made on 2025 validation results and retained for the separate 2026 test. No model tuning followed test inspection. All intervals and target energy requirements are identical across charging strategies. Published prices need no forecasting. The unknown-price experiment targets 48-hour future periods beyond the assumed publication boundary. The source is hourly SMARD, not exact modern quarter-hour supplier settlement.

40 weekly simulated EV sessions in each validation/test period do not establish annual savings, German household representativeness, a future win probability or measured behavioural effects. No real charging-session history was available. A small nominal 80% hourly interval does not imply 80% confidence in total scheduled cost: hours are dependent and scheduling selects prices. The optional P90 weight is a heuristic, not stochastic MPC or CVaR. No online control or automatic model refresh exists.

Measured lessons: the seasonal-naive schedule lost money versus immediate charging in the 2025 validation sample. LightGBM passed the promotion gate but did not beat Chronos-Bolt tiny on the specified validation decision-cost criterion. Chronos passed selection but still had a month with extra cost on the 2026 test. Even the best tested strategy captured less than half the aggregate perfect-foresight opportunity. Full numeric results are preserved; no losses are clipped.

A separate LP reproduces the greedy optimum for divisible hourly energy and linear prices. This does not validate integer charging sessions, minimum charging duration, battery state-of-charge trajectories or physical device control. Those require a richer model.

Personal-file analysis is device-local and its demand forecast is a seasonal baseline. Missing readings are excluded; incomplete half-hour pairs cannot supply a full hourly connection constraint. The method matches UTC hours, which can differ from local routines across DST. Imported consumption is historical, not a guarantee of future household demand. External user testing has a protocol but no completed participants.

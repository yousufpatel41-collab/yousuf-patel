-- Net billed cost reconciles positive charges and negative adjustments.
SELECT SUM(CASE WHEN BilledCost>0 THEN BilledCost ELSE 0 END) AS PositiveCharges,
       SUM(CASE WHEN BilledCost<0 THEN BilledCost ELSE 0 END) AS NegativeAdjustments,
       SUM(BilledCost) AS NetBilledCost FROM billing_records;

-- Largest services. Preserve negative adjustments in each service total.
SELECT * FROM service_spend ORDER BY BilledCost DESC LIMIT 10;

-- Cost allocation: absolute cost avoids cancellation in the percentage basis.
SELECT SUM(UnallocatedAbsoluteCost)/NULLIF(SUM(AbsoluteBilledCost),0) AS UnallocatedShare
FROM billing_records;

-- Prorated illustrative budget for the actual source window, not a full month.
WITH coverage AS (
 SELECT CAST(julianday(MAX(ChargeDate))-julianday(MIN(ChargeDate))+1 AS REAL) AS DaysCovered,
 CAST(strftime('%d',date(MIN(ChargeDate),'start of month','+1 month','-1 day')) AS REAL) AS MonthDays
 FROM billing_records
)
SELECT a.SubAccountName, a.BilledCost,
       a.MonthlyBudget*c.DaysCovered/c.MonthDays AS PeriodBudget,
       a.BilledCost-a.MonthlyBudget*c.DaysCovered/c.MonthDays AS OverUnderBudget
FROM account_budget_review a CROSS JOIN coverage c ORDER BY OverUnderBudget DESC;

-- Review candidates, not confirmed incidents or savings opportunities.
SELECT * FROM anomalies ORDER BY ExcessCost DESC;

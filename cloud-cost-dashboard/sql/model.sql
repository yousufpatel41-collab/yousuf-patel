-- One billing record per ingested source row. Negative charges are retained.
CREATE VIEW account_spend AS
SELECT SubAccountId, SubAccountName, BillingMonth,
       SUM(BilledCost) AS BilledCost, SUM(EffectiveCost) AS EffectiveCost,
       COUNT(*) AS RecordCount
FROM billing_records GROUP BY SubAccountId, SubAccountName, BillingMonth;

-- Aggregate costs before joining a one-row-per-account/month budget.
-- Joining the budget directly to billing records would multiply the budget.
CREATE VIEW account_budget_review AS
SELECT s.*, b.MonthlyBudget, b.BudgetBasis
FROM account_spend s
LEFT JOIN budgets b ON s.SubAccountId=b.SubAccountId AND s.BillingMonth=b.BillingMonth;

CREATE VIEW service_spend AS
SELECT ServiceName, GROUP_CONCAT(DISTINCT ServiceCategory) AS ServiceCategories, SUM(BilledCost) AS BilledCost,
       SUM(EffectiveCost) AS EffectiveCost, COUNT(*) AS RecordCount
FROM billing_records GROUP BY ServiceName;

CREATE VIEW department_allocation AS
SELECT Department, SUM(BilledCost) AS NetBilledCost,
       SUM(AbsoluteBilledCost) AS AbsoluteCost, COUNT(*) AS RecordCount
FROM billing_records GROUP BY Department;

"""Checks that catch financial aggregation errors and broken BI relationships."""
from pathlib import Path
import csv, json, sqlite3, unittest, zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

class FinancialModel(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(ROOT/'data/cloud_costs.sqlite')
        self.meta=json.loads((ROOT/'reports/metadata.json').read_text())
    def tearDown(self):self.db.close()
    def scalar(self,sql):return self.db.execute(sql).fetchone()[0]
    def test_net_includes_adjustments(self):
        positive=self.scalar('SELECT SUM(BilledCost) FROM billing_records WHERE BilledCost>0')
        negative=self.scalar('SELECT SUM(BilledCost) FROM billing_records WHERE BilledCost<0')
        self.assertLess(negative,0)
        self.assertAlmostEqual(positive+negative,self.meta['net_billed_cost'],places=6)
    def test_daily_grain_reconciles_cost_and_rows(self):
        self.assertAlmostEqual(self.scalar('SELECT SUM(BilledCost) FROM daily_costs'),self.meta['net_billed_cost'],places=6)
        self.assertEqual(self.scalar('SELECT SUM(RecordCount) FROM daily_costs'),self.meta['source_rows'])
    def test_services_are_not_split_by_category(self):
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM service_spend'),self.meta['service_count'])
        self.assertAlmostEqual(self.scalar("SELECT BilledCost FROM service_spend WHERE ServiceName='Virtual Machines'"),3288.60312112323,places=6)
    def test_budget_join_does_not_multiply_budget(self):
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM account_budget_review'),13)
        self.assertAlmostEqual(self.scalar('SELECT SUM(MonthlyBudget) FROM account_budget_review'),36100)
        self.assertAlmostEqual(36100*19/30,self.meta['period_scenario_budget'])
    def test_account_id_not_display_name_is_key(self):
        self.assertEqual(self.scalar('SELECT COUNT(DISTINCT SubAccountId) FROM budgets'),13)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM budgets WHERE SubAccountName='Pay-As-You-Go'"),2)
    def test_allocation_uses_absolute_cost_basis(self):
        ratio=self.scalar('SELECT SUM(UnallocatedAbsoluteCost)/SUM(AbsoluteBilledCost) FROM billing_records')
        self.assertAlmostEqual(ratio,0.8432837253059278,places=5)
        self.assertGreaterEqual(ratio,0);self.assertLessEqual(ratio,1)
    def test_sql_queries_execute(self):
        source=(ROOT/'sql/analysis.sql').read_text()
        for statement in source.split(';'):
            if statement.strip():self.db.execute(statement).fetchall()
    def test_powerbi_dimension_keys_and_relationships(self):
        model=json.loads((ROOT/'powerbi/CloudCosts.SemanticModel/model.bim').read_text())['model']
        self.assertEqual(len(model['relationships']),5)
        with (ROOT/'data/daily_costs.csv').open(newline='',encoding='utf-8') as f:facts=list(csv.DictReader(f))
        for file,key in [('dim_accounts.csv','SubAccountId'),('dim_services.csv','ServiceName'),('dim_departments.csv','Department')]:
            with (ROOT/'data'/file).open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
            keys=[r[key] for r in rows];self.assertEqual(len(keys),len(set(keys)))
            self.assertTrue({r[key] for r in facts}.issubset(set(keys)))
    def test_excel_has_formulas_and_two_native_charts(self):
        with zipfile.ZipFile(ROOT/'Cloud_Cost_Review.xlsx') as z:
            charts=[n for n in z.namelist() if '/charts/chart' in n and n.endswith('.xml')]
            self.assertEqual(len(charts),2)
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml')); ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            cells={c.attrib['r']:c for c in sheet.findall('.//x:c',ns)}
            self.assertIn('SUMIFS',cells['B9'].find('x:f',ns).text)
            self.assertAlmostEqual(float(cells['B9'].find('x:v',ns).text),self.meta['net_billed_cost'],places=6)

if __name__=='__main__':unittest.main(verbosity=2)

from pathlib import Path
import json,sqlite3,hashlib,unittest,zipfile
import xml.etree.ElementTree as ET
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
class ElectricityModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hourly=pd.read_csv(ROOT/'data/hourly_prices.csv');cls.daily=pd.read_csv(ROOT/'data/daily_prices.csv');cls.monthly=pd.read_csv(ROOT/'data/monthly_prices.csv')
    def test_official_2025_benchmark(self):
        prices=self.hourly[self.hourly.Year==2025];self.assertEqual(len(prices),8760);self.assertAlmostEqual(prices.PriceEURMWh.mean(),89.32,places=2);self.assertEqual(prices.IsNegative.sum(),573)
    def test_2024_leap_year(self):self.assertEqual(len(self.hourly[self.hourly.Year==2024]),8784)
    def test_timestamp_key_and_gap(self):
        self.assertFalse(self.hourly.TimestampMs.duplicated().any());self.assertFalse((self.hourly.Date=='2026-10-10').any());self.assertEqual(json.loads((ROOT/'reports/data_checks.json').read_text())['missing_hours'],24)
    def test_dst_is_retained(self):
        self.assertEqual(int(self.daily[self.daily.Date=='2024-03-31'].Hours.iloc[0]),23)
        self.assertEqual(int(self.daily[self.daily.Date=='2024-10-27'].Hours.iloc[0]),25)
    def test_units_and_negative_prices(self):
        self.assertAlmostEqual((self.hourly.PriceEURMWh/1000-self.hourly.PriceEURKWh).abs().max(),0)
        self.assertAlmostEqual((self.hourly.PriceEURMWh/10-self.hourly.PriceCentKWh).abs().max(),0)
        self.assertLess(self.hourly.PriceEURKWh.min(),0)
    def test_aggregation_uses_hour_weight(self):
        self.assertAlmostEqual(self.daily.SumEURMWh.sum()/self.daily.Hours.sum(),self.hourly.PriceEURMWh.mean(),places=8)
        self.assertEqual(self.daily.Hours.sum(),len(self.hourly))
    def test_equal_monthly_consumption_and_partial_month(self):
        complete=self.monthly[self.monthly.Month!='2026-10'];self.assertTrue((complete.ConsumptionWeight-1).abs().max()<1e-10)
        last=self.monthly[self.monthly.Month=='2026-10'].ConsumptionWeight.iloc[0];self.assertAlmostEqual(last,240/745)
    def test_same_energy_flexible_schedule(self):
        self.assertTrue((self.daily.Cheapest4MeanEURMWh<=self.daily.EveningMeanEURMWh+1e-9).all())
        for day in ['2024-03-31','2024-10-27','2025-06-01']:
            prices=self.hourly[self.hourly.Date==day];expected=prices.nsmallest(4,'PriceEURMWh').PriceEURMWh.mean();actual=self.daily[self.daily.Date==day].Cheapest4MeanEURMWh.iloc[0];self.assertAlmostEqual(actual,expected)
    def test_source_checksums(self):
        for source in json.loads((ROOT/'data/source_manifest.json').read_text()):self.assertEqual(hashlib.sha256((ROOT/'data/raw'/source['file']).read_bytes()).hexdigest(),source['sha256'])
    def test_sql_queries_and_reconciliation(self):
        with sqlite3.connect(ROOT/'data/electricity.sqlite') as db:
            self.assertAlmostEqual(db.execute('SELECT AVG(PriceEURMWh) FROM hourly_prices').fetchone()[0],self.hourly.PriceEURMWh.mean(),places=8)
            source='\n'.join(line for line in (ROOT/'sql/analysis.sql').read_text().splitlines() if not line.strip().startswith('--'))
            for sql in source.split(';'):
                if sql.strip():db.execute(sql).fetchall()
    def test_powerbi_unique_date_dimension(self):
        dates=pd.read_csv(ROOT/'data/calendar.csv');self.assertFalse(dates.Date.duplicated().any());self.assertTrue(set(self.daily.Date)<=set(dates.Date))
    def test_workbook_cached_total_and_native_charts(self):
        with zipfile.ZipFile(ROOT/'German_Electricity_Review.xlsx') as z:
            self.assertEqual(len([n for n in z.namelist() if '/charts/chart' in n and n.endswith('.xml')]),2)
            ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));cells={c.attrib['r']:c for c in sheet.findall('.//x:c',ns)}
            self.assertAlmostEqual(float(cells['E9'].find('x:v',ns).text),self.hourly.PriceEURMWh.mean(),places=6)
            self.assertIn('SUMIFS',cells['B27'].find('x:f',ns).text)
if __name__=='__main__':unittest.main(verbosity=2)

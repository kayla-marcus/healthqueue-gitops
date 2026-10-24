import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import dora_synthetic as d


def row(lead, failed=False, recovery=None):
    return {"lead_time_minutes": lead, "failed": failed,
            "recovery_minutes": recovery if failed else ""}


class MetricCalculationTests(unittest.TestCase):
    def test_known_inputs(self):
        rows = [row(60), row(120), row(180, True, 30), row(240, True, 90)]
        m = d.compute_metrics(rows, window_days=10)
        self.assertEqual(m["deployments"], 4)
        self.assertAlmostEqual(m["deploys_per_day"], 0.4)
        self.assertAlmostEqual(m["deploys_per_week"], 2.8)
        self.assertEqual(m["lead_median"], 150)
        self.assertEqual(m["cfr_percent"], 50.0)
        self.assertEqual(m["recovery_median"], 60)
        self.assertEqual(m["recovery_mean"], 60)

    def test_no_failures(self):
        m = d.compute_metrics([row(60), row(90)], window_days=10)
        self.assertEqual(m["cfr_percent"], 0.0)
        self.assertIsNone(m["recovery_median"])

    def test_percentile(self):
        self.assertEqual(d.percentile([1, 2, 3, 4, 5], 50), 3)
        self.assertEqual(d.percentile([10, 20], 90), 19)


class ClassificationTests(unittest.TestCase):
    def test_frequency(self):
        self.assertEqual(d.classify_frequency(2.0), "Elite")
        self.assertEqual(d.classify_frequency(0.5), "High")
        self.assertEqual(d.classify_frequency(0.05), "Medium")
        self.assertEqual(d.classify_frequency(0.01), "Low")

    def test_lead_time(self):
        self.assertEqual(d.classify_lead_time(600), "Elite")
        self.assertEqual(d.classify_lead_time(3 * 1440), "High")
        self.assertEqual(d.classify_lead_time(14 * 1440), "Medium")
        self.assertEqual(d.classify_lead_time(60 * 1440), "Low")

    def test_recovery(self):
        self.assertEqual(d.classify_recovery(30), "Elite")
        self.assertTrue(d.classify_recovery(300).startswith("High or Medium"))
        self.assertTrue(d.classify_recovery(3 * 1440).startswith("Between"))
        self.assertEqual(d.classify_recovery(10 * 1440), "Low")

    def test_change_failure_rate_uses_nearest_typical_value(self):
        self.assertEqual(d.classify_cfr(4), "Elite")
        self.assertEqual(d.classify_cfr(10), "Medium")  # Medium (10%) is below High (20%)
        self.assertEqual(d.classify_cfr(19), "High")
        self.assertEqual(d.classify_cfr(50), "Low")
        self.assertEqual(d.classify_cfr(15), "Medium")  # exact tie goes to the lower typical value


class BusinessHoursTests(unittest.TestCase):
    def test_weekend_moves_to_monday_morning(self):
        saturday = datetime(2027, 1, 9, 12, 0)
        self.assertEqual(d.next_business_time(saturday), datetime(2027, 1, 11, 9, 0))

    def test_evening_moves_to_next_morning(self):
        self.assertEqual(d.next_business_time(datetime(2027, 1, 5, 18, 30)), datetime(2027, 1, 6, 9, 0))

    def test_friday_evening_moves_to_monday(self):
        self.assertEqual(d.next_business_time(datetime(2027, 1, 8, 17, 0)), datetime(2027, 1, 11, 9, 0))

    def test_business_hours_unchanged(self):
        t = datetime(2027, 1, 5, 10, 15)
        self.assertEqual(d.next_business_time(t), t)


class GeneratedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.censored = d.generate(d.SEED)

    def test_is_deterministic(self):
        again, _ = d.generate(d.SEED)
        self.assertEqual(self.rows, again)

    def test_different_seed_differs(self):
        other, _ = d.generate(d.SEED + 1)
        self.assertNotEqual(self.rows, other)

    def test_all_rows_inside_the_90_day_window(self):
        for r in self.rows:
            self.assertLess(datetime.fromisoformat(r["deploy_time"]), d.END)
            self.assertGreaterEqual(datetime.fromisoformat(r["commit_time"]), d.START)

    def test_lead_time_equals_sum_of_stages(self):
        for r in self.rows:
            total = sum(r[col] for col, _, _ in d.LEAD_STAGES)
            self.assertAlmostEqual(r["lead_time_minutes"], total, places=1)

    def test_recovery_equals_sum_of_recovery_stages(self):
        failed = [r for r in self.rows if r["failed"]]
        self.assertTrue(failed)
        for r in failed:
            total = sum(r[col] for col, _, _ in d.RECOVERY_STAGES)
            self.assertAlmostEqual(r["recovery_minutes"], total, places=1)

    def test_every_row_is_labeled_synthetic(self):
        self.assertTrue(all(r["data_source"] == "SYNTHETIC" for r in self.rows))

    def test_outputs_are_labeled_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path, report_path, _, _ = d.write_outputs(self.rows, self.censored, d.SEED, Path(tmp))
            self.assertIn("SYNTHETIC", csv_path.name)
            self.assertIn("SYNTHETIC", report_path.name)
            text = report_path.read_text(encoding="utf-8")
            self.assertTrue(text.count("SYNTHETIC DATA") >= 2)  # banner at top and bottom
            self.assertIn("must not be read, quoted, or presented as HealthQueue's real delivery performance", text)


if __name__ == "__main__":
    unittest.main()

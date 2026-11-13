import unittest

from effect_check import Status, check_effect
from examples.mock_notify import FakeClock


def run(result, verify, **kw):
    clock = FakeClock()
    return check_effect(result, verify, clock=clock.now, sleep=clock.sleep, **kw)


class CheckEffectTests(unittest.TestCase):
    def test_confirmed_on_first_look(self):
        v = run({"status": "success"}, lambda: True)
        self.assertEqual(v.status, Status.CONFIRMED)
        self.assertEqual(v.attempts, 1)
        self.assertTrue(v.safe_to_report_success)

    def test_confirmed_after_polling(self):
        clock = FakeClock()
        v = check_effect(
            {"status": "success"},
            lambda: clock.now() >= 0.3,
            timeout_s=1.0,
            interval_s=0.1,
            clock=clock.now,
            sleep=clock.sleep,
        )
        self.assertEqual(v.status, Status.CONFIRMED)
        self.assertGreater(v.attempts, 1)

    def test_not_confirmed_when_effect_never_appears(self):
        v = run({"status": "success"}, lambda: False, timeout_s=0.5, interval_s=0.1)
        self.assertEqual(v.status, Status.NOT_CONFIRMED)
        self.assertFalse(v.safe_to_report_success)

    def test_short_window_gives_false_alarm_on_slow_effect(self):
        clock = FakeClock()
        v = check_effect(
            {"status": "success"},
            lambda: clock.now() >= 0.3,
            timeout_s=0.1,
            interval_s=0.1,
            clock=clock.now,
            sleep=clock.sleep,
        )
        self.assertEqual(v.status, Status.NOT_CONFIRMED)

    def test_tool_reported_failure_is_passed_through(self):
        v = run({"status": "error"}, lambda: True)
        self.assertEqual(v.status, Status.TOOL_REPORTED_FAILURE)
        self.assertEqual(v.attempts, 0)

    def test_no_verifier_is_unverifiable_never_success(self):
        v = run({"status": "success"}, None)
        self.assertEqual(v.status, Status.UNVERIFIABLE)
        self.assertFalse(v.safe_to_report_success)

    def test_broken_verifier_is_unverifiable_never_success(self):
        def boom():
            raise RuntimeError("down")

        v = run({"status": "success"}, boom)
        self.assertEqual(v.status, Status.UNVERIFIABLE)
        self.assertIn("RuntimeError", v.detail)
        self.assertFalse(v.safe_to_report_success)

    def test_custom_success_rule(self):
        v = run({"code": 200}, lambda: True, claims_success=lambda r: r.get("code") == 200)
        self.assertEqual(v.status, Status.CONFIRMED)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            run({"status": "success"}, lambda: True, timeout_s=-1)
        with self.assertRaises(ValueError):
            run({"status": "success"}, lambda: True, interval_s=0)


if __name__ == "__main__":
    unittest.main()

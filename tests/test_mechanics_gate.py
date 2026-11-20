"""The mechanics gate must run both proofs and fail if either does (ADR-422)."""

from __future__ import annotations

import unittest
from unittest import mock

from tools import mechanics_gate


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class MechanicsGateTest(unittest.TestCase):
    def test_both_proofs_run_and_pass(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return _Completed(stdout="proof ok")

        with mock.patch.object(mechanics_gate.subprocess, "run", side_effect=fake_run):
            code = mechanics_gate.main([])

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn("tools/ai_play.py", calls[0])
        self.assertIn("tools/chaos_fuzz.py", calls[1])
        self.assertIn("--save-every", calls[1])

    def test_a_failing_campaign_fails_the_gate(self):
        def fake_run(command, **kwargs):
            return _Completed(returncode=1 if "ai_play" in command[1] else 0,
                              stdout="Chaos fuzz: ok")

        with mock.patch.object(mechanics_gate.subprocess, "run", side_effect=fake_run):
            self.assertEqual(mechanics_gate.main([]), 1)

    def test_a_failing_fuzz_fails_the_gate(self):
        def fake_run(command, **kwargs):
            return _Completed(returncode=1 if "chaos_fuzz" in command[1] else 0,
                              stdout="campaign ok")

        with mock.patch.object(mechanics_gate.subprocess, "run", side_effect=fake_run):
            self.assertEqual(mechanics_gate.main([]), 1)

    def test_a_timeout_is_a_failure_with_a_reason(self):
        def fake_run(command, **kwargs):
            raise mechanics_gate.subprocess.TimeoutExpired(command, 300)

        with mock.patch.object(mechanics_gate.subprocess, "run", side_effect=fake_run):
            self.assertEqual(mechanics_gate.main([]), 1)

    def test_the_fuzz_seed_and_action_count_are_forwarded(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return _Completed(stdout="ok")

        with mock.patch.object(mechanics_gate.subprocess, "run", side_effect=fake_run):
            mechanics_gate.main(["--fuzz-actions", "77", "--fuzz-seed", "9", "--steps", "42"])

        self.assertIn("42", calls[0])
        self.assertIn("77", calls[1])
        self.assertIn("9", calls[1])

    def test_misuse_is_refused(self):
        with self.assertRaises(SystemExit):
            mechanics_gate.main(["--steps", "0"])


if __name__ == "__main__":
    unittest.main()

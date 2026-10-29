"""Flight-log windowing: galactic news must outlive routine AI-trade chatter."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.logbook import (
    LOG_LIMIT,
    is_notable,
    summarize_trades,
    trim_log,
)
from voidfarer.models import GameEvent


TRADE = "AI TRADE: Captain Vega moved 4x fuel_cells to pulsar_psr."
WAR = "WAR: Sol Coalition captured Lyra from Void Corsairs; 1,200 civilians displaced."
PEACE = "PEACE: Sol Coalition and Void Corsairs sign a treaty; status quo restored."
DECLARED = "WAR DECLARED: Sol Coalition (Halden) moves against Void Corsairs."
ELIMINATED = "FACTION ELIMINATED: Iron Meridian has no remaining territory."


class SummarizeTradesTest(unittest.TestCase):
    def test_two_captain_lines_become_one_summary(self):
        lines = [
            "AI TRADE: Captain Vega moved 4x fuel_cells to pulsar_psr.",
            "AI TRADE: Nyx the Broker moved 2x titanium to lyra.",
        ]
        self.assertEqual(
            summarize_trades(lines),
            ["AI TRADE: 2 runs moved 6 crates (Captain Vega, Nyx the Broker)."],
        )

    def test_summary_keeps_the_position_of_the_first_trade_line(self):
        lines = ["MARKET: shock", TRADE, "MONTH END: payroll"]
        out = summarize_trades(lines)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], "MARKET: shock")
        self.assertTrue(out[1].startswith("AI TRADE: 1 run moved 4 crate"))
        self.assertEqual(out[2], "MONTH END: payroll")

    def test_lines_that_are_not_trades_pass_through(self):
        self.assertEqual(summarize_trades([WAR]), [WAR])


class NotableNewsTest(unittest.TestCase):
    def test_war_news_is_notable(self):
        for line in (WAR, PEACE, DECLARED, ELIMINATED):
            self.assertTrue(is_notable(line), line)

    def test_routine_chatter_is_not_notable(self):
        for line in (TRADE, "MONTH END: crew payroll runs 65 cr/month.",
                     "AI TRADE: 2 runs moved 6 crates (Vega, Nyx)."):
            self.assertFalse(is_notable(line), line)

    def test_trade_spam_cannot_evict_a_capture(self):
        lines = [WAR] + [TRADE] * 40
        kept = trim_log(lines)
        self.assertEqual(len(kept), LOG_LIMIT)
        self.assertIn(WAR, kept)

    def test_the_newest_half_of_the_log_always_survives(self):
        lines = [WAR] * 30 + [f"local {index}" for index in range(10)]
        kept = trim_log(lines)
        self.assertEqual(len(kept), LOG_LIMIT)
        self.assertEqual(kept[-5:], lines[-5:])

    def test_older_news_is_not_promoted_past_newer_news(self):
        older_news = [f"WAR: front {index} collapsed." for index in range(15)]
        lines = older_news + [TRADE] * 30
        kept = trim_log(lines)
        self.assertEqual(len(kept), LOG_LIMIT)
        self.assertIn(older_news[-1], kept)
        self.assertNotIn(older_news[0], kept, "the oldest headline should yield to newer ones")

    def test_trim_keeps_the_newest_lines_when_nothing_is_notable(self):
        lines = [f"line {index}" for index in range(30)]
        kept = trim_log(lines)
        self.assertEqual(kept, lines[-LOG_LIMIT:])

    def test_short_logs_are_untouched(self):
        pristine = [WAR, TRADE]
        self.assertEqual(trim_log(pristine), pristine)


class WarNewsEventsTest(unittest.TestCase):
    def test_capture_and_treaty_become_notifications(self):
        events = SimulationEngine.war_news_events([WAR, PEACE], 120, [])
        self.assertEqual([event.kind for event in events], ["war", "war"])
        self.assertEqual([event.title for event in events],
                         ["System Captured", "Peace Treaty Signed"])
        self.assertEqual(events[0].message, WAR)
        self.assertFalse(events[0].dismissed)

    def test_declarations_stay_in_the_log_only(self):
        self.assertEqual(SimulationEngine.war_news_events([DECLARED], 7, []), [])

    def test_at_most_two_events_per_tick(self):
        lines = [WAR, PEACE, ELIMINATED]
        self.assertEqual(len(SimulationEngine.war_news_events(lines, 9, [])), 2)

    def test_an_undismissed_duplicate_is_not_repeated(self):
        existing = [GameEvent(id="evt_1_1", kind="war", title="System Captured",
                              message=WAR, tick=1, dismissed=False)]
        self.assertEqual(SimulationEngine.war_news_events([WAR], 2, existing), [])

    def test_a_dismissed_event_may_be_announced_again(self):
        existing = [GameEvent(id="evt_1_1", kind="war", title="System Captured",
                              message=WAR, tick=1, dismissed=True)]
        self.assertEqual(len(SimulationEngine.war_news_events([WAR], 2, existing)), 1)


class WarReachesThePlayerTest(unittest.TestCase):
    def test_a_simulated_campaign_shows_a_war_headline_to_the_player(self):
        engine = SimulationEngine(seed=42)
        war_events = []
        for _ in range(1200):
            engine.tick(1)
            war_events = [event for event in engine.state.events if event.kind == "war"]
            if war_events:
                break
        self.assertTrue(war_events, "no capture, treaty or elimination reached the cockpit")
        self.assertTrue(any(event.title in ("System Captured", "Peace Treaty Signed",
                                            "Faction Eliminated") for event in war_events))

    def test_trade_chatter_is_summarized_once_per_tick(self):
        engine = SimulationEngine(seed=42)
        engine.tick(1)
        log = list(engine.state.ship.flight_log)
        trade_lines = [line for line in log if line.startswith("AI TRADE:")]
        for line in trade_lines:
            self.assertIn("run", line)
            # The raw per-captain form is "moved 4x fuel_cells to ...".
            self.assertNotRegex(line, r"moved \d+x ")

    def test_log_never_exceeds_its_limit(self):
        engine = SimulationEngine(seed=42)
        for _ in range(40):
            engine.tick(1)
            self.assertLessEqual(len(engine.state.ship.flight_log), LOG_LIMIT)


if __name__ == "__main__":
    unittest.main()

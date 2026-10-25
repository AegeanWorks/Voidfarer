"""Unit and integration tests for the living crew, volume-aware market, and cash-flow mechanics."""

import http.client
import json
import random
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import cmd_crew, cmd_status, main
from voidfarer.crew import (
    RESIGN_MORALE,
    apply_morale_event,
    shore_leave_restore,
    tick_crew,
)
from voidfarer.engine import SimulationEngine
from voidfarer.models import CrewMember
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _member(member_id="c1", morale=80.0, status="active", wage=30):
    return CrewMember(
        id=member_id,
        name=f"Crew {member_id}",
        role="pilot",
        skill=3,
        morale=morale,
        wage=wage,
        portrait="crew_01",
        specialty="evasion",
        status=status,
    )


class TestCrewMoraleCore(unittest.TestCase):
    def test_morale_event_clamps_and_logs(self):
        crew = (_member("c1", morale=95.0),)
        updated, log = apply_morale_event(crew, 6.0, "victory")
        self.assertEqual(updated[0].morale, 100.0)
        self.assertIsNotNone(log)
        self.assertIn("+6", log)

        updated, log = apply_morale_event(updated, -40.0, "storm")
        self.assertEqual(updated[0].morale, 60.0)

        updated, log = apply_morale_event(updated, -80.0, "collapse")
        self.assertEqual(updated[0].morale, 0.0)

        # Zero delta and empty crews pass through
        self.assertIsNone(apply_morale_event((), 5.0, "x")[1])
        same, no_log = apply_morale_event(crew, 0.0, "x")
        self.assertIsNone(no_log)

    def test_inactive_members_do_not_drift(self):
        crew = (_member("c1", morale=50.0), _member("c2", morale=80.0, status="inactive"))
        updated, paid, logs = tick_crew(crew, 10, 10_000, rng=random.Random(7))
        self.assertEqual(updated[1].morale, 80.0, "inactive crew must not gain morale")
        self.assertGreater(updated[0].morale, 50.0)

    def test_unpaid_crew_can_resign_deterministically(self):
        crew = (_member("c1", morale=RESIGN_MORALE - 5.0),)
        rng = random.Random(3)
        resigned = False
        for _ in range(300):
            updated, _paid, logs = tick_crew(crew, 1, 0, rng=rng)
            if any("resigned" in line.lower() for line in logs):
                resigned = True
                self.assertEqual(len(updated), 0)
                break
            crew = updated
        self.assertTrue(resigned, "unpaid low-morale crew must eventually resign")

    def test_paid_crew_never_resigns(self):
        crew = (_member("c1", morale=1.0),)
        rng = random.Random(3)
        for _ in range(200):
            updated, paid, logs = tick_crew(crew, 1, 100_000, rng=rng)
            self.assertEqual(len(updated), 1)
            self.assertFalse(any("resigned" in line.lower() for line in logs))
            crew = updated

    def test_critical_morale_warning_is_logged(self):
        crew = (_member("c1", morale=25.0),)
        _updated, _paid, logs = tick_crew(crew, 1, 0, rng=random.Random(1))
        self.assertTrue(any("MORALE CRITICAL" in line for line in logs))

    def test_shore_leave_restore_math(self):
        crew = (_member("c1", morale=50.0), _member("c2", morale=95.0), _member("c3", morale=100.0, status="inactive"))
        updated, restored, cost = shore_leave_restore(crew)
        self.assertEqual(updated[0].morale, 85.0)
        self.assertEqual(updated[1].morale, 100.0)
        self.assertEqual(updated[2].morale, 100.0)
        self.assertEqual(restored, 40)
        self.assertEqual(cost, 25 + 6 * 40)


class TestEngineMoraleEvents(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _crew_morale(self):
        return {m.id: m.morale for m in self.engine.state.ship.crew}

    def test_story_choice_celebration_raises_morale(self):
        before = self._crew_morale()
        ok, msg = self.engine.make_story_choice("choice_vance_telemetry")
        self.assertTrue(ok, msg)
        after = self._crew_morale()
        for member_id, morale in before.items():
            self.assertAlmostEqual(after[member_id], min(100.0, morale + 6.0), places=1)

    def test_hostile_arrival_lowers_morale(self):
        from voidfarer.navigation import shortest_route

        target = self.engine.current_system.connections[0]
        target_faction = self.engine.state.systems[target].faction
        from voidfarer.factions import get_faction_id_from_name

        faction_id = get_faction_id_from_name(target_faction)
        standings = dict(self.engine.state.ship.faction_standings)
        standings[faction_id] = -60
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(faction_standings=standings, fuel=80),
                active_anomaly=None,
                active_combat=None,
            )
        before = self._crew_morale()
        ok, msg = self.engine.jump(target)
        self.assertTrue(ok, msg)
        after = self._crew_morale()
        for member_id, morale in before.items():
            self.assertAlmostEqual(after[member_id], max(0.0, morale - 2.0), places=1)

    def test_void_storm_lowers_morale(self):
        from voidfarer.navigation import shortest_route

        path = shortest_route(self.engine.state.systems, "sol", "cygnus_x1")
        for step in path[1:]:
            with self.engine.lock:
                self.engine.state = self.engine._clone_state(
                    ship=self.engine._clone_ship(fuel=80), active_anomaly=None, active_combat=None
                )
            ok, msg = self.engine.jump(step)
            self.assertTrue(ok, msg)
        ok, msg = self.engine.orbit("cygnus_x1_black_hole")
        self.assertTrue(ok, msg)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(active_anomaly=None, active_combat=None)
        ok, msg = self.engine.void_dive("golconda")
        self.assertTrue(ok, msg)

        before = self._crew_morale()
        with patch.object(self.engine.rng, "random", return_value=0.0):
            self.engine.tick(1)
        after = self._crew_morale()
        for member_id, morale in before.items():
            self.assertLessEqual(after[member_id], morale)
        self.assertTrue(any("void storm shear" in line.lower() for line in self.engine.state.ship.flight_log))


class TestShoreLeave(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)
        station = [b for b in self.engine.current_system.bodies if b.station_dockable][0]
        ok, msg = self.engine.orbit(station.id)
        self.assertTrue(ok, msg)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_shore_leave_requires_docking(self):
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(orbiting_body_id=None))
        ok, msg = self.engine.shore_leave()
        self.assertFalse(ok)
        self.assertIn("docking", msg.lower())

    def test_shore_leave_restores_morale_for_credits(self):
        low_crew, _ = apply_morale_event(self.engine.state.ship.crew, -40.0, "test")
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(crew=low_crew))
        credits_before = self.engine.state.ship.credits
        morale_before = sum(m.morale for m in self.engine.state.ship.crew)

        ok, msg = self.engine.shore_leave()
        self.assertTrue(ok, msg)
        self.assertIn("morale", msg.lower())
        self.assertLess(self.engine.state.ship.credits, credits_before)
        self.assertGreater(sum(m.morale for m in self.engine.state.ship.crew), morale_before)
        self.assertTrue(any("SHORE LEAVE" in line for line in self.engine.state.ship.flight_log))

    def test_shore_leave_rejects_peak_morale(self):
        peak = tuple(
            m.__class__(**{**m.to_dict(), "morale": 100.0}) for m in self.engine.state.ship.crew
        )
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(crew=peak))
        ok, msg = self.engine.shore_leave()
        self.assertFalse(ok)
        self.assertIn("peak", msg.lower())

    def test_shore_leave_rejects_insufficient_credits(self):
        low_crew, _ = apply_morale_event(self.engine.state.ship.crew, -40.0, "test")
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(crew=low_crew, credits=10)
            )
        ok, msg = self.engine.shore_leave()
        self.assertFalse(ok)
        self.assertIn("Insufficient credits", msg)

    def test_cli_crew_shore_command(self):
        low_crew, _ = apply_morale_event(self.engine.state.ship.crew, -30.0, "test")
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(crew=low_crew))
        res = cmd_crew(self.engine, self.storage, ["crew", "shore"])
        self.assertEqual(res, 0)
        res = cmd_crew(self.engine, self.storage, ["crew"])
        self.assertEqual(res, 0)
        res = cmd_crew(self.engine, self.storage, ["crew", "list"])
        self.assertEqual(res, 0)

    def test_cli_main_crew_shore(self):
        import os

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"LOCALAPPDATA": tmp, "HOME": tmp, "USERPROFILE": tmp}
        ):
            self.assertEqual(main(["crew", "shore"]), 0)


class TestVolumeAwareMarket(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)
        station = [b for b in self.engine.current_system.bodies if b.station_dockable][0]
        ok, msg = self.engine.orbit(station.id)
        self.assertTrue(ok, msg)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(credits=100_000, cargo={}, cargo_capacity=500)
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _stock(self, commodity_id):
        return self.engine.state.economy.markets["sol"].stockpiles[commodity_id]

    def test_single_unit_keeps_flat_price(self):
        stock = self._stock("fuel_cells")
        ok, msg = self.engine.trade("fuel_cells", 1, is_buy=True)
        self.assertTrue(ok, msg)
        self.assertNotIn("market impact", msg)
        self.assertEqual(self._stock("fuel_cells"), max(5, stock - 1))

    def test_bulk_buy_pays_market_impact(self):
        from voidfarer.economy import calculate_dynamic_market_quote
        from voidfarer.galaxy import COMMODITY_MAP

        body = self.engine.orbiting_body
        initial = calculate_dynamic_market_quote(
            self.engine.current_system, body, COMMODITY_MAP["fuel_cells"], self.engine.state.economy
        ).buy_price
        stock = self._stock("fuel_cells")
        quantity = min(60, stock - 10)
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=True)
        self.assertTrue(ok, msg)
        self.assertIn("market impact", msg)
        # Total paid exceeds the flat initial quote for the whole order
        spent = credits_before - self.engine.state.ship.credits
        self.assertGreater(spent, initial * quantity)
        self.assertEqual(self._stock("fuel_cells"), max(5, stock - quantity))

    def test_bulk_sell_earns_diminishing_returns(self):
        quantity = 60
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=True)
        self.assertTrue(ok, msg)
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=False)
        self.assertTrue(ok, msg)
        self.assertIn("market impact", msg)
        self.assertIn("-", msg.split("market impact")[1])

    def test_buy_rejected_when_impact_exceeds_credits(self):
        stock = self._stock("fuel_cells")
        quantity = min(80, stock - 5)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(credits=quantity * 2, cargo={}, cargo_capacity=500)
            )
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=True)
        # The impact-adjusted total must exceed the naive flat cost estimate
        self.assertFalse(ok)
        self.assertIn("Insufficient credits", msg)

    def test_arbitrage_guard_still_blocks_same_station_round_trip(self):
        stock = self._stock("fuel_cells")
        quantity = min(30, stock - 10)
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=True)
        self.assertTrue(ok, msg)
        ok, msg = self.engine.trade("fuel_cells", quantity, is_buy=False)
        self.assertTrue(ok, msg)
        self.assertLess(self.engine.state.ship.credits, credits_before)


class TestCashFlowTelemetry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cash_flow_fields_and_math(self):
        flow = self.engine.cash_flow()
        self.assertEqual(flow["upkeep_per_month"], 65)
        self.assertGreaterEqual(flow["passive_per_month"], 0.0)
        self.assertAlmostEqual(flow["net_per_month"], round(flow["passive_per_month"] - 65, 1))

    def test_scout_drone_counts_as_passive_income(self):
        ok, msg = self.engine.buy_drone("scout")
        self.assertTrue(ok, msg)
        flow = self.engine.cash_flow()
        self.assertGreater(flow["passive_per_month"], 0.0)

    def test_snapshot_and_crew_report_expose_cash_flow(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("cash_flow", snapshot)
        report = self.engine.get_crew_report()
        self.assertIn("cash_flow", report)
        self.assertIn("morale_warnings", report)

    def test_cli_status_prints_cash_flow(self):
        res = cmd_status(self.engine)
        self.assertEqual(res, 0)


class TestServerCrewShoreEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = StorageManager(cls.temp_dir.name)
        cls.engine = SimulationEngine(seed=42)
        station = [b for b in cls.engine.current_system.bodies if b.station_dockable][0]
        cls.engine.orbit(station.id)

        VoidFarerHandler.engine = cls.engine
        VoidFarerHandler.storage = cls.storage
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"

        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def _post(self, path: str, body: dict):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        payload = json.dumps(body)
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def test_post_crew_shore(self):
        low_crew, _ = apply_morale_event(self.engine.state.ship.crew, -30.0, "test")
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(crew=low_crew))
        status, data = self._post("/api/crew/shore", {})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("cash_flow", payload["state"])


if __name__ == "__main__":
    unittest.main()

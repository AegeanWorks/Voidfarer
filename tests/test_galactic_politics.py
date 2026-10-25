"""Galactic politics: power-driven wars over hyperlane fronts, peace treaties and player war support."""

import io
import json
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import http.client

from voidfarer.cli import main
from voidfarer.engine import SimulationEngine
from voidfarer.faction_state import (
    WAR_CAPTURE_THRESHOLD,
    WAR_EXHAUSTION_TICKS,
    WAR_MOMENTUM,
    frontier_systems,
    generate_faction_leaders,
    resolve_wars,
    simulate_faction_behaviors,
    war_effort,
    war_momentum,
)
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import WarState
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class FixedRng:
    """Noise-free rng: uniform returns a fixed value, choice takes the first item."""

    def __init__(self, value=0.0):
        self.value = value

    def uniform(self, low, high):
        return self.value

    def choice(self, seq):
        return seq[0]


def _owner_ids(systems, name):
    return sorted(sid for sid, s in systems.items() if s.faction == name)


class TestWarFronts(unittest.TestCase):
    def setUp(self):
        self.systems = GalaxyGenerator(seed=42).generate_galaxy()

    def _war(self, **kwargs):
        base = dict(id="w1", attacker_id="sol_coalition", defender_id="nebula_collective", started_tick=0)
        base.update(kwargs)
        return WarState(**base)

    def test_frontier_is_loser_territory_adjacent_to_the_winner(self):
        front = frontier_systems("Sol Coalition", "Nebula Collective", self.systems)
        for sid in front:
            self.assertEqual(self.systems[sid].faction, "Nebula Collective")
            self.assertTrue(any(self.systems[n].faction == "Sol Coalition" for n in self.systems[sid].connections))

    def test_capture_takes_a_front_system_and_spends_the_score(self):
        front = frontier_systems("Sol Coalition", "Nebula Collective", self.systems)
        if not front:
            self.skipTest("seed 42 has no Sol/Nebula border")
        war = self._war(war_score=WAR_CAPTURE_THRESHOLD + 4)
        wars, systems, _, logs = resolve_wars((war,), self.systems, FixedRng(), 10, ())
        captured = wars[0].captured_systems
        self.assertEqual(len(captured), 1)
        self.assertIn(captured[0], front)
        self.assertEqual(systems[captured[0]].faction, "Sol Coalition")
        self.assertLess(abs(wars[0].war_score), WAR_CAPTURE_THRESHOLD)

    def test_no_front_means_no_capture(self):
        systems = dict(self.systems)
        sol = set(_owner_ids(systems, "Sol Coalition"))
        # Move every Nebula world that touches Sol space to a neutral third faction.
        for sid in frontier_systems("Sol Coalition", "Nebula Collective", systems):
            systems[sid] = replace(systems[sid], faction="Precursor Watch")
        if not _owner_ids(systems, "Nebula Collective") or frontier_systems("Sol Coalition", "Nebula Collective", systems):
            self.skipTest("cannot isolate Nebula space on this seed")
        war = self._war(war_score=WAR_CAPTURE_THRESHOLD + 4)
        wars, updated, _, _ = resolve_wars((war,), systems, FixedRng(), 10, ())
        self.assertEqual(wars[0].captured_systems, ())
        self.assertEqual(set(_owner_ids(updated, "Sol Coalition")), sol)

    def _assign(self, owners):
        systems = dict(self.systems)
        for sid, name in owners.items():
            systems[sid] = replace(systems[sid], faction=name)
        return systems

    def test_more_core_territory_means_more_war_effort(self):
        sol = _owner_ids(self.systems, "Sol Coalition")
        smaller = self._assign({sol[0]: "Void Corsairs"})
        self.assertGreater(war_effort("sol_coalition", self.systems), war_effort("sol_coalition", smaller))

    def test_overextension_caps_war_effort(self):
        others = [sid for sid, s in self.systems.items() if s.faction != "Sol Coalition"]
        empire = self._assign({sid: "Sol Coalition" for sid in others})
        self.assertLess(war_effort("sol_coalition", empire), 5 * war_effort("sol_coalition", self.systems))

    def test_a_hegemon_faces_containment(self):
        others = [sid for sid, s in self.systems.items() if s.faction not in ("Sol Coalition", "Nebula Collective")]
        hegemon = self._assign({sid: "Sol Coalition" for sid in others})
        self.assertLess(war_momentum("sol_coalition", "nebula_collective", hegemon), 0.0)

    def test_last_stand_bonus_does_not_empower_the_besieged_attacker(self):
        sol = _owner_ids(self.systems, "Sol Coalition")
        systems = self._assign({sid: "Precursor Watch" for sid in sol[1:]})
        attack = war_effort("sol_coalition", systems)
        defend = war_effort("nebula_collective", systems)
        expected = WAR_MOMENTUM * (attack - defend) / max(1.0, attack + defend)
        self.assertAlmostEqual(
            war_momentum("sol_coalition", "nebula_collective", systems), expected, places=6
        )

    def test_capital_needs_double_score(self):
        capital = "arcturus"  # Nebula Collective headquarters on every seed
        nebula = [sid for sid in _owner_ids(self.systems, "Nebula Collective") if sid != capital]
        systems = self._assign({sid: "Precursor Watch" for sid in nebula})
        for neighbour in systems[capital].connections:
            systems[neighbour] = replace(systems[neighbour], faction="Sol Coalition")
        held, _, _, _ = resolve_wars((self._war(war_score=WAR_CAPTURE_THRESHOLD + 4),), systems, FixedRng(), 10, ())
        self.assertEqual(held[0].captured_systems, ())
        taken, after, _, _ = resolve_wars((self._war(war_score=2 * WAR_CAPTURE_THRESHOLD + 8),), systems, FixedRng(), 10, ())
        self.assertEqual(taken[0].captured_systems, (capital,))
        self.assertEqual(after[capital].faction, "Sol Coalition")

    def test_the_capital_holds_while_the_defender_still_owns_other_worlds(self):
        capital = "arcturus"
        owners = {sid: "Precursor Watch" for sid in self.systems}
        owners.update({
            capital: "Nebula Collective",
            "vega": "Nebula Collective",
            "orion_belt": "Nebula Collective",
            "alpha_centauri": "Sol Coalition",
        })
        systems = self._assign(owners)
        self.assertEqual(frontier_systems("Sol Coalition", "Nebula Collective", systems), [capital])
        wars, _, _, _ = resolve_wars(
            (self._war(war_score=2 * WAR_CAPTURE_THRESHOLD + 8),), systems, FixedRng(), 10, ()
        )
        self.assertEqual(wars[0].captured_systems, ())

    def test_a_defending_faction_is_not_dogpiled(self):
        rng = FixedRng()
        rng.random = lambda: 0.0
        existing = self._war(attacker_id="outlaw_corsairs")
        wars, _, _, _ = simulate_faction_behaviors(
            generate_faction_leaders(42), (existing,), self.systems, rng, 5, ()
        )
        new = [w for w in wars if w.id != existing.id]
        self.assertTrue(all(w.defender_id != existing.defender_id for w in new))

    def test_exhaustion_ends_the_war_with_a_treaty(self):
        war = self._war(started_tick=0)
        wars, _, _, logs = resolve_wars((war,), self.systems, FixedRng(), WAR_EXHAUSTION_TICKS, ())
        self.assertFalse(wars[0].active)
        self.assertEqual(wars[0].ended_tick, WAR_EXHAUSTION_TICKS)
        self.assertTrue(any(line.startswith("PEACE:") for line in logs))

    def test_old_war_records_load_with_defaults(self):
        war = WarState.from_dict({"id": "w", "attacker_id": "a", "defender_id": "b", "started_tick": 3})
        self.assertEqual(war.captured_systems, ())
        self.assertIsNone(war.ended_tick)
        self.assertEqual(war.support, {})
        self.assertEqual(WarState.from_dict(war.to_dict()), war)


def _engine_at_war(credits=5000):
    engine = SimulationEngine(seed=42)
    war = WarState(id="w_test", attacker_id="sol_coalition", defender_id="nebula_collective", started_tick=0)
    engine.state = engine._clone_state(wars=(war,), ship=engine._clone_ship(credits=credits))
    return engine


class TestWarSupport(unittest.TestCase):
    def test_support_spends_credits_shifts_score_and_standing(self):
        engine = _engine_at_war()
        before = engine.state.ship.faction_standings.get("nebula_collective", 0)
        ok, msg = engine.support_war("w_test", "nebula_collective", 1200)
        self.assertTrue(ok, msg)
        self.assertEqual(engine.state.ship.credits, 5000 - 1200)
        war = engine.state.wars[0]
        self.assertLess(war.war_score, 0.0, "defender support pushes the score negative")
        self.assertEqual(war.support.get("nebula_collective"), 1200)
        self.assertGreater(engine.state.ship.faction_standings.get("nebula_collective", 0), before)
        self.assertLess(engine.state.ship.faction_standings.get("sol_coalition", 0), 0)

    def test_support_is_refused_when_it_cannot_apply(self):
        engine = _engine_at_war(credits=50)
        self.assertFalse(engine.support_war("w_test", "nebula_collective", 500)[0])
        self.assertFalse(engine.support_war("w_test", "void_corsairs", 100)[0])
        self.assertFalse(engine.support_war("missing", "sol_coalition", 100)[0])
        engine = _engine_at_war()
        self.assertFalse(engine.support_war("w_test", "sol_coalition", 10)[0], "below the minimum pledge")

    def test_snapshot_exposes_territory_and_fronts(self):
        engine = _engine_at_war()
        politics = engine.get_status_snapshot()["galactic_politics"]
        self.assertEqual(set(politics["systems"]), set(engine.state.systems))
        for info in politics["systems"].values():
            self.assertRegex(info["color"], r"^#[0-9a-fA-F]{6}$")
        war = politics["wars"][0]
        for a, b in war["fronts"]:
            self.assertIn(b, engine.state.systems[a].connections)
        self.assertTrue(any(f["id"] == "sol_coalition" for f in politics["factions"]))


class TestWarSupportParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = TemporaryDirectory()
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def test_rest_support(self):
        VoidFarerHandler.engine = _engine_at_war()
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        body = json.dumps({"war_id": "w_test", "faction_id": "sol_coalition", "credits": 800})
        conn.request("POST", "/api/war/support", body=body, headers={"Content-Type": "application/json"})
        payload = json.loads(conn.getresponse().read())
        conn.close()
        self.assertTrue(payload["ok"], payload["message"])
        self.assertEqual(payload["state"]["ship"]["credits"], 5000 - 800)

    def test_cli_war_list_and_support(self):
        with TemporaryDirectory() as home:
            with patch.dict("os.environ", {"LOCALAPPDATA": home, "HOME": home, "USERPROFILE": home}):
                StorageManager(Path(home) / ".voidfarer").save(_engine_at_war().state)
                with patch("sys.stdout", new_callable=io.StringIO) as out:
                    self.assertEqual(main(["war", "list"]), 0)
                    self.assertEqual(main(["war", "support", "w_test", "sol_coalition", "600"]), 0)
                self.assertIn("w_test", out.getvalue())
                self.assertEqual(StorageManager(Path(home) / ".voidfarer").load().ship.credits, 5000 - 600)


if __name__ == "__main__":
    unittest.main()

"""Loading a save must not rewrite live universe state (ADR-406)."""

from __future__ import annotations

import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.models import TradeLink
from voidfarer.storage import StorageManager


def _drive(engine: SimulationEngine, actions: int) -> None:
    """A deterministic hop-and-scan tour that lets the tick advance trade links."""
    for index in range(actions):
        connections = engine.current_system.connections
        if connections:
            engine.jump(connections[index % len(connections)])
        body = engine.current_system.bodies[index % len(engine.current_system.bodies)]
        engine.orbit(body.id)
        engine.scan()
        engine.tick(3)


class LegacyWorldMigrationTest(unittest.TestCase):
    """Only a genuinely pre-demographics world is backfilled on load (ADR-407)."""

    def _system_with(self, body_kwargs, faction="Precursor Watch"):
        engine = SimulationEngine(seed=1)
        system = engine.current_system
        body = system.bodies[0]
        body = replace(body, **body_kwargs)
        system = replace(system, faction=faction, bodies=(body,) + tuple(system.bodies[1:]))
        engine.state = engine._clone_state(
            systems={**engine.state.systems, system.id: system},
            ship=engine._clone_ship(current_system_id=system.id, orbiting_body_id=""),
        )
        return engine, body.id

    def test_a_conquered_gas_giant_keeps_its_unclaimed_flag_on_load(self):
        engine, body_id = self._system_with({
            "body_type": "ringed_giant", "population": 0, "population_capacity": 0,
            "tech_level": 9, "market_archetype": "industrial", "landable": True,
            "faction": "Unclaimed", "devastation": 0.0,
        })
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            reloaded = SimulationEngine(state=StorageManager(temp_dir).load())
        body = next(b for b in reloaded.state.systems[engine.current_system.id].bodies
                    if b.id == body_id)
        self.assertEqual(body.faction, "Unclaimed")
        self.assertEqual(body.population, 0)

    def test_a_real_legacy_world_is_still_seeded(self):
        engine, body_id = self._system_with({
            "body_type": "terrestrial", "population": 0, "population_capacity": 0,
            "tech_level": 1, "market_archetype": "none", "landable": True,
            "faction": "Unclaimed", "devastation": 0.0, "government": "None",
        })
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            reloaded = SimulationEngine(state=StorageManager(temp_dir).load())
        body = next(b for b in reloaded.state.systems[engine.current_system.id].bodies
                    if b.id == body_id)
        self.assertGreater(body.population_capacity, 0)
        self.assertEqual(body.faction, "Precursor Watch")


class EmptyCollectionsStayEmptyTest(unittest.TestCase):
    """A modern save keeps a deliberately empty crew, weapons or inbox (ADR-415)."""

    def _save_and_reload(self, engine: SimulationEngine) -> SimulationEngine:
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            return SimulationEngine(state=StorageManager(temp_dir).load())

    def test_an_empty_crew_stays_empty(self):
        engine = SimulationEngine(seed=5)
        engine.state = engine._clone_state(ship=engine._clone_ship(crew=()))
        self.assertTrue(engine.state.rng_state)
        reloaded = self._save_and_reload(engine)
        self.assertEqual(reloaded.state.ship.crew, ())

    def test_an_empty_weapon_loadout_stays_empty(self):
        engine = SimulationEngine(seed=5)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(weapons=(), primary_weapon="")
        )
        reloaded = self._save_and_reload(engine)
        self.assertEqual(reloaded.state.ship.weapons, ())
        self.assertEqual(reloaded.state.ship.primary_weapon, "")

    def test_an_empty_inbox_stays_empty(self):
        engine = SimulationEngine(seed=5)
        engine.state = engine._clone_state(messages=())
        reloaded = self._save_and_reload(engine)
        self.assertEqual(reloaded.state.messages, ())

    def test_a_legacy_save_still_receives_the_starter_crew(self):
        engine = SimulationEngine(seed=5)
        payload = engine.state.to_dict()
        payload["rng_state"] = None
        payload["ship"]["crew"] = []
        legacy = type(engine.state).from_dict(payload)
        reloaded = SimulationEngine(state=legacy)
        roles = [member.role for member in reloaded.state.ship.crew]
        self.assertEqual(roles, ["engineer", "pilot"])

    def test_a_legacy_save_with_messages_still_gets_a_tree_root(self):
        engine = SimulationEngine(seed=5)
        payload = engine.state.to_dict()
        payload["rng_state"] = None
        legacy = type(engine.state).from_dict(payload)
        reloaded = SimulationEngine(state=legacy)
        self.assertTrue(any(message.tree_id for message in reloaded.state.messages))


class LoadPreservesLiveStateTest(unittest.TestCase):
    def test_loading_keeps_the_live_trade_link_volumes(self):
        engine = SimulationEngine(seed=11)
        _drive(engine, 6)
        before = tuple(engine.state.trade_links)
        self.assertTrue(before)

        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            reloaded = SimulationEngine(state=StorageManager(temp_dir).load())

        self.assertEqual(tuple(reloaded.state.trade_links), before)

    def test_a_legacy_save_without_trade_links_still_gets_them(self):
        engine = SimulationEngine(seed=11)
        payload = engine.state.to_dict()
        payload["trade_links"] = []
        legacy = type(engine.state).from_dict(payload)
        reloaded = SimulationEngine(state=legacy)
        self.assertTrue(reloaded.state.trade_links)

    def test_a_rebuilt_engine_matches_the_saved_state(self):
        engine = SimulationEngine(seed=11)
        _drive(engine, 6)
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            reloaded = SimulationEngine(state=StorageManager(temp_dir).load())
        self.assertEqual(reloaded.state.trade_links, engine.state.trade_links)

    def test_the_computed_links_still_replace_an_empty_route_table(self):
        engine = SimulationEngine(seed=11)
        engine.state = engine._clone_state(trade_links=())
        engine._bootstrap_frontier()
        self.assertTrue(engine.state.trade_links)
        self.assertTrue(all(isinstance(link, TradeLink) for link in engine.state.trade_links))


if __name__ == "__main__":
    unittest.main()

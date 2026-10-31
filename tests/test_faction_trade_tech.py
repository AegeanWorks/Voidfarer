"""Faction trade links and technology drift across the simulation."""

import unittest

from voidfarer.demographics import MAX_TECH_LEVEL, TECH_PROGRESS_PER_LEVEL
from voidfarer.engine import SimulationEngine
from voidfarer.faction_economy import compute_faction_economy
from voidfarer.faction_trade import (
    compute_trade_links,
    trade_income_for,
    trade_partner_names,
    trade_partners_for,
    warring_pairs,
)
from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import FactionEconomy, GameState, TradeLink, WarState


def _pair(link: TradeLink) -> frozenset[str]:
    return frozenset((link.faction_a, link.faction_b))


class TestTradeLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.systems = GalaxyGenerator(seed=42).generate_galaxy()
        cls.links = compute_trade_links(cls.systems)

    def test_peaceful_neighbours_trade(self):
        self.assertTrue(self.links)
        for link in self.links:
            self.assertLess(link.faction_a, link.faction_b)
            self.assertGreater(link.volume, 0)

    def test_every_link_crosses_a_hyperlane_between_the_two_owners(self):
        for link in self.links:
            left = CANONICAL_FACTIONS[link.faction_a].name
            right = CANONICAL_FACTIONS[link.faction_b].name
            crosses = any(
                systems_neighbour.faction == right
                for system in self.systems.values()
                if system.faction == left
                for systems_neighbour in (
                    self.systems[n] for n in system.connections if n in self.systems
                )
            )
            self.assertTrue(crosses, link)

    def test_war_severs_the_route(self):
        link = self.links[0]
        war = WarState(
            id="w_trade",
            attacker_id=link.faction_a,
            defender_id=link.faction_b,
            started_tick=0,
        )
        severed = compute_trade_links(self.systems, (war,))
        self.assertNotIn(_pair(link), {_pair(other) for other in severed})
        self.assertIn(_pair(link), warring_pairs((war,)))

    def test_each_faction_keeps_at_most_three_partners(self):
        for faction_id in CANONICAL_FACTIONS:
            self.assertLessEqual(trade_partners_for(faction_id, self.links), 3)

    def test_route_pays_half_its_volume_to_each_endpoint(self):
        link = self.links[0]
        self.assertEqual(trade_income_for(link.faction_a, (link,)), link.volume // 2)
        self.assertEqual(trade_income_for(link.faction_b, (link,)), link.volume // 2)

    def test_partner_names_are_canonical_names(self):
        link = self.links[0]
        names = trade_partner_names(link.faction_a, (link,))
        self.assertEqual(names, [CANONICAL_FACTIONS[link.faction_b].name])

    def test_trade_links_round_trip_in_a_save(self):
        engine = SimulationEngine(seed=42)
        data = engine.state.to_dict()
        restored = GameState.from_dict(data)
        self.assertEqual(restored.trade_links, engine.state.trade_links)


class TestTechnologyDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.systems = GalaxyGenerator(seed=42).generate_galaxy()

    def test_research_accumulates_into_a_new_tech_level(self):
        report = compute_faction_economy(
            "sol_coalition",
            self.systems,
            tech_level=5,
            tech_progress=TECH_PROGRESS_PER_LEVEL - 0.01,
        )
        self.assertEqual(report.tech_level, 6)
        self.assertLess(report.tech_progress, TECH_PROGRESS_PER_LEVEL)

    def test_tech_never_exceeds_the_cap(self):
        report = compute_faction_economy(
            "sol_coalition",
            self.systems,
            tech_level=MAX_TECH_LEVEL,
            tech_progress=99.0,
            num_ticks=10_000,
        )
        self.assertEqual(report.tech_level, MAX_TECH_LEVEL)
        self.assertLessEqual(report.tech_progress, TECH_PROGRESS_PER_LEVEL - 0.1)

    def test_economy_carries_trade_partners_and_income(self):
        engine = SimulationEngine(seed=42)
        economy = next(e for e in engine.state.faction_economies if e.faction_id == "sol_coalition")
        self.assertGreater(economy.trade_income, 0)
        self.assertGreater(economy.trade_partners, 0)

        partner = next(
            (t for t in engine.state.trade_links if "sol_coalition" in (t.faction_a, t.faction_b)),
            None,
        )
        self.assertIsNotNone(partner)
        war = WarState(
            id="w_cut",
            attacker_id=partner.faction_a,
            defender_id=partner.faction_b,
            started_tick=0,
        )
        cut = compute_faction_economy(
            "sol_coalition",
            engine.state.systems,
            (war,),
            trade_links=engine.state.trade_links,
            tech_level=economy.tech_level,
        )
        # The route no longer exists, so partner income drops for the involved faction.
        self.assertLessEqual(cut.trade_income, economy.trade_income)

    def test_worlds_drift_up_and_capacity_follows(self):
        engine = SimulationEngine(seed=42)
        before = {
            body.id: (body.tech_level, body.population_capacity)
            for system in engine.state.systems.values()
            for body in system.bodies
            if body.population > 0
        }
        engine.tick(6000)
        upgraded = 0
        for system in engine.state.systems.values():
            for body in system.bodies:
                if body.id not in before:
                    continue
                old_tech, old_capacity = before[body.id]
                if body.tech_level > old_tech:
                    upgraded += 1
                    self.assertGreaterEqual(body.population_capacity, old_capacity)
        self.assertGreater(upgraded, 0)

    def test_faction_tech_levels_advance_over_time(self):
        engine = SimulationEngine(seed=42)
        before = {e.faction_id: e.tech_level for e in engine.state.faction_economies}
        engine.tick(12000)
        advanced = [
            e.faction_id
            for e in engine.state.faction_economies
            if e.tech_level > before.get(e.faction_id, 1)
        ]
        self.assertTrue(advanced)


if __name__ == "__main__":
    unittest.main()

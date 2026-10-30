"""Outpost supply links: same-system hubs, rules, bonuses and persistence."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import Outpost
from voidfarer.outposts import (
    OUTPOST_SUPPLY_HUB_BONUS,
    OUTPOST_SUPPLY_LINK_BONUS,
    outpost_supply_multiplier,
    outpost_tick_production,
)


def _outpost(outpost_id: str, system_id: str = "sol", **kwargs) -> Outpost:
    return Outpost(
        id=outpost_id,
        name=outpost_id.replace("_", " ").title(),
        system_id=system_id,
        body_id=f"{system_id}_body_1",
        **kwargs,
    )


class OutpostSupplyTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.a = _outpost("supply_a")
        self.b = _outpost("supply_b")
        self.c = _outpost("supply_c")
        self.remote = _outpost("supply_remote", system_id="alpha_centauri")
        self.engine.state = self.engine._clone_state(
            outposts=(self.a, self.b, self.c, self.remote)
        )

    def test_valid_link_sets_the_hub_and_bonuses(self):
        ok, message = self.engine.link_outpost_supply(self.a.id, self.b.id)
        self.assertTrue(ok, message)
        linked = self.engine.state.outposts[0]
        self.assertEqual(linked.supply_hub_id, self.b.id)
        report = {
            outpost["id"]: outpost for outpost in self.engine.get_outpost_report()["outposts"]
        }
        self.assertEqual(report[self.a.id]["supply_hub_name"], self.b.name)
        self.assertAlmostEqual(report[self.a.id]["supply_multiplier"], 1.05)
        self.assertEqual(report[self.b.id]["supply_link_count"], 1)
        self.assertAlmostEqual(report[self.b.id]["supply_multiplier"], 1.08)

    def test_link_rejects_self_remote_and_existing_links(self):
        ok, message = self.engine.link_outpost_supply(self.a.id, self.a.id)
        self.assertFalse(ok)
        self.assertIn("itself", message.lower())

        ok, message = self.engine.link_outpost_supply(self.a.id, self.remote.id)
        self.assertFalse(ok)
        self.assertIn("one star system", message.lower())

        self.assertTrue(self.engine.link_outpost_supply(self.a.id, self.b.id)[0])
        ok, message = self.engine.link_outpost_supply(self.a.id, self.c.id)
        self.assertFalse(ok)
        self.assertIn("already supplies", message.lower())

    def test_hub_capacity_and_no_upward_chain(self):
        self.assertTrue(self.engine.link_outpost_supply(self.a.id, self.b.id)[0])
        self.assertTrue(self.engine.link_outpost_supply(self.c.id, self.b.id)[0])
        ok, message = self.engine.link_outpost_supply(self.remote.id, self.b.id)
        self.assertFalse(ok)
        self.assertIn("one star system", message.lower())

        extra = _outpost("supply_extra")
        extra2 = _outpost("supply_extra2")
        self.engine.state = self.engine._clone_state(
            outposts=tuple(self.engine.state.outposts) + (extra, extra2)
        )
        ok, message = self.engine.link_outpost_supply(extra.id, self.b.id)
        self.assertFalse(ok)
        self.assertIn("already hosts", message.lower())

        ok, message = self.engine.link_outpost_supply(self.b.id, extra2.id)
        self.assertFalse(ok)
        self.assertIn("hosts its own", message.lower())

    def test_unlink_clears_the_hub(self):
        self.assertTrue(self.engine.link_outpost_supply(self.a.id, self.b.id)[0])
        ok, message = self.engine.unlink_outpost_supply(self.a.id)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.outposts[0].supply_hub_id, "")
        self.assertFalse(self.engine.unlink_outpost_supply(self.a.id)[0])

    def test_supply_multiplier_math_and_tick_production(self):
        outposts = (self.a, self.b, self.c)
        linked = self.a
        self.assertEqual(outpost_supply_multiplier(linked, outposts), 1.0)
        linked = Outpost.from_dict({**self.a.to_dict(), "supply_hub_id": self.b.id})
        self.assertAlmostEqual(
            outpost_supply_multiplier(linked, outposts),
            1.0 + OUTPOST_SUPPLY_LINK_BONUS,
        )
        hub = Outpost.from_dict({**self.b.to_dict()})
        outposts = (
            linked,
            hub,
            Outpost.from_dict({**self.c.to_dict(), "supply_hub_id": self.b.id}),
        )
        self.assertAlmostEqual(
            outpost_supply_multiplier(hub, outposts),
            1.0 + OUTPOST_SUPPLY_HUB_BONUS * 2,
        )
        base = outpost_tick_production(linked, 1.0, 1.0, 1.0)["credits"]
        boosted = outpost_tick_production(linked, 1.0, 1.0, 1.05)["credits"]
        self.assertGreater(boosted, base)

    def test_persistence_and_legacy_default(self):
        self.assertTrue(self.engine.link_outpost_supply(self.a.id, self.b.id)[0])
        restored = Outpost.from_dict(self.engine.state.to_dict()["outposts"][0])
        self.assertEqual(restored.supply_hub_id, self.b.id)
        payload = self.a.to_dict()
        payload.pop("supply_hub_id", None)
        self.assertEqual(Outpost.from_dict(payload).supply_hub_id, "")


if __name__ == "__main__":
    unittest.main()

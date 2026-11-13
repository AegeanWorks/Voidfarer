"""The headless AI captain exercises the fuel-cell burn, so the mechanics gate covers it."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class TestAiBurnCells(unittest.TestCase):
    def test_a_played_game_burns_a_cell_through_the_engineering_action(self) -> None:
        with tempfile.TemporaryDirectory() as save_dir:
            engine = SimulationEngine(seed=42)
            engine.allow_decision_events = True
            VoidFarerHandler.engine = engine
            VoidFarerHandler.storage = StorageManager(save_dir)
            VoidFarerHandler.static_dir = STATIC
            server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                report = AiCaptain(ApiClient(port=server.server_port), seed=42).play(steps=200)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2.0)
        self.assertEqual(report["errors"], [])
        self.assertIn("burn_cells", report["families"], report["families"])
        self.assertEqual(report["coverage_gaps"], [])


if __name__ == "__main__":
    unittest.main()

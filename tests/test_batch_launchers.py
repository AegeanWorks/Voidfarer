"""Regression tests for the Windows batch launchers (``play.bat``, ``voidfarer.bat``).

Users launch VoidFarer by double-clicking these scripts from Explorer, so the files
must keep CRLF line endings and the interactive menu must render without cmd parse
errors and exit cleanly. Regression: unescaped ``|`` characters in the ASCII banner
made cmd pipe the echo into a nonexistent command and abort the script with exit
code 255 before any menu appeared (double-click looked like "nothing happens").
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAY_BAT = PROJECT_ROOT / "play.bat"
CLI_BAT = PROJECT_ROOT / "voidfarer.bat"


class TestLauncherLineEndings(unittest.TestCase):
    """cmd.exe parses CRLF batches reliably; lone LF endings can abort a script mid-file."""

    def _assert_crlf(self, path: Path) -> None:
        data = path.read_bytes()
        lone_lf = data.replace(b"\r\n", b"").count(b"\n")
        self.assertEqual(
            lone_lf, 0, f"{path.name} contains {lone_lf} lone LF line ending(s); batch files need CRLF"
        )

    def test_play_bat_uses_crlf_line_endings(self):
        self._assert_crlf(PLAY_BAT)

    def test_voidfarer_bat_uses_crlf_line_endings(self):
        self._assert_crlf(CLI_BAT)


@unittest.skipUnless(sys.platform == "win32" and shutil.which("cmd"), "Windows cmd.exe required")
class TestLauncherMenu(unittest.TestCase):
    """The interactive mission menu must survive its ASCII banner and exit cleanly."""

    def test_menu_choice_zero_renders_and_exits_cleanly(self):
        result = subprocess.run(
            ["cmd.exe", "/c", str(PLAY_BAT)],
            input="0\r\n",
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"launcher exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("Select mission mode", result.stdout)

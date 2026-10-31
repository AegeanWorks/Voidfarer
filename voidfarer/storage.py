"""Crash-resilient storage engine and atomic persistence for VoidFarer."""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from voidfarer.models import GameState

_SLOT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class StorageManager:
    """Manages power-loss safe atomic persistence and shadow backups."""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.save_file = self.data_dir / "voidfarer_save.json"
        self._write_lock = threading.Lock()

    def _write_atomic(self, target_path: Path, data: dict[str, Any]) -> Path:
        """Write JSON payload atomically using a unique temporary file, fsync, and shadow backup."""
        with self._write_lock:
            # Check free disk space (> 10MB)
            if hasattr(shutil, "disk_usage"):
                stat = shutil.disk_usage(self.data_dir)
                if stat.free < 10 * 1024 * 1024:
                    raise OSError("Insufficient disk space (< 10MB free)")

            token = uuid.uuid4().hex
            temp_path = self.data_dir / f".tmp_{target_path.name}_{token}"
            backup_path = target_path.with_suffix(".bak")

            payload = json.dumps(data, indent=2)
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

            if target_path.exists():
                backup_temp = self.data_dir / f".tmp_{backup_path.name}_{token}"
                try:
                    shutil.copy2(target_path, backup_temp)
                    with open(backup_temp, "rb+") as bf:
                        os.fsync(bf.fileno())
                    os.replace(backup_temp, backup_path)
                except OSError:
                    backup_temp.unlink(missing_ok=True)

            last_error: OSError | None = None
            for _ in range(5):
                try:
                    os.replace(temp_path, target_path)
                    break
                except OSError as exc:
                    last_error = exc
                    time.sleep(0.02)
            else:
                temp_path.unlink(missing_ok=True)
                raise OSError(f"Atomic save failed for {target_path}") from last_error

            return target_path

    def _read_json_file(self, target_path: Path) -> dict[str, Any] | None:
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return None

    def _quarantine(self, target_path: Path) -> None:
        if not target_path.exists():
            return
        corrupt_path = self.data_dir / f"{target_path.name}.corrupt_{int(time.time())}"
        try:
            shutil.move(target_path, corrupt_path)
        except OSError:
            target_path.unlink(missing_ok=True)

    def _slot_path(self, slot: str | None = None) -> tuple[str, Path]:
        normalized = resolve_slot_name(slot)
        if normalized == "default":
            return "default", self.save_file
        return normalized, self.data_dir / f"voidfarer_save_{normalized}.json"

    def save(self, state: GameState, slot: str | None = None) -> Path:
        """Atomically persist universe and ship state into the requested save slot."""
        _, target_path = self._slot_path(slot)
        return self._write_atomic(target_path, state.to_dict())

    def load(self, slot: str | None = None) -> GameState | None:
        """Load game state from disk for the given slot, quarantining corrupt primary data and trying the backup."""
        _, primary = self._slot_path(slot)
        data = self._read_json_file(primary)
        if data is None:
            if primary.exists():
                self._quarantine(primary)
        else:
            try:
                return GameState.from_dict(data)
            except (KeyError, TypeError, ValueError, AttributeError):
                self._quarantine(primary)

        backup_data = self._read_json_file(primary.with_suffix(".bak"))
        if backup_data is None:
            return None
        try:
            return GameState.from_dict(backup_data)
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    def clear(self, slot: str | None = None) -> bool:
        """Remove save file and shadow backup for the given slot."""
        _, target_path = self._slot_path(slot)
        backup_path = target_path.with_suffix(".bak")
        existed = target_path.exists() or backup_path.exists()
        target_path.unlink(missing_ok=True)
        backup_path.unlink(missing_ok=True)
        return existed

    def delete_save(self, slot: str | None = None) -> bool:
        """Delete a save slot and its shadow backup."""
        return self.clear(slot=slot)

    def list_saves(self) -> list[dict[str, Any]]:
        """List all available save slots with summary metadata."""
        candidates: list[tuple[str, Path]] = []
        if self.save_file.exists() or self.save_file.with_suffix(".bak").exists():
            candidates.append(("default", self.save_file))

        for path in sorted(self.data_dir.glob("voidfarer_save_*.json")):
            stem_suffix = path.stem[len("voidfarer_save_"):]
            if _SLOT_NAME_RE.match(stem_suffix) and stem_suffix != "default":
                candidates.append((stem_suffix, path))

        summaries: list[dict[str, Any]] = []
        for slot_name, path in candidates:
            data = self._read_json_file(path)
            if data is None:
                data = self._read_json_file(path.with_suffix(".bak"))
            if not isinstance(data, dict):
                continue
            summaries.append(_extract_save_summary(slot_name, path, data))
        return summaries


def resolve_slot_name(slot: str | None = None) -> str:
    """Validate and normalize a save slot identifier."""
    if slot is None:
        return "default"
    if not isinstance(slot, str):
        raise ValueError("Save slot must be a string.")
    cleaned = slot.strip()
    if cleaned in ("", "default"):
        return "default"
    if not _SLOT_NAME_RE.match(cleaned):
        raise ValueError(
            f"Invalid save slot '{slot}'. Why: slot names must be 1-40 ASCII letters, digits, '_' or '-'. "
            "Fix: choose a safe slot name such as 'slot_1' or 'alpha'."
        )
    return cleaned


def _extract_save_summary(slot_name: str, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Build a compact metadata dictionary for a save slot."""
    ship = data.get("ship") if isinstance(data.get("ship"), dict) else {}
    time_data = data.get("time") if isinstance(data.get("time"), dict) else {}
    ticks = int(time_data.get("tick", time_data.get("ticks", 0)) or 0)
    date_str = str(time_data.get("date") or "01.01.3042")
    try:
        mtime = int(path.stat().st_mtime)
    except OSError:
        mtime = 0
    return {
        "slot": slot_name,
        "filename": path.name,
        "commander_name": str(ship.get("commander_name", "Astraea")),
        "callsign": str(ship.get("callsign", "VF-01")),
        "ship_class": str(ship.get("ship_class", "Vanguard Scout")),
        "current_system_id": str(ship.get("current_system_id", "sol")),
        "credits": int(ship.get("credits", 0) or 0),
        "tick": ticks,
        "stardate": date_str,
        "updated_at": mtime,
    }

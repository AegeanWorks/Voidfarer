"""Branching quantum message trees and their consequences."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from voidfarer.models import MessageChoice, QuantumMessage


@dataclass(frozen=True)
class MessageNode:
    id: str
    sender: str
    subject: str
    body: str
    choices: tuple[MessageChoice, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MessageTree:
    id: str
    name: str
    nodes: dict[str, MessageNode]
    root: str = "root"

    def node(self, node_id: str) -> MessageNode | None:
        return self.nodes.get(node_id)


TREES: dict[str, MessageTree] = {
    "precursor_signal": MessageTree(
        id="precursor_signal",
        name="Precursor Signal",
        nodes={
            "root": MessageNode(
                id="root",
                sender="Cipher // Precursor Watch",
                subject="A signal beneath the noise",
                body=(
                    "Commander, a carrier wave is repeating beneath the quantum noise. "
                    "It predates every known civilization by eleven thousand years. "
                    "We can decode it, sell the coordinates, or answer it directly."
                ),
                choices=(
                    MessageChoice(
                        id="decode",
                        label="Decode the signal",
                        description="Scientific approach: gain research data and a stable quantum key.",
                        outcome={"research": 60, "quantum_key": 1, "standing_faction": "precursor_watch", "standing_delta": 6},
                        next_node_id="decoded",
                    ),
                    MessageChoice(
                        id="sell",
                        label="Sell coordinates to the Syndicate",
                        description="Commercial approach: immediate credits, but Watch standing suffers.",
                        outcome={"credits": 900, "standing_faction": "precursor_watch", "standing_delta": -8, "standing_other": "vanguard_syndicate", "standing_other_delta": 6},
                        next_node_id="sold",
                    ),
                    MessageChoice(
                        id="answer",
                        label="Answer the signal",
                        description="Risky approach: reactor surge and a possible weapon unlock.",
                        outcome={"hull": -12, "heat": 18, "unlock_weapon": "quantum_lance", "research": 30},
                        next_node_id="answered",
                    ),
                ),
            ),
            "decoded": MessageNode(
                id="decoded",
                sender="Cipher // Precursor Watch",
                subject="Decryption complete",
                body="The signal contains a gravitational map and a dormant quantum lattice. Your science team is already integrating it.",
                choices=(
                    MessageChoice(
                        id="install_lattice",
                        label="Install the lattice in the reactor",
                        description="Permanent reactor output at the cost of heat capacity.",
                        outcome={"reactor_output": 0.12, "heat_capacity": -8, "research": 25},
                    ),
                    MessageChoice(
                        id="archive_lattice",
                        label="Archive the lattice for later study",
                        description="Research points and a safer reactor.",
                        outcome={"research": 70, "cooling": 3},
                    ),
                ),
            ),
            "sold": MessageNode(
                id="sold",
                sender="Director Sable // Free Spacers Syndicate",
                subject="Coordinates received",
                body="A clean transaction, Commander. The Syndicate remembers friends. Try not to let the Watch trace this back to you.",
                choices=(
                    MessageChoice(
                        id="take_bonus",
                        label="Take the bonus contract",
                        description="Extra credits and Syndicate standing.",
                        outcome={"credits": 450, "standing_other": "vanguard_syndicate", "standing_other_delta": 8},
                    ),
                    MessageChoice(
                        id="refuse_bonus",
                        label="Refuse and keep clean",
                        description="Small Watch standing recovery.",
                        outcome={"standing_faction": "precursor_watch", "standing_delta": 3},
                    ),
                ),
            ),
            "answered": MessageNode(
                id="answered",
                sender="Unknown // Signal Echo",
                subject="WE HEAR YOU",
                body="The response is not language. It is a weapon schematic written in gravitational pulses. Your reactor is still recovering.",
                choices=(
                    MessageChoice(
                        id="stabilize",
                        label="Stabilize the reactor",
                        description="Repair hull and reduce heat.",
                        outcome={"hull": 15, "heat": -30, "research": 20},
                    ),
                ),
            ),
        },
    ),
    "quantum_offer": MessageTree(
        id="quantum_offer",
        name="Quantum Research Compact",
        nodes={
            "root": MessageNode(
                id="root",
                sender="Archon Ilsa // Nebula Collective",
                subject="A shared quantum future",
                body=(
                    "The Collective proposes a joint quantum-research compact. We offer laboratory access "
                    "in exchange for convoy protection and a share of any discoveries."
                ),
                choices=(
                    MessageChoice(
                        id="accept",
                        label="Accept the compact",
                        description="Research points and Collective standing.",
                        outcome={"research": 120, "standing_faction": "nebula_collective", "standing_delta": 10, "quantum_key": 1},
                        next_node_id="accepted",
                    ),
                    MessageChoice(
                        id="negotiate",
                        label="Negotiate harder",
                        description="More research if your diplomacy skill is sufficient.",
                        outcome={"research": 80, "standing_faction": "nebula_collective", "standing_delta": 4},
                        next_node_id="accepted",
                    ),
                    MessageChoice(
                        id="decline",
                        label="Decline politely",
                        description="Keep independence; small standing loss.",
                        outcome={"standing_faction": "nebula_collective", "standing_delta": -4},
                    ),
                ),
            ),
            "accepted": MessageNode(
                id="accepted",
                sender="Archon Ilsa // Nebula Collective",
                subject="Compact ratified",
                body="The first shared experiment is ready. Choose the branch your fleet needs most.",
                choices=(
                    MessageChoice(
                        id="weapons_branch",
                        label="Weapons branch: quantum lance",
                        description="Unlock a quantum weapon and gain combat research.",
                        outcome={"unlock_weapon": "quantum_lance", "research": 30},
                    ),
                    MessageChoice(
                        id="drive_branch",
                        label="Drive branch: quantum efficiency",
                        description="Improve fuel efficiency and gain quantum keys.",
                        outcome={"fuel_efficiency": 0.12, "quantum_key": 2},
                    ),
                    MessageChoice(
                        id="shield_branch",
                        label="Shield branch: entangled deflectors",
                        description="Improved shield cap and reactor cooling.",
                        outcome={"max_shield": 25, "cooling": 4},
                    ),
                ),
            ),
        },
    ),
    "refugee_fleet": MessageTree(
        id="refugee_fleet",
        name="Refugee Flotilla",
        nodes={
            "root": MessageNode(
                id="root",
                sender="Envoy Tessa // Independent Flotilla",
                subject="Request for asylum",
                body=(
                    "Three hundred thousand refugees are fleeing a faction war. They request berths, "
                    "medical support, and a place in your fleet."
                ),
                choices=(
                    MessageChoice(
                        id="accept_crew",
                        label="Accept trained crew",
                        description="Recruit a specialist and gain diplomatic standing.",
                        outcome={"crew_role": "engineer", "credits": -150, "standing_faction": "sol_coalition", "standing_delta": 5},
                    ),
                    MessageChoice(
                        id="accept_cargo",
                        label="Accept their industrial cargo",
                        description="Gain cargo and credits, but lose some standing.",
                        outcome={"cargo": "medicines", "cargo_qty": 6, "credits": 120, "standing_other": "outlaw_corsairs", "standing_other_delta": 3},
                    ),
                    MessageChoice(
                        id="turn_away",
                        label="Turn the flotilla away",
                        description="Keep resources, lose standing.",
                        outcome={"standing_faction": "sol_coalition", "standing_delta": -10},
                    ),
                ),
            ),
        },
    ),
}

TREE_MAP: dict[str, MessageTree] = TREES


def tree_root_message(tree_id: str, tick: int, message_id: str | None = None) -> QuantumMessage | None:
    tree = TREE_MAP.get(tree_id)
    if not tree:
        return None
    node = tree.node(tree.root)
    if not node:
        return None
    return QuantumMessage(
        id=message_id or f"tree_{tree_id}_{tick}",
        sender=node.sender,
        recipient="Commander",
        subject=node.subject,
        body=node.body,
        tick=tick,
        tree_id=tree.id,
        node_id=node.id,
        choices=node.choices,
    )


def follow_up_message(tree_id: str, node_id: str, tick: int, parent_id: str) -> QuantumMessage | None:
    tree = TREE_MAP.get(tree_id)
    if not tree:
        return None
    node = tree.node(node_id)
    if not node:
        return None
    return QuantumMessage(
        id=f"{parent_id}_{node_id}",
        sender=node.sender,
        recipient="Commander",
        subject=node.subject,
        body=node.body,
        tick=tick,
        tree_id=tree.id,
        node_id=node.id,
        choices=node.choices,
    )


def choice_by_id(message: QuantumMessage, choice_id: str) -> MessageChoice | None:
    return next((c for c in message.choices if c.id == choice_id), None)


def tree_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": tree.id,
            "name": tree.name,
            "root": tree.root,
            "nodes": [
                {
                    "id": node.id,
                    "sender": node.sender,
                    "subject": node.subject,
                    "body": node.body,
                    "choices": [choice.to_dict() for choice in node.choices],
                }
                for node in tree.nodes.values()
            ],
        }
        for tree in TREES.values()
    ]

"""Tokenized mining simulation.

For each tick: sum the hashrate contribution of all RUNNING mining
workloads, mix in a slowly-drifting difficulty, and decide whether to emit
a 'block'. Block emission uses a deterministic threshold so we don't get
weeks without a block on a small fleet.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from arena.services.state import SimState

# Target ~1 block per 30 seconds at baseline fleet hashrate.
BLOCK_TARGET_INTERVAL_S = 30.0


def tick(state: SimState) -> dict | None:
    """Advance mining state. Returns a block payload if one was emitted."""
    with state.lock():
        # Total hashrate from active mining workloads = sum of node hashrates
        # that currently run a MINING workload.
        running_miner_nodes: set[str] = set()
        for w in state.workloads.values():
            if w.state == "RUNNING" and w.kind == "MINING" and w.assigned_node:
                running_miner_nodes.add(w.assigned_node)

        total_ths = sum(
            state.nodes[nid].hashrate_ths for nid in running_miner_nodes if nid in state.nodes
        )
        state.hashrate_ths = round(total_ths, 2)

        # Drift difficulty slowly toward a target proportional to fleet hashrate.
        target_difficulty = max(100_000.0, total_ths * 100_000.0)
        state.difficulty += (target_difficulty - state.difficulty) * 0.001

        # Probability per tick that we mint a block: hashrate / difficulty,
        # tuned to hit BLOCK_TARGET_INTERVAL_S on the seeded fleet.
        if total_ths <= 0:
            return None
        p = (total_ths * 1_000.0) / max(state.difficulty, 1.0) / BLOCK_TARGET_INTERVAL_S
        if random.random() > p:
            return None

        # Emit block
        now = datetime.now(timezone.utc)
        miner = random.choice(list(running_miner_nodes))
        nonce = random.randbytes(8).hex()
        h = hashlib.sha256(f"{state.tick_count}:{nonce}:{miner}".encode()).hexdigest()
        # Reward decays slowly with height for flavor.
        reward = 6.25 * (0.995 ** (state.tick_count // 1000))
        # Energy used by this block = sum of miner node draws * BLOCK_TARGET_INTERVAL_S
        kwh = sum(
            state.nodes[nid].power_draw_kw for nid in running_miner_nodes if nid in state.nodes
        ) * (BLOCK_TARGET_INTERVAL_S / 3600.0)

        return {
            "ts": now,
            "miner": miner,
            "hash": h,
            "reward_tokens": round(reward, 4),
            "energy_kwh": round(kwh, 3),
        }

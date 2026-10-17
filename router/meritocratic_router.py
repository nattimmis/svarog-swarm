#!/usr/bin/env python3
"""
Meritocratic router (reference stub).

Given a request and the swarm's current health view, score every healthy node
(including self) and pick the best. The best answer wins, not the loudest node.

This is intentionally small and dependency-free so you can read it in one sitting
and adapt it. It ships no network code, no credentials, and no node inventory.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Node:
    node_id: str
    # declared capability profile
    model_tier: int          # rough capability rank, e.g. 1=small 3B .. 5=frontier-local
    ctx_len: int             # usable context window (tokens)
    modalities: set = field(default_factory=lambda: {"text"})
    tokens_per_sec: float = 20.0
    # live state (from gossip)
    load: float = 0.0        # 0.0 idle .. 1.0 saturated
    healthy: bool = True
    is_self: bool = False


@dataclass
class Request:
    needs_tier: int = 1      # how hard is this task (1..5)
    needs_ctx: int = 2048    # tokens of context required
    modality: str = "text"


def capability_match(node: Node, req: Request) -> float:
    """Can this node do the job well? Penalise under-powered nodes hard,
    reward headroom mildly (do not waste a frontier node on a trivial task)."""
    if req.modality not in node.modalities:
        return float("-inf")          # cannot do it at all -> never routed here
    if node.ctx_len < req.needs_ctx:
        return float("-inf")          # context too small -> disqualified
    tier_gap = node.model_tier - req.needs_tier
    if tier_gap < 0:
        return -8.0 * abs(tier_gap)   # too weak for the task: steep penalty
    return 3.0 - 0.5 * tier_gap       # strong enough; mild penalty for overkill


def load_penalty(node: Node) -> float:
    # non-linear: a node past ~70% load becomes expensive to pick
    return 4.0 * (node.load ** 2)


def hop_penalty(node: Node) -> float:
    return 0.0 if node.is_self else 1.0   # prefer local when scores are close


def score(node: Node, req: Request) -> float:
    base = capability_match(node, req)
    if base == float("-inf"):
        return base
    return base - load_penalty(node) - hop_penalty(node)


def route(nodes: list[Node], req: Request) -> Node | None:
    """Return the best healthy node for this request, or None if the swarm
    cannot serve it right now (in which case the caller should fail closed)."""
    candidates = [n for n in nodes if n.healthy]
    if not candidates:
        return None
    best, best_score = None, float("-inf")
    for n in candidates:
        s = score(n, req)
        # tie-break toward self (lower latency, keeps traffic off the wire)
        if s > best_score or (s == best_score and n.is_self):
            best, best_score = n, s
    return best if best_score > float("-inf") else None


if __name__ == "__main__":
    swarm = [
        Node("self",  model_tier=2, ctx_len=8192,  tokens_per_sec=35, load=0.2, is_self=True),
        Node("gpu-1", model_tier=5, ctx_len=65536, tokens_per_sec=60, load=0.8),
        Node("gpu-2", model_tier=4, ctx_len=32768, tokens_per_sec=45, load=0.1),
        Node("edge",  model_tier=1, ctx_len=4096,  tokens_per_sec=12, load=0.0),
    ]

    trivial = Request(needs_tier=1, needs_ctx=1024)
    hard    = Request(needs_tier=5, needs_ctx=40000)

    print("trivial ->", route(swarm, trivial).node_id)   # self wins: cheap, local, strong enough
    print("hard    ->", route(swarm, hard).node_id)       # gpu-1 wins: only node whose context fits 40k,
                                                          # so it takes it despite being busy

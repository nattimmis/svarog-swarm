# Architecture

svarog is a peer-to-peer swarm. There are no tiers. Every node runs the same three things:
a local model runtime, a router, and a gossip/health loop. A node is useful on its own and
more useful in a mesh.

## 1. Node

A node owns:

- **A local model runtime.** Any OpenAI-compatible local server works (llama.cpp / `llama-server`,
  Ollama, vLLM, TGI). The swarm only needs a chat/completions endpoint and a declared capability
  profile (model family, context length, modality, rough tokens/sec).
- **A router.** Decides whether to answer locally or forward, and to whom. See
  [meritocratic routing](#3-meritocratic-routing).
- **A gossip loop.** Periodically exchanges a small health/capability record with a few peers.

A node holds no authority over any other node. Losing it costs the swarm that node's capacity
and nothing else.

## 2. Discovery, gossip and self-healing

Discovery is seed-based: a node starts from a small peer list (`SWARM_PEERS`) and learns the
rest through gossip. Each round, a node sends a compact record to a random subset of known peers:

```
{ node_id, caps, load, healthy, last_seen, known_peers[] }
```

From the union of records, every node builds its own eventually-consistent view of the mesh.
There is no single source of truth, by design.

**Self-healing** falls out of this:

- A peer not seen for `N` gossip rounds is marked `suspect`, then `down`, and dropped from routing.
- Work that would have gone to a down node is rescored against the remaining pool.
- When the node reappears and passes health, it is readmitted automatically.
- Split-brain is tolerated: two partitions each keep serving from what they can see, and reconcile
  their peer views when the partition heals.

Because every node runs the same loop, there is nothing special to restart when a particular box
dies. The swarm notices and reshapes.

## 3. Meritocratic routing

When a node receives a request it does not simply answer locally. It scores every healthy
candidate (including itself) and routes to the best one:

```
score(node, request) =
      capability_match(node.caps, request.needs)   # can it even do this well
    - load_penalty(node.load)                       # how busy is it now
    - hop_penalty(is_remote)                         # prefer local when close
    + affinity(node, request)                        # sticky sessions, warm caches
```

The highest score wins. "Best answer wins, not the loudest node." A tiny 3B model does not win
a hard reasoning request just because it is local; a strong but busy node does not win a trivial
one. Ties break toward the local node to keep latency low and traffic off the wire.

A reference implementation of this scoring is in
[`router/meritocratic_router.py`](../router/meritocratic_router.py).

## 4. Failing closed

A node pulls itself from the pool rather than serve degraded output when it detects any of:

- model runtime unreachable or returning errors,
- health check failing (disk, memory, GPU, temperature thresholds),
- integrity check on its own config/binaries failing (tamper signal).

The principle: **a service that fails closed is worth ten that fail open.** A node that is unsure
of itself should go quiet, not answer wrong. The swarm already knows how to route around silence.

## 5. Security posture

- **Local by default.** Prompts and completions do not leave the mesh.
- **Per-node independence.** Each node is provisioned with its own keys and rotated secrets. There
  is no shared master key whose theft compromises the fleet. (This repo ships none of them.)
- **Mesh-scoped transport.** Nodes are expected to talk over a private overlay / mutually
  authenticated channel, not the open internet.

## 6. What is intentionally out of scope here

Provisioning your overlay network, choosing and quantising models, and your own hardware
inventory are yours to decide. This repo documents the swarm behaviour and gives you readable
reference pieces, not an opinionated turnkey stack.

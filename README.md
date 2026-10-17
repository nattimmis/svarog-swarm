# svarog-swarm

A reference architecture for a **leaderless, self-healing swarm of machines that run their
own local models**. No central server to kill. No single node that matters. If one falls,
the others heal around the hole and carry on.

> Built and maintained by **Nathan Timmis** (Zurich). This repo documents the pattern so
> others can stand up their own swarm from scratch, which is what "reswarm" means here.

## Why

We spent a decade centralising inference behind a handful of APIs and calling it progress.
That buys convenience and sells away three things that matter: **privacy** (every prompt
leaves your network), **resilience** (one provider outage takes you down), and **sovereignty**
(someone else decides what your model will and will not say).

svarog is the opposite stance. Every box runs its own models locally. Nothing phones home.
The swarm routes a request to whichever node can answer it best right now, and keeps working
when nodes come and go. The design goal is simple to state and hard to earn: **a system that
cannot be decapitated.**

## Principles

- **No kings.** There is no master node and no control plane whose death is fatal. Every node
  is a peer that can discover others, answer requests, and route onward.
- **Self-healing.** Nodes continuously gossip health. When one drops, its share of work is
  redistributed. When it returns, it is folded back in. No human in the loop for the common case.
- **Local first.** Models run on the node. A node with no network still answers for itself.
- **Meritocratic routing.** The best answer wins, not the loudest node. Requests are scored and
  routed by capability and current load, not by a fixed hierarchy.
- **Fail closed, not open.** A node that detects tampering or an unhealthy state removes itself
  from the pool rather than serving degraded or unsafe output. Safety is the first design
  decision, not a bolt-on.

## How it fits together

```
          gossip + health (every node talks to a few peers)
   ┌───────────┐     ┌───────────┐     ┌───────────┐
   │  node A   │◄───►│  node B   │◄───►│  node C   │
   │ local LLM │     │ local LLM │     │ local LLM │
   │ router    │     │ router    │     │ router    │
   └───────────┘     └───────────┘     └───────────┘
        ▲                                     │
        └─────────── any node can take a request, score it,
                     and route it to the best available peer
```

Full design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Reswarm (bootstrap your own)

`reswarm.sh` is a reference bootstrap. It is intentionally generic: you supply your own node
list, model, and shared mesh, and it stands a node up and joins it to the swarm. It ships **no
credentials, no IP addresses, and no private topology** on purpose. Copy it, fill in your own
`swarm.env`, and run it per machine.

```bash
cp swarm.env.example swarm.env   # edit: SWARM_PEERS, SWARM_MODEL, bind addr
./reswarm.sh join                # stand up this node and join the mesh
./reswarm.sh status              # show peers + health as this node sees them
```

The meritocratic router stub lives in [`router/meritocratic_router.py`](router/meritocratic_router.py)
and shows the scoring idea in ~100 lines you can read in one sitting.

## What this is and is not

This is a **reference architecture and reading material**, distilled from a working private
swarm. It is a pattern to learn from and build on, not a turnkey product. It deliberately does
not include the author's production inventory, secrets, or any third-party or confidential
material.

## License

MIT. See [`LICENSE`](LICENSE).

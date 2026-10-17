#!/usr/bin/env bash
# reswarm.sh: stand up this machine as a svarog node and join the mesh.
#
# Reference bootstrap. Generic on purpose: it ships NO credentials, NO IP
# addresses, and NO private topology. You provide those in swarm.env (copy from
# swarm.env.example). Run it per machine. See README.md and docs/ARCHITECTURE.md.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SWARM_ENV:-$HERE/swarm.env}"

load_env() {
  [ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy swarm.env.example)"; exit 1; }
  # shellcheck disable=SC1090
  set -a; . "$ENV_FILE"; set +a
  : "${SWARM_PEERS:?set SWARM_PEERS (comma-separated seed peers)}"
  : "${SWARM_MODEL:?set SWARM_MODEL (local model id/path)}"
  : "${SWARM_BIND:=0.0.0.0:8080}"
  : "${SWARM_NODE_ID:=$(hostname)-$$}"
}

have() { command -v "$1" >/dev/null 2>&1; }

start_model_runtime() {
  # Bring up an OpenAI-compatible local server. Adapt to your runtime of choice.
  if have ollama; then
    echo "[reswarm] using ollama for $SWARM_MODEL"
    ollama serve >/dev/null 2>&1 &
    ollama pull "$SWARM_MODEL" >/dev/null 2>&1 || true
  elif have llama-server; then
    echo "[reswarm] using llama.cpp llama-server for $SWARM_MODEL"
    llama-server -m "$SWARM_MODEL" --host "${SWARM_BIND%%:*}" --port "${SWARM_BIND##*:}" \
      >/dev/null 2>&1 &
  else
    echo "[reswarm] no local runtime found (install ollama or llama.cpp)"; exit 1
  fi
}

register_self() {
  # Publish this node's capability record to each seed peer. The gossip loop
  # takes over from there. (Transport is yours: curl over your private overlay.)
  IFS=',' read -ra PEERS <<< "$SWARM_PEERS"
  for p in "${PEERS[@]}"; do
    echo "[reswarm] announcing $SWARM_NODE_ID to $p"
    # curl -fsS "https://$p/swarm/announce" -d "node_id=$SWARM_NODE_ID&bind=$SWARM_BIND" || true
  done
}

case "${1:-}" in
  join)
    load_env
    start_model_runtime
    register_self
    echo "[reswarm] node $SWARM_NODE_ID joined. it answers for itself even if the mesh is gone."
    ;;
  status)
    load_env
    echo "node_id : $SWARM_NODE_ID"
    echo "bind    : $SWARM_BIND"
    echo "model   : $SWARM_MODEL"
    echo "peers   : $SWARM_PEERS"
    echo "(wire your gossip view in here to print live peer health)"
    ;;
  *)
    echo "usage: $0 {join|status}"; exit 2;;
esac

#!/usr/bin/env bash
# Executa N rodadas do experimento na node-api: suíte de propriedades com cobertura (Jest/Istanbul)
# e análise de mutação (StrykerJS, mutadores padrão). Cada rodada grava em data/raw/node/run-XX/.
# Uso: scripts/run_node.sh [N=30] [INICIO=1]
set -euo pipefail
N=${1:-30}
INICIO=${2:-1}
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ/node-api"

for ((i = INICIO; i < INICIO + N; i++)); do
  DIR="$RAIZ/data/raw/node/run-$(printf '%02d' "$i")"
  rm -rf "$DIR" && mkdir -p "$DIR"
  echo "[node] rodada $i"

  # 1) suíte de propriedades com cobertura (tempo de parede da suíte)
  rm -rf coverage
  t0=$(date +%s.%N)
  npx jest --config jest.properties.config.js --coverage > "$DIR/suite.log" 2>&1
  t1=$(date +%s.%N)
  cp coverage/coverage-summary.json "$DIR/coverage-summary.json"

  # 2) mutação com StrykerJS
  rm -rf reports/mutation
  t2=$(date +%s.%N)
  npx stryker run > "$DIR/stryker.log" 2>&1
  t3=$(date +%s.%N)
  cp reports/mutation/mutation.json "$DIR/mutation.json"

  python3 - "$DIR" "$i" "$t0" "$t1" "$t2" "$t3" <<'EOF'
import json, sys
d, i, t0, t1, t2, t3 = sys.argv[1], int(sys.argv[2]), *map(float, sys.argv[3:])
json.dump({"ecossistema": "node", "execucao": i, "tempo_suite_s": round(t1 - t0, 3),
           "tempo_mutacao_s": round(t3 - t2, 3)}, open(f"{d}/meta.json", "w"))
EOF
done

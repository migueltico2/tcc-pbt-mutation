#!/usr/bin/env bash
# Linha de base opcional: mutação usando só os 11 casos de exemplo compartilhados (determinísticos,
# por isso uma execução por ecossistema). Grava em data/raw/baseline-exemplos/.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$RAIZ/data/raw/baseline-exemplos"
rm -rf "$OUT" && mkdir -p "$OUT"
source "$RAIZ/scripts/java_local_env.sh"
bash "$RAIZ/scripts/java_build.sh"
cd "$RAIZ/java-api"
CP="$(pwd)/target/classes:$(pwd)/target/test-classes:$TEST_LIBS"
java -cp "$RAIZ/scripts/pit-runner/out:$CP:$PIT_LIBS" PitRunner "$CP:$PIT_LIBS" \
  'br.pucminas.tcc.ingressos.domain.*' 'br.pucminas.tcc.ingressos.examples.*' "$OUT/java-pit" src/main/java > "$OUT/java-pit.log" 2>&1
cd "$RAIZ/node-api"
npx stryker run stryker.examples.config.json > "$OUT/node-stryker.log" 2>&1
cp reports/mutation/examples.json "$OUT/node-mutation.json"

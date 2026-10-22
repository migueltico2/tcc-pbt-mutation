#!/usr/bin/env bash
# Linha de base: mutação usando só os 11 casos de exemplo compartilhados (determinísticos, por isso
# uma execução por ecossistema), com os mesmos operadores do experimento (PIT: DEFAULTS ∪ STRONGER ∪
# NEGATE_CONDITIONALS; StrykerJS: padrão). Grava em data/raw/v2/baseline-exemplos/.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$RAIZ/data/raw/v2/baseline-exemplos"
rm -rf "$OUT" && mkdir -p "$OUT"
source "$RAIZ/scripts/java_local_env.sh"
bash "$RAIZ/scripts/java_build.sh"
cd "$RAIZ/java-api"
CP="$(pwd)/target/classes:$(pwd)/target/test-classes:$TEST_LIBS"
java -Dpit.mutators=DEFAULTS,STRONGER,NEGATE_CONDITIONALS -cp "$RAIZ/scripts/pit-runner/out:$CP:$PIT_LIBS" \
  PitRunner "$CP:$PIT_LIBS" 'br.pucminas.tcc.ingressos.domain.*' 'br.pucminas.tcc.ingressos.examples.*' \
  "$OUT/java-pit" src/main/java > "$OUT/java-pit.log" 2>&1
gzip -9 "$OUT/java-pit/mutations.xml" && rm -f "$OUT/java-pit/mutations.csv"
cd "$RAIZ/node-api"
npx stryker run stryker.examples.config.json > "$OUT/node-stryker.log" 2>&1
gzip -9 -c reports/mutation/examples.json > "$OUT/node-mutation.json.gz"

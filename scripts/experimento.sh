#!/usr/bin/env bash
# Experimento fatorial do TCC II (versão 2):
#   ecossistema (java, node) × suíte (fraca = P1–P8, forte = P1–P17) × tentativas (10, 100, 1000)
#   = 12 configurações, N rodadas cada.
# Em cada rodada as 12 configurações são executadas em ordem aleatória (semente = nº da rodada),
# para que variações de carga da máquina não se concentrem em uma configuração.
# Cada execução grava em data/raw/v2/<eco>/<suite>-t<tentativas>/run-XX/.
#
# Operadores: o PIT roda com DEFAULTS ∪ STRONGER ∪ NEGATE_CONDITIONALS e o StrykerJS com o conjunto
# padrão. Os recortes "padrão" e "harmonizado" são calculados depois, por operador (consolidate.py),
# o que é válido porque cada mutante é avaliado isoladamente.
#
# Uso: scripts/experimento.sh [N=30] [INICIO=1]
# Requer as ferramentas de scripts/java_local_env.sh (ou adapte para o pom.xml) e node-api/node_modules.
set -euo pipefail
N=${1:-30}
INICIO=${2:-1}
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
source "$RAIZ/scripts/java_local_env.sh"
bash "$RAIZ/scripts/java_build.sh"
javac -nowarn -cp "$PIT_LIBS" -d "$RAIZ/scripts/pit-runner/out" "$RAIZ/scripts/pit-runner/PitRunner.java"

CONSOLE=/usr/share/java/junit-platform-console-standalone-1.9.1.jar
PKG=br.pucminas.tcc.ingressos.properties
FRACA_JAVA="$PKG.PropriedadesPrecoTest,$PKG.PropriedadesDisponibilidadeTest,$PKG.PropriedadesStatusTest"
FORTE_JAVA="$FRACA_JAVA,$PKG.PropriedadesForte*"
PIT_MUTADORES="DEFAULTS,STRONGER,NEGATE_CONDITIONALS"
LOG="$RAIZ/data/raw/v2/experimento.log"
mkdir -p "$RAIZ/data/raw/v2"

registrar_meta() { # dir eco suite tentativas rodada t0 t1 t2 t3
  python3 - "$@" <<'EOF'
import json, sys
d, eco, suite, tent, i = sys.argv[1:6]
t0, t1, t2, t3 = map(float, sys.argv[6:10])
json.dump({"ecossistema": eco, "suite": suite, "tentativas": int(tent), "execucao": int(i),
           "tempo_suite_s": round(t1 - t0, 3), "tempo_mutacao_s": round(t3 - t2, 3)}, open(f"{d}/meta.json", "w"))
EOF
}

rodar_java() { # suite tentativas rodada
  local suite=$1 t=$2 i=$3
  local dir="$RAIZ/data/raw/v2/java/$suite-t$t/run-$(printf '%02d' "$i")"
  [ -f "$dir/meta.json" ] && return 0   # execução já concluída (permite retomar o experimento)
  rm -rf "$dir" && mkdir -p "$dir"
  cd "$RAIZ/java-api"
  local cp="$(pwd)/target/classes:$(pwd)/target/test-classes:$TEST_LIBS"
  local alvos=$FRACA_JAVA; [ "$suite" = forte ] && alvos=$FORTE_JAVA
  local selecao=()
  if [ "$suite" = forte ]; then selecao=(--select-package "$PKG"); else
    for c in ${alvos//,/ }; do selecao+=(--select-class "$c"); done; fi
  local t0 t1 t2 t3
  t0=$(date +%s.%N)
  java -Djqwik.tries.default="$t" -javaagent:"$JACOCO_AGENT"=destfile="$dir/jacoco.exec" -jar "$CONSOLE" execute \
    -cp "$cp" "${selecao[@]}" --disable-banner --details=summary > "$dir/suite.log" 2>&1
  t1=$(date +%s.%N)
  java -jar "$JACOCO_CLI" report "$dir/jacoco.exec" --classfiles target/classes \
    --sourcefiles src/main/java --csv "$dir/jacoco.csv" > /dev/null 2>&1
  rm -f "$dir/jacoco.exec"
  t2=$(date +%s.%N)
  java -Dpit.mutators="$PIT_MUTADORES" -Dpit.jvmArgs="-Djqwik.tries.default=$t" \
    -cp "$RAIZ/scripts/pit-runner/out:$cp:$PIT_LIBS" PitRunner "$cp:$PIT_LIBS" \
    'br.pucminas.tcc.ingressos.domain.*' "$alvos" "$dir/pit" src/main/java > "$dir/pit.log" 2>&1
  t3=$(date +%s.%N)
  gzip -9 "$dir/pit/mutations.xml" && rm -f "$dir/pit/mutations.csv"
  registrar_meta "$dir" java "$suite" "$t" "$i" "$t0" "$t1" "$t2" "$t3"
}

rodar_node() { # suite tentativas rodada
  local suite=$1 t=$2 i=$3
  local dir="$RAIZ/data/raw/v2/node/$suite-t$t/run-$(printf '%02d' "$i")"
  [ -f "$dir/meta.json" ] && return 0   # execução já concluída (permite retomar o experimento)
  rm -rf "$dir" && mkdir -p "$dir"
  cd "$RAIZ/node-api"
  local t0 t1 t2 t3
  rm -rf coverage
  t0=$(date +%s.%N)
  SUITE=$suite PBT_TENTATIVAS=$t npx jest --config jest.properties.config.js --coverage > "$dir/suite.log" 2>&1
  t1=$(date +%s.%N)
  cp coverage/coverage-summary.json "$dir/coverage-summary.json"
  rm -rf reports/mutation
  t2=$(date +%s.%N)
  SUITE=$suite PBT_TENTATIVAS=$t npx stryker run > "$dir/stryker.log" 2>&1
  t3=$(date +%s.%N)
  gzip -9 -c reports/mutation/mutation.json > "$dir/mutation.json.gz"
  registrar_meta "$dir" node "$suite" "$t" "$i" "$t0" "$t1" "$t2" "$t3"
}

CONFIGS=()
for eco in java node; do for suite in fraca forte; do for t in 10 100 1000; do
  CONFIGS+=("$eco $suite $t"); done; done; done

for ((i = INICIO; i < INICIO + N; i++)); do
  mapfile -t ordem < <(printf '%s\n' "${CONFIGS[@]}" | shuf --random-source=<(yes "$i"))
  for cfg in "${ordem[@]}"; do
    read -r eco suite t <<< "$cfg"
    echo "$(date -u +%FT%TZ) rodada $i $eco $suite t=$t" >> "$LOG"
    if [ "$eco" = java ]; then rodar_java "$suite" "$t" "$i"; else rodar_node "$suite" "$t" "$i"; fi
  done
  echo "$(date -u +%FT%TZ) rodada $i concluída" >> "$LOG"
done
echo "$(date -u +%FT%TZ) EXPERIMENTO_CONCLUIDO" >> "$LOG"

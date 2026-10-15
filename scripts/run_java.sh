#!/usr/bin/env bash
# Executa N rodadas do experimento na java-api: suíte de propriedades com cobertura (JaCoCo)
# e análise de mutação (PIT, mutadores DEFAULTS). Cada rodada grava em data/raw/java/run-XX/.
# Uso: scripts/run_java.sh [N=30] [INICIO=1]
set -euo pipefail
N=${1:-30}
INICIO=${2:-1}
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
source "$RAIZ/scripts/java_local_env.sh"
bash "$RAIZ/scripts/java_build.sh"
cd "$RAIZ/java-api"
CP="$(pwd)/target/classes:$(pwd)/target/test-classes:$TEST_LIBS"
CONSOLE=/usr/share/java/junit-platform-console-standalone-1.9.1.jar

for ((i = INICIO; i < INICIO + N; i++)); do
  DIR="$RAIZ/data/raw/java/run-$(printf '%02d' "$i")"
  rm -rf "$DIR" && mkdir -p "$DIR"
  echo "[java] rodada $i"

  # 1) suíte de propriedades com JaCoCo (tempo de parede da suíte)
  t0=$(date +%s.%N)
  java -javaagent:"$JACOCO_AGENT"=destfile="$DIR/jacoco.exec" -jar "$CONSOLE" execute \
    -cp "$CP" --select-package br.pucminas.tcc.ingressos.properties \
    --disable-banner --details=summary > "$DIR/suite.log" 2>&1
  t1=$(date +%s.%N)
  java -jar "$JACOCO_CLI" report "$DIR/jacoco.exec" --classfiles target/classes \
    --sourcefiles src/main/java --csv "$DIR/jacoco.csv" > /dev/null 2>&1

  # 2) mutação com PIT
  t2=$(date +%s.%N)
  java -cp "$RAIZ/scripts/pit-runner/out:$CP:$PIT_LIBS" PitRunner "$CP:$PIT_LIBS" \
    'br.pucminas.tcc.ingressos.domain.*' 'br.pucminas.tcc.ingressos.properties.*' \
    "$DIR/pit" src/main/java > "$DIR/pit.log" 2>&1
  t3=$(date +%s.%N)

  python3 - "$DIR" "$i" "$t0" "$t1" "$t2" "$t3" <<'EOF'
import json, sys
d, i, t0, t1, t2, t3 = sys.argv[1], int(sys.argv[2]), *map(float, sys.argv[3:])
json.dump({"ecossistema": "java", "execucao": i, "tempo_suite_s": round(t1 - t0, 3),
           "tempo_mutacao_s": round(t3 - t2, 3)}, open(f"{d}/meta.json", "w"))
EOF
done

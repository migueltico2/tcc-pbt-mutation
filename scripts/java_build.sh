#!/usr/bin/env bash
# Compila domínio e testes da java-api sem Maven (javac --release 17).
set -euo pipefail
cd "$(dirname "$0")/../java-api"
source ../scripts/java_local_env.sh
rm -rf target/classes target/test-classes && mkdir -p target/classes target/test-classes
javac --release 17 -encoding UTF-8 -d target/classes $(find src/main/java/br/pucminas/tcc/ingressos/domain -name "*.java")
javac --release 17 -encoding UTF-8 -cp target/classes:$TEST_LIBS -d target/test-classes $(find src/test/java/br/pucminas/tcc/ingressos/examples src/test/java/br/pucminas/tcc/ingressos/properties -name "*.java")
cp -r src/test/resources/* target/test-classes/

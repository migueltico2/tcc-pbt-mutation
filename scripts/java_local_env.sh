# Classpath das ferramentas Java compiladas localmente (ambiente sem Maven Central).
# Na máquina do pesquisador, use o pom.xml (mvn test / mvn org.pitest:pitest-maven:mutationCoverage).
L=/usr/share/java
T=${TOOLS:-$HOME/tools}
export TEST_LIBS="$T/jqwik-1.7.4.jar:$L/junit-platform-console-standalone-1.9.1.jar:$L/opentest4j-1.2.0.jar:$L/apiguardian-api-1.1.2.jar"
export PIT_LIBS="$T/pitest-core-1.18.2.jar:$T/pitest-entry-1.18.2.jar:$T/pitest-junit5-plugin-1.2.3.jar:$L/asm-9.7.jar:$L/asm-commons-9.7.jar:$L/asm-tree-9.7.jar:$L/asm-util-9.7.jar:$L/asm-analysis-9.7.jar:$L/commons-text.jar:$L/commons-lang3.jar"
export JACOCO_AGENT="$T/jacoco/lib/jacocoagent.jar"
export JACOCO_CLI="$T/jacoco/lib/jacococli.jar"

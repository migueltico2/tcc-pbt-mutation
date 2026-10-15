# Diário de configuração (métrica M14)

Registro, em ordem, do que foi preciso para levar cada ecossistema da suíte de propriedades
até a primeira análise de mutação bem-sucedida. Data: 15/10/2026.

## Java (jqwik + PIT + JaCoCo)

Caminho padrão (máquina com acesso ao Maven Central), declarado em `java-api/pom.xml`:

- 2 arquivos de configuração: `pom.xml` (dependência do jqwik e plugins do PIT e do JaCoCo) e
  `src/test/resources/junit-platform.properties` (tentativas, modo de geração e política de sementes do jqwik).
- 4 artefatos declarados para o experimento: `jqwik`, `pitest-maven`, `pitest-junit5-plugin`, `jacoco-maven-plugin`.
- Ponto de atenção: o PIT só executa testes JUnit 5/jqwik com o `pitest-junit5-plugin` declarado como
  dependência do plugin; sem ele, nenhum teste é encontrado.
- Ponto de atenção: o jqwik, por padrão, reexecuta primeiro a semente que falhou na execução anterior
  (`failures.after.default = SAMPLE_FIRST` / banco `.jqwik-database`). Sob o PIT isso faz um mutante
  influenciar o seguinte; foi preciso desligar (`RANDOM_SEED`, `failures.runfirst = false`).
- Ponto de atenção: com 100 tentativas, o jqwik avisa que a geração de casos de borda excede o número
  de tentativas e interrompe a geração após 100 casos — os casos de borda dominam a amostra.

Caminho efetivamente usado no ambiente do experimento (sem acesso ao Maven Central):

1. Maven Central bloqueado (HTTP 403 no proxy). Bibliotecas JUnit 5, ASM, commons-text e
   anotações obtidas dos pacotes do Ubuntu 24.04; JaCoCo 0.8.12 obtido da página de releases no GitHub.
2. jqwik 1.7.4 compilado a partir do código-fonte (tag `1.7.4`), escolhido por ser compatível com a
   JUnit Platform 1.9 disponível. Exigiu as anotações `org.jetbrains.annotations` e `javax.annotation` (JSR-305).
3. PIT 1.18.2 compilado a partir do código-fonte (tag `1.18.2`), escolhido por usar ASM 9.7, a versão
   disponível. O módulo de linha de comando foi substituído por um executor de 40 linhas
   (`scripts/pit-runner/PitRunner.java`) que chama a mesma API (`EntryPoint`) usada pelo plugin Maven.
4. Erro `Unable to load class content for org.pitest.boot.HotSwapAgent`: o classpath analisado precisa
   conter os próprios jars do PIT (o plugin Maven faz isso automaticamente). Corrigido no script.
5. `pitest-junit5-plugin` 1.2.3 compilado a partir do código-fonte.

## Node.js (fast-check + StrykerJS + Jest)

- `npm install --save-dev jest fast-check @stryker-mutator/core @stryker-mutator/jest-runner`
  (4 pacotes do experimento; `express` e `supertest` são da camada REST).
- 4 arquivos de configuração: `package.json`, `jest.properties.config.js` (só a suíte de propriedades e
  cobertura do domínio), `test/properties/setup.js` (`fc.configureGlobal({ numRuns: 100 })`) e
  `stryker.config.json`.
- Nenhum erro até a primeira análise de mutação bem-sucedida.
- Ajuste metodológico: `disableBail: true` no StrykerJS, para registrar todas as propriedades que matam
  cada mutante, como a matriz completa do PIT. Sem isso, o StrykerJS para no primeiro teste que falha.

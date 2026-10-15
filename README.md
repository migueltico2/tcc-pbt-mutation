# TCC — PBT × Mutation Testing em APIs REST Java/Spring Boot e Node.js/Express

Repositório do Trabalho de Conclusão de Curso *"Análise Comparativa da Efetividade de Testes Baseados
em Propriedades em APIs REST Java/Spring Boot e Node.js/Express por meio de Mutation Testing"*
(Miguel Vieira — Engenharia de Software, PUC Minas, 2026).

Duas implementações equivalentes de uma API de eventos e reservas de ingressos recebem as mesmas
oito propriedades de negócio (P1–P8), escritas com **jqwik** (Java) e **fast-check** (Node.js), e são
avaliadas por **PIT** e **StrykerJS** em 30 execuções por ecossistema.

## Estrutura

```
SPEC.md                    regras R1–R20, propriedades P1–P8 e faixas dos geradores
shared/casos-exemplo.json  11 cenários de exemplo executados pelas duas APIs (equivalência)
java-api/                  Spring Boot 3.3 + jqwik 1.7.4 + PIT 1.18.2 + JaCoCo 0.8.12 (pom.xml)
  src/main/.../domain/     regras de negócio (alvo da mutação)
  src/main/.../web/        controladores REST finos
  src/test/.../properties/ P1–P8 em jqwik
  src/test/.../examples/   executor dos casos compartilhados
node-api/                  Express 5 + fast-check 4 + Jest 30 + StrykerJS 10
  src/domain/              regras de negócio (alvo da mutação)
  src/web/                 rotas REST finas
  test/properties/         P1–P8 em fast-check
  test/examples/           executor dos casos compartilhados
scripts/                   coleta (run_java.sh, run_node.sh) e consolidação (consolidate.py)
data/raw/                  relatórios brutos de cada execução (PIT XML, Stryker JSON, cobertura, tempos)
data/runs.csv              uma linha por execução
data/mutants.csv           uma linha por mutante por execução
analysis/                  analise.py, tabelas (resultados/) e figuras (figuras/)
artigo/                    texto do TCC em LaTeX
docs/diario.md             registro do esforço de configuração
```

## Como reproduzir

### Node.js

```bash
cd node-api
npm install
npm test                      # exemplos compartilhados + propriedades + REST
npm run test:properties       # só P1–P8
npx stryker run               # mutação (relatório em reports/mutation)
npm start                     # API em http://localhost:3000
```

### Java (com Maven)

```bash
cd java-api
mvn test                                                   # exemplos + propriedades + REST
mvn test-compile org.pitest:pitest-maven:mutationCoverage  # mutação (target/pit-reports)
mvn spring-boot:run                                        # API em http://localhost:8080
```

### Experimento completo (30 execuções) e análise

```bash
scripts/run_java.sh 30      # requer as ferramentas de scripts/java_local_env.sh (ver nota abaixo)
scripts/run_node.sh 30
python3 scripts/consolidate.py
python3 analysis/analise.py
```

**Nota sobre o ambiente do experimento.** As 30 execuções foram feitas em uma máquina sem acesso ao
Maven Central. Por isso, jqwik 1.7.4, PIT 1.18.2 e pitest-junit5-plugin 1.2.3 foram compilados a partir
do código-fonte das tags publicadas, e o PIT foi acionado por `scripts/pit-runner/PitRunner.java`,
que usa a mesma API do plugin Maven. O `pom.xml` declara exatamente essas versões. Detalhes em
`docs/diario.md`.

## Rotas REST (iguais nas duas APIs)

| Método | Rota | Operação |
| --- | --- | --- |
| POST | /eventos | criar evento |
| GET | /eventos/{id} | consultar evento |
| PATCH | /eventos/{id}/status | alterar status do evento |
| POST | /eventos/{id}/lotes | criar lote |
| GET | /lotes/{id} | consultar lote |
| POST | /cupons | cadastrar cupom |
| POST | /reservas | criar reserva |
| GET | /reservas/{id} | consultar reserva (com totais) |
| POST | /reservas/{id}/itens | adicionar item |
| PUT | /reservas/{id}/cupom | aplicar cupom |
| POST | /reservas/{id}/confirmacao | confirmar |
| POST | /reservas/{id}/pagamento | pagar (simulado) |
| POST | /reservas/{id}/cancelamento | cancelar |
| POST | /reservas/{id}/expiracao | expirar |

Erros de regra de negócio retornam `{"erro": "<CODIGO>"}` com HTTP 404 (não encontrado) ou 422 (demais).

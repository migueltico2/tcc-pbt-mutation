# TCC — PBT × Mutation Testing em APIs REST Java/Spring Boot e Node.js/Express

Repositório do Trabalho de Conclusão de Curso *"Análise Comparativa da Efetividade de Testes Baseados
em Propriedades em APIs REST Java/Spring Boot e Node.js/Express por meio de Mutation Testing"*
(Miguel Vieira — Engenharia de Software, PUC Minas, 2026).

Duas implementações equivalentes de uma API de eventos e reservas de ingressos recebem as mesmas
propriedades de negócio, escritas com **jqwik** (Java) e **fast-check** (Node.js), e são avaliadas por
**PIT** e **StrykerJS**. O experimento é fatorial:

| Fator | Níveis |
| --- | --- |
| Ecossistema | Java (jqwik + PIT), Node.js (fast-check + StrykerJS) |
| Suíte de propriedades | fraca (P1–P8, do TCC I), forte (P1–P17, com oráculos exatos) |
| Tentativas por propriedade | 10, 100, 1000 |
| Operadores de mutação (recorte) | padrão de cada ferramenta, harmonizado entre as duas |
| Repetições | 30 por configuração (360 execuções) |

[![CI](https://github.com/migueltico2/tcc-pbt-mutation/actions/workflows/ci.yml/badge.svg)](https://github.com/migueltico2/tcc-pbt-mutation/actions/workflows/ci.yml)

## Estrutura

```
SPEC.md                    regras R1–R20, propriedades P1–P17 e faixas dos geradores
shared/casos-exemplo.json  11 cenários de exemplo executados pelas duas APIs (equivalência e linha de base)
java-api/                  Spring Boot 3.3 + jqwik 1.7.4 + PIT 1.18.2 + JaCoCo 0.8.12 (pom.xml)
  src/main/.../domain/     regras de negócio (alvo da mutação)
  src/main/.../web/        controladores REST finos
  src/test/.../properties/ P1–P8 (Propriedades*Test) e P9–P17 (PropriedadesForte*Test)
  src/test/.../examples/   executor dos casos compartilhados
node-api/                  Express 5 + fast-check 4 + Jest 30 + StrykerJS 10
  src/domain/              regras de negócio (alvo da mutação)
  src/web/                 rotas REST finas
  test/properties/         P1–P8; test/properties/fortes/ P9–P17
  test/examples/           executor dos casos compartilhados
scripts/                   experimento.sh (fatorial), run_baseline_examples.sh, consolidate.py
data/raw/v2/               relatórios brutos de cada execução (PIT XML e Stryker JSON compactados, cobertura, tempos)
data/runs.csv              uma linha por execução
data/mutants.csv           uma linha por mutante por execução
analysis/                  analise.py, classificar_sobreviventes.py, tabelas (resultados/) e figuras (figuras/)
artigo/                    texto do TCC em LaTeX
docs/diario.md             registro da configuração do ambiente
```

## Como reproduzir

### Node.js

```bash
cd node-api
npm ci
npm test                                           # exemplos + propriedades (fraca e forte) + REST
npm run test:properties                            # só a suíte fraca (P1–P8)
SUITE=forte npm run test:properties                # suíte forte (P1–P17)
SUITE=forte PBT_TENTATIVAS=1000 npx stryker run    # mutação com a suíte forte e 1000 tentativas
npm start                                          # API em http://localhost:3000
```

### Java (com Maven)

```bash
cd java-api
mvn test                                                                  # exemplos + propriedades + REST
mvn test-compile org.pitest:pitest-maven:mutationCoverage                 # mutação, suíte fraca
mvn test-compile org.pitest:pitest-maven:mutationCoverage -Psuite-forte   # mutação, suíte forte
mvn test -Djqwik.tries.default=1000                                        # outro número de tentativas
mvn spring-boot:run                                                       # API em http://localhost:8080
```

### Experimento completo e análise

```bash
scripts/experimento.sh 30          # 30 rodadas × 12 configurações (retomável: pula execuções concluídas)
scripts/run_baseline_examples.sh   # linha de base com os 11 cenários de exemplo
python3 scripts/consolidate.py
python3 analysis/analise.py
python3 analysis/classificar_sobreviventes.py
```

**Nota sobre o ambiente do experimento.** As execuções foram feitas em uma máquina sem acesso ao
Maven Central. Por isso, jqwik 1.7.4, PIT 1.18.2 e pitest-junit5-plugin 1.2.3 foram compilados a partir
do código-fonte das tags publicadas (ver `scripts/java_local_env.sh`), e o PIT foi acionado por
`scripts/pit-runner/PitRunner.java`, que usa a mesma API do plugin Maven. A integração contínua
(`.github/workflows/ci.yml`) roda o PIT pelo plugin Maven oficial e reproduz os mesmos resultados.

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

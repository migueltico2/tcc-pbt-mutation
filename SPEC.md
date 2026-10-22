# Especificação da aplicação de referência

API REST de gestão de eventos e reservas de ingressos. Esta especificação é a fonte
única das duas implementações (`java-api/` e `node-api/`). Toda regra tem um
identificador (R1…R20) e cada propriedade (P1…P8) aponta as regras que verifica.

## Convenções

- **Dinheiro em centavos inteiros** (`long` em Java, inteiro em JavaScript). Nenhum valor
  monetário usa ponto flutuante.
- **Datas** no formato ISO `AAAA-MM-DD`, comparadas lexicograficamente.
- **Persistência em memória** (`Map`), recriada a cada instância do serviço.
- **Erros de regra de negócio** são lançados como `RegraNegocioException` (Java) /
  `RegraNegocioError` (JS), sempre com um dos códigos da tabela final. A camada REST
  converte o código em HTTP 404 (`*_NAO_ENCONTRADO`) ou 422 (demais).

## Entidades

| Entidade | Campos |
| --- | --- |
| Evento | id, nome, data, local, status (`ATIVO`, `CANCELADO`, `ENCERRADO`), capacidade |
| Lote | id, eventoId, nome, precoCentavos, quantidadeTotal, quantidadeDisponivel |
| Cupom | codigo, tipo (`PERCENTUAL`, `FIXO`), valor, minimoCentavos, maximoDescontoCentavos (opcional), validoAte |
| Reserva | id, eventoId, itens [{loteId, quantidade}], codigoCupom (opcional), status |

## Regras

### Eventos
- **R1** Capacidade deve ser inteiro > 0; nome não vazio. Senão `DADOS_INVALIDOS`.
- **R2** Evento nasce `ATIVO`. Só eventos `ATIVO` aceitam novas reservas, itens e
  confirmações (`EVENTO_INDISPONIVEL`).

### Lotes
- **R3** precoCentavos ≥ 0 e quantidadeTotal > 0 (`DADOS_INVALIDOS`).
- **R4** A soma de `quantidadeTotal` dos lotes de um evento não pode exceder a capacidade
  do evento (`CAPACIDADE_EXCEDIDA`).
- **R5** Lote nasce com `quantidadeDisponivel = quantidadeTotal`. Em todo momento,
  0 ≤ quantidadeDisponivel ≤ quantidadeTotal.

### Reservas e itens
- **R6** Reserva nasce `CRIADA`, sem itens, para um evento `ATIVO`.
- **R7** Itens só podem ser adicionados em reserva `CRIADA` (`TRANSICAO_INVALIDA`);
  quantidade deve ser > 0 (`QUANTIDADE_INVALIDA`); o lote deve pertencer ao evento da
  reserva (`LOTE_INVALIDO`).
- **R8** Subtotal = Σ (precoCentavos do lote × quantidade) sobre os itens.

### Cupons
- **R9** Cupom `PERCENTUAL`: valor inteiro em [1, 100]. Cupom `FIXO`: valor > 0 em centavos.
  minimoCentavos ≥ 0; maximoDescontoCentavos, se presente, > 0 (`DADOS_INVALIDOS`).
- **R10** Cupom só pode ser aplicado em reserva `CRIADA` (`TRANSICAO_INVALIDA`). Aplicar um
  código inexistente não é erro: a reserva guarda o código, e o desconto é zero (R12).
- **R11** Desconto bruto: `PERCENTUAL` → ⌊subtotal × valor / 100⌋; `FIXO` → valor.
  Se houver maximoDescontoCentavos, desconto = min(bruto, máximo).
- **R12** O desconto é **zero** quando: não há cupom; o código não existe; o cupom está
  expirado (`hoje > validoAte`); ou subtotal < minimoCentavos.
- **R13** Desconto efetivo = min(desconto, subtotal). Total = subtotal − desconto efetivo.
  Logo 0 ≤ desconto ≤ subtotal e total ≥ 0.

### Disponibilidade
- **R14** Confirmar exige reserva `CRIADA` (`TRANSICAO_INVALIDA`), ao menos um item
  (`RESERVA_VAZIA`) e evento `ATIVO` (`EVENTO_INDISPONIVEL`).
- **R15** Confirmar exige, para cada lote, disponibilidade ≥ soma das quantidades pedidas
  daquele lote na reserva (`DISPONIBILIDADE_INSUFICIENTE`). A verificação é feita para
  todos os lotes **antes** de qualquer baixa: ou baixa tudo, ou nada.
- **R16** Ao confirmar, cada lote perde exatamente a quantidade reservada; a reserva vira
  `CONFIRMADA`.
- **R17** Cancelar ou expirar uma reserva `CONFIRMADA` devolve exatamente as quantidades
  reservadas aos lotes. Cancelar ou expirar uma reserva `CRIADA` não altera lotes.

### Status da reserva
- **R18** Transições válidas (qualquer outra → `TRANSICAO_INVALIDA`, sem efeito colateral):

| De | Para | Operação |
| --- | --- | --- |
| CRIADA | CONFIRMADA | confirmar |
| CRIADA | CANCELADA | cancelar |
| CRIADA | EXPIRADA | expirar |
| CONFIRMADA | PAGA | pagar (pagamento simulado) |
| CONFIRMADA | CANCELADA | cancelar (devolve disponibilidade) |
| CONFIRMADA | EXPIRADA | expirar (devolve disponibilidade) |

- **R19** `PAGA`, `CANCELADA` e `EXPIRADA` são finais: nenhuma operação as altera.
- **R20** Entidade inexistente → `EVENTO_NAO_ENCONTRADO`, `LOTE_NAO_ENCONTRADO`,
  `RESERVA_NAO_ENCONTRADA`.

## Códigos de erro

`DADOS_INVALIDOS`, `CAPACIDADE_EXCEDIDA`, `EVENTO_INDISPONIVEL`, `QUANTIDADE_INVALIDA`,
`LOTE_INVALIDO`, `RESERVA_VAZIA`, `DISPONIBILIDADE_INSUFICIENTE`, `TRANSICAO_INVALIDA`,
`EVENTO_NAO_ENCONTRADO`, `LOTE_NAO_ENCONTRADO`, `RESERVA_NAO_ENCONTRADA`.

## Propriedades (P1–P8)

| Propriedade | Enunciado | Regras |
| --- | --- | --- |
| P1 Total não negativo | Para qualquer conjunto de itens e qualquer cupom (válido, expirado, abaixo do mínimo ou inexistente), total ≥ 0. | R8, R11–R13 |
| P2 Desconto limitado | Para qualquer cupom, 0 ≤ desconto ≤ subtotal e total = subtotal − desconto. | R11, R13 |
| P3 Comutatividade do subtotal | Permutar a ordem dos itens não altera o subtotal. | R8 |
| P4 Cupom inválido neutro | Cupom inexistente, expirado ou com mínimo acima do subtotal não altera o total (total = subtotal). | R12 |
| P5 Disponibilidade não negativa | Após qualquer tentativa de confirmação (bem-sucedida ou não), toda disponibilidade fica em [0, quantidadeTotal]. | R5, R15 |
| P6 Redução correta | Confirmação bem-sucedida reduz cada lote exatamente pela soma das quantidades reservadas; confirmação recusada não altera nenhum lote. | R15, R16 |
| P7 Cancelamento restaura | Confirmar e depois cancelar (ou expirar) devolve cada lote à disponibilidade inicial. | R17 |
| P8 Transições válidas | Para qualquer sequência de operações, cada operação ou segue a tabela R18, ou é recusada sem mudar o status; estados finais nunca mudam. | R18, R19 |

## Suíte forte (P9–P17)

A suíte das propriedades P1–P8 (suíte **fraca**, vinda do TCC I) verifica limites e relações de metade
das regras. A suíte **forte** acrescenta P9–P17, derivadas regra a regra desta especificação para que
toda regra R1–R20 tenha ao menos uma propriedade com **oráculo exato**: o resultado esperado é
calculado por um modelo de referência escrito a partir deste documento (não a partir do código), e os
nomes de tipos e status são comparados com os nomes definidos aqui.

| Propriedade | Enunciado | Regras |
| --- | --- | --- |
| P9 Oráculo de preço | Para qualquer compra e cupom (gerado, inexistente ou ausente), subtotal, desconto e total são exatamente os do modelo de R8 e R11–R13. | R8, R11–R13 |
| P10 Validação de evento | Evento com nome nulo/em branco ou capacidade ≤ 0 é recusado com `DADOS_INVALIDOS`; evento válido nasce `ATIVO` e é recuperado com os mesmos dados. | R1, R2 |
| P11 Validação de lote e capacidade | Em qualquer sequência de cadastros de lotes, cada lote é recusado com `DADOS_INVALIDOS` ou `CAPACIDADE_EXCEDIDA` exatamente quando o modelo prevê (lotes de outro evento não contam); lote aceito nasce com disponibilidade = total. | R3, R4, R5 |
| P12 Validação de cupom | O cadastro aceita exatamente os cupons válidos e preserva seus dados. | R9 |
| P13 Itens da reserva | Adicionar item segue a ordem de verificação (status, quantidade, lote do evento); item aceito é registrado, item recusado não altera a reserva. | R7 |
| P14 Evento inativo e reserva vazia | Só evento `ATIVO` aceita novas reservas, itens e confirmações; reserva vazia não confirma; confirmação recusada não altera lotes. | R2, R6, R14 |
| P15 Cupom só em reserva criada | Aplicar cupom só é aceito em reserva `CRIADA` (código inexistente é guardado); nos demais status é recusado sem efeito. | R10 |
| P16 Entidade inexistente | Toda operação sobre id inexistente falha com o código da entidade; ids existentes continuam sendo encontrados. | R20 |
| P17 Modelo de estoque | Sob qualquer sequência de confirmar, pagar, cancelar e expirar sobre várias reservas, disponibilidade dos lotes, status e erros coincidem com o modelo de R15–R19 após cada operação. | R15–R19 |

**Ordem de verificação.** Quando mais de uma pré-condição falha, as implementações verificam na ordem
em que as regras as listam: em R7, status → evento ativo → quantidade → lote existe → lote do evento;
em R14/R15, status → reserva vazia → evento ativo → disponibilidade. P13, P14 e P17 usam essa ordem.

## Parâmetros dos geradores (iguais nos dois ecossistemas)

| Dado | Faixa |
| --- | --- |
| Preço do lote | 0 a 100 000 centavos |
| Quantidade total do lote | 1 a 50 |
| Lotes por evento | 1 a 4 |
| Itens por reserva | 1 a 5 |
| Quantidade por item | 1 a 10 |
| Cupom percentual | 1 a 100 |
| Cupom fixo | 1 a 50 000 centavos |
| Mínimo do cupom | 0 a 200 000 centavos |
| Máximo de desconto | ausente ou 1 a 50 000 centavos |
| Validade do cupom | data base ± 30 dias |
| Sequência de operações (P8) | 1 a 8 operações entre confirmar, pagar, cancelar, expirar, adicionar item |
| Tentativas por propriedade | 100 (no experimento: 10, 100 e 1000) |

Geradores adicionais da suíte forte:

| Dado | Faixa |
| --- | --- |
| Nome do evento (P10) | `""`, `"   "`, `"Show"` ou nulo (equiprováveis) |
| Capacidade do evento (P10) | −5 a 300 |
| Cadastro de lotes (P11) | capacidade 1 a 200; lote de outro evento 1 a 50; 1 a 6 lotes com preço −50 a 100 000 e total −3 a 80 |
| Cupom bruto (P12) | código `""`, `" "`, `"C1"` ou nulo; tipo PERCENTUAL (valor −5 a 110) ou FIXO (valor −5 a 60 000); mínimo −5 a 1000; máximo ausente (25%) ou −5 a 1000 |
| Item adicional (P13) | quantidade −3 a 10; lote do evento ou de outro evento; reserva CRIADA, CONFIRMADA ou CANCELADA |
| Operações sobre o evento (P14) | status do evento ATIVO, CANCELADO ou ENCERRADO; operação criar reserva, adicionar item ou confirmar; reserva com ou sem item |
| Status da reserva (P15) | os cinco status de R18; código existente ou inexistente |
| Id inexistente (P16) | uma das 14 operações; sufixo numérico 1000 a 9999 |
| Sequência de estoque (P17) | 2 a 4 reservas (itens como acima); 1 a 12 operações entre confirmar, pagar, cancelar e expirar |

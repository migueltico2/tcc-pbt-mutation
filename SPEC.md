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
| Tentativas por propriedade | 100 |

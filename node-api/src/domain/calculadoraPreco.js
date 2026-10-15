'use strict';

const { TipoCupom } = require('./modelos');

/** Regras de preço R8, R11, R12 e R13. Funções puras, sem estado. */

/** R8. itens: [{ precoCentavos, quantidade }] */
function subtotal(itens) {
  let soma = 0;
  for (const item of itens) {
    soma += item.precoCentavos * item.quantidade;
  }
  return soma;
}

/** R11, R12 e R13. cupom null representa ausência de cupom ou código inexistente. */
function desconto(cupom, sub, hoje) {
  if (cupom === null) {
    return 0;
  }
  if (hoje > cupom.validoAte) {
    return 0;
  }
  if (sub < cupom.minimoCentavos) {
    return 0;
  }
  let bruto;
  if (cupom.tipo === TipoCupom.PERCENTUAL) {
    bruto = Math.floor((sub * cupom.valor) / 100);
  } else {
    bruto = cupom.valor;
  }
  if (cupom.maximoDescontoCentavos !== null) {
    bruto = Math.min(bruto, cupom.maximoDescontoCentavos);
  }
  return Math.min(bruto, sub);
}

/** R13. */
function calcular(itens, cupom, hoje) {
  const sub = subtotal(itens);
  const desc = desconto(cupom, sub, hoje);
  return { subtotal: sub, desconto: desc, total: sub - desc };
}

module.exports = { subtotal, desconto, calcular };

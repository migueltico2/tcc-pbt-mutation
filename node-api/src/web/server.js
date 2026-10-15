'use strict';

const { criarApp } = require('./app');

const porta = Number(process.env.PORT || 3000);
criarApp().listen(porta, () => {
  console.log(`API de ingressos (Node.js/Express) em http://localhost:${porta}`);
});

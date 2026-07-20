// server.js
// Servidor Web: recebe requisições HTTP, aplica o sistema de mitigação
// (importado de mitigation.js) e expõe uma API de estatísticas.

const express = require('express');
const { blacklistMiddleware, rateLimiterMiddleware, getMitigationStats } = require('./mitigation');

const app = express();
const PORT = 3000;

// ==== CONTADORES GLOBAIS (do servidor, não da mitigação) ====
let totalRequests = 0;
let requestsThisSecond = 0;
let requestsLastSecond = 0;

// Atualiza a contagem de requisições por segundo a cada 1000ms
setInterval(() => {
  requestsLastSecond = requestsThisSecond;
  requestsThisSecond = 0;
}, 1000);

// ==== MIDDLEWARE: LOGGER / CONTADOR GLOBAL ====
function loggerMiddleware(req, res, next) {
  totalRequests++;
  requestsThisSecond++;
  next();
}

// ==== ROTAS ====

// Rota "alvo" - simula o serviço protegido que o atacante está tentando derrubar.
// Os middlewares de mitigação são aplicados só aqui (não globalmente), assim
// consultar /stats no dashboard não conta como tráfego de ataque.
app.get('/', blacklistMiddleware, rateLimiterMiddleware, loggerMiddleware, (req, res) => {
  res.json({ message: 'Requisição processada com sucesso' });
});

// Rota de estatísticas - consumida pelo dashboard via polling
app.get('/stats', (req, res) => {
  const mitigationStats = getMitigationStats();
  res.json({
    totalRequests,
    requestsPerSecond: requestsLastSecond,
    ...mitigationStats,
  });
});

app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);
  console.log(`Estatísticas em http://localhost:${PORT}/stats`);
});
// mitigation.js
// Sistema de Mitigação: rate limiting, blacklist de IPs e logs de eventos.
// Exporta os middlewares e o estado para o server.js usar.

// ==== CONFIGURAÇÕES ====
const RATE_LIMIT_WINDOW_MS = 5000;   // janela de tempo: 5 segundos
const RATE_LIMIT_MAX_REQUESTS = 10;  // máximo de requisições permitidas na janela
const BLACKLIST_DURATION_MS = 30000; // tempo que um IP fica bloqueado: 30 segundos

// ==== ESTADO EM MEMÓRIA ====
const requestLog = {};  // { ip: [timestamps das requisições recentes] }
const blacklist = {};   // { ip: timestamp de quando o bloqueio expira }
const events = [];      // histórico de eventos para o dashboard (log)

let blockedCount = 0;

// Adiciona um evento ao log (mantém só os últimos 50 para não crescer infinito)
function logEvent(message) {
  const timestamp = new Date().toLocaleTimeString('pt-BR');
  events.unshift(`[${timestamp}] ${message}`);
  if (events.length > 50) events.pop();
}

// Extrai o "IP" da requisição.
// Usamos o header X-Forwarded-For para simular múltiplos IPs vindos do
// attacker.js, já que localmente todo mundo teria o mesmo IP real.
function getClientIp(req) {
  return req.headers['x-forwarded-for'] || req.socket.remoteAddress;
}

// ==== MIDDLEWARE: BLACKLIST ====
// Verifica se o IP está bloqueado antes de deixar passar para as próximas etapas
function blacklistMiddleware(req, res, next) {
  const ip = getClientIp(req);
  const expiresAt = blacklist[ip];

  if (expiresAt) {
    if (Date.now() < expiresAt) {
      // Ainda bloqueado
      return res.status(403).json({ error: 'IP bloqueado temporariamente' });
    } else {
      // Bloqueio expirou, libera o IP
      delete blacklist[ip];
      logEvent(`IP ${ip} desbloqueado (tempo expirado)`);
    }
  }

  next();
}

// ==== MIDDLEWARE: RATE LIMITER ====
// Conta requisições por IP numa janela deslizante. Se exceder o limite,
// bloqueia o IP adicionando na blacklist.
function rateLimiterMiddleware(req, res, next) {
  const ip = getClientIp(req);
  const now = Date.now();

  if (!requestLog[ip]) requestLog[ip] = [];

  // Remove timestamps fora da janela de tempo
  requestLog[ip] = requestLog[ip].filter(
    (timestamp) => now - timestamp < RATE_LIMIT_WINDOW_MS
  );

  requestLog[ip].push(now);

  if (requestLog[ip].length > RATE_LIMIT_MAX_REQUESTS) {
    // Excedeu o limite: bloqueia o IP
    blacklist[ip] = now + BLACKLIST_DURATION_MS;
    blockedCount++;
    logEvent(`IP ${ip} BLOQUEADO por excesso de requisições (${requestLog[ip].length} em ${RATE_LIMIT_WINDOW_MS / 1000}s)`);
    delete requestLog[ip]; // limpa o histórico desse IP
    return res.status(429).json({ error: 'Muitas requisições. IP bloqueado.' });
  }

  next();
}

// Função auxiliar para o server.js montar a resposta de /stats
function getMitigationStats() {
  return {
    blockedIps: Object.keys(blacklist),
    blockedCount,
    attackDetected: Object.keys(blacklist).length > 0,
    events: events.slice(0, 20), // últimos 20 eventos
  };
}

module.exports = {
  blacklistMiddleware,
  rateLimiterMiddleware,
  getMitigationStats,
};
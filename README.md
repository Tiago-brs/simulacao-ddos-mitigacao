# Simulação de Ataques DDoS e Mecanismos de Mitigação

Projeto acadêmico de Segurança Computacional.

## Componentes
- `server.js` — servidor web, expõe rotas e a API de estatísticas
- `mitigation.js` — sistema de mitigação (rate limiting, blacklist de IPs, logs)
- `attacker.js` — simulador de ataque DDoS (múltiplos IPs simulados em paralelo)
- `dashboard.html` — painel de monitoramento em tempo real

## Como rodar
1. `npm install`
2. `node server.js` (deixe rodando)
3. Abra `dashboard.html` no navegador
4. Em outro terminal: `node attacker.js`



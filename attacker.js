// attacker.js
// Simulador de Ataque DDoS: dispara várias requisições simultâneas ao
// servidor, simulando N "clientes" (IPs falsos) enviando M requisições cada.

const http = require('http');

// ==== CONFIGURAÇÕES DO ATAQUE ====
const TARGET_HOST = 'localhost';
const TARGET_PORT = 3000;
const TARGET_PATH = '/';

const NUM_CLIENTS = 15;          // quantidade de "IPs" simulados
const REQUESTS_PER_CLIENT = 20;  // quantas requisições cada cliente dispara

// Gera um IP falso no formato 10.0.0.X, um por cliente simulado
function generateFakeIp(clientIndex) {
  return `10.0.0.${clientIndex + 1}`;
}

// Dispara uma única requisição HTTP, simulando o IP de origem via
// o header X-Forwarded-For (o server.js lê esse header como o "IP do cliente")
function sendRequest(fakeIp) {
  return new Promise((resolve) => {
    const options = {
      hostname: TARGET_HOST,
      port: TARGET_PORT,
      path: TARGET_PATH,
      method: 'GET',
      headers: {
        'X-Forwarded-For': fakeIp,
      },
    };

    const req = http.request(options, (res) => {
      resolve({ ip: fakeIp, status: res.statusCode });
    });

    req.on('error', (err) => {
      resolve({ ip: fakeIp, status: 'erro', error: err.message });
    });

    req.end();
  });
}

// Simula um "cliente" disparando várias requisições em sequência rápida
async function simulateClient(clientIndex) {
  const fakeIp = generateFakeIp(clientIndex);
  const results = [];

  for (let i = 0; i < REQUESTS_PER_CLIENT; i++) {
    const result = await sendRequest(fakeIp);
    results.push(result);
  }

  return results;
}

// Dispara todos os clientes ao mesmo tempo (concorrência real)
async function runAttack() {
  console.log(`Iniciando ataque simulado: ${NUM_CLIENTS} clientes x ${REQUESTS_PER_CLIENT} requisições cada`);
  console.log(`Alvo: http://${TARGET_HOST}:${TARGET_PORT}${TARGET_PATH}\n`);

  const startTime = Date.now();

  const clientPromises = [];
  for (let i = 0; i < NUM_CLIENTS; i++) {
    clientPromises.push(simulateClient(i));
  }

  const allResults = await Promise.all(clientPromises);
  const flatResults = allResults.flat();

  const elapsedSeconds = ((Date.now() - startTime) / 1000).toFixed(2);

  // Resumo por código de status
  const summary = {};
  flatResults.forEach((r) => {
    summary[r.status] = (summary[r.status] || 0) + 1;
  });

  console.log(`Ataque concluído em ${elapsedSeconds}s`);
  console.log(`Total de requisições enviadas: ${flatResults.length}`);
  console.log('Resumo por status:', summary); // retorna quantas respostas http teve de cada tipo que recebeu
  console.log('  200 = aceita | 429 = bloqueada pelo rate limiter | 403 = IP já banido');
}

runAttack();
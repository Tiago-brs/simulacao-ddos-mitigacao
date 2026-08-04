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

PAYLOAD_POST = {
    "origem": "botnet_simulada",
    "dados": "Olá!" * 2500  # envia 10000 caracteres
}


def gerar_ip_simulado(client_index: int) -> str:
    return f"127.0.0.{client_index + 2}"

# seção do menu CLI
def menu_cli():
    print("    Simulador de Ataque DDos - painel de controle")

    # tipo de requisição do ataque
    tipo_ataque = input("Tipo de requisição do ataque (GET ou POST) flood [padrão: POST]: ").strip().upper()
    if tipo_ataque not in ["GET", "POST"]:
        tipo_ataque = "POST"

    # quantidade de IPs simulados
    num_ips_str = input("Quantidade de IPs simulados [padrão: 1]: ").strip()
    num_ips = int(num_ips_str) if num_ips_str.isdigit() and int(num_ips_str) > 0 else 1

    # duração do ataque em segundos
    duracao_str = input("Duração do ataque em segundos [padrão: 10]: ").strip()
    duracao_atck = int(duracao_str) if duracao_str.isdigit() and int(duracao_str) > 0 else 10

    return tipo_ataque, num_ips, duracao_atck

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
async def simular_cliente_get(cliente_index: int, duracao_segundos: int) -> list:
    ip_origem = gerar_ip_simulado(cliente_index)
    resultados_list =[]
    tempo_fim = time.time() + duracao_segundos # define o tempo que o ataque vai rodar

    if IS_WINDOWS:
        # modo windows: cria o cliente HTTP normal, sem forçar placa de rede
        async with httpx.AsyncClient() as cliente:
            while time.time() < tempo_fim:
                resultado = await mandar_requisicao_get(cliente, ip_origem)
                resultados_list.append(resultado)
    else:
        # modo linux/mac: "local_address" força a saída do tráfego pelo IP real específico
        transport = httpx.AsyncHTTPTransport(local_address=ip_origem)
        async with httpx.AsyncClient(transport=transport) as cliente:
            while time.time() < tempo_fim:
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

async def simular_cliente_post(cliente_index: int, duracao_segundos: int) -> list:
    ip_origem = gerar_ip_simulado(cliente_index)
    resultados_list = []
    tempo_fim = time.time() + duracao_segundos

    if IS_WINDOWS:
        async with httpx.AsyncClient() as cliente:
            while time.time() < tempo_fim:
                resultado = await mandar_requisicao_post(cliente, ip_origem)
                resultados_list.append(resultado)
    else:
        transport = httpx.AsyncHTTPTransport(local_address=ip_origem)
        async with httpx.AsyncClient(transport=transport) as cliente:
            while time.time() < tempo_fim:
                resultado = await mandar_requisicao_post(cliente, ip_origem)
                resultados_list.append(resultado)

    return resultados_list

# execução do ataque
async def rodar_ataque():
    # chama o CLI para definir o ataque
    tipo_ataque, num_clientes, duracao_atck = menu_cli()

    print(f"Iniciando ataque simulado: {num_clientes} clientes durante {duracao_atck} segundos")
    print(f"Alvo: {URL_BASE}/produto/{{id}}\n")

    hora_inicio = time.time()

    # cria as tarefas, a função simular_cliente_get cria o cliente específico de cada IP
    # seleciona qual tipo de ataque vai simular
    if tipo_ataque == "POST":
        tasks = [simular_cliente_post(i, duracao_atck) for i in range(num_clientes)]
    else:
        tasks = [simular_cliente_get(i, duracao_atck) for i in range(num_clientes)]

    todos_resultados = await asyncio.gather(*tasks)

    # comprime a lista de listas em uma única lista
    flat_results = [resultado for resultados_cliente in todos_resultados for resultado in resultados_cliente]

    segundos_passado = round(time.time() - hora_inicio, 2)

    # resumo por código de status
    sumario = {}
    for r in flat_results:
        status = r["status"]
        sumario[status] = sumario.get(status, 0) + 1

    print(f"Ataque do tipo {tipo_ataque} concluído em {segundos_passado}s")
    print(f"Total de requisições enviadas: {len(flat_results)}")
    print("Resumo por status:", sumario)
    print("  200 = aceita | 429 = bloqueada pelo rate limiter | 403 = IP já banido")


if __name__ == "__main__":
    asyncio.run(rodar_ataque())
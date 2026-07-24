# simulador de ataque DDos dispara varis requisições simultaneas ao servidor
# simulando N cliente (usando IPs falsos) enviando M requisições cada

import asyncio
import time
import httpx

# configurações do ataque
HOST_ALVO = "localhost"
PORTA_ALVO = 3000
PATH_ALVO = "/"
URL_ALVO = f"http://{HOST_ALVO}:{PORTA_ALVO}{PATH_ALVO}"

NUM_CLIENTES = 15               # quantidade de ips simulados
REQUISICOES_POR_CLIENTE = 20    # quantidade de requisições por ip

def gerar_ip_falso(client_index: int) -> str:
    return f"10.0.0.{client_index + 1}"

# dispara apenas uma requisição HTTP simulando o ip de origem via o header X-Forwarded-For
# e o cliente pega o header e le como o "IP do cliente", 
# para simular diversos ips diferentes de forma fácil (TALVEZ USAR OUTRO MÉTODO PARA MULTIPLOS IPS)
async def mandar_requisicao(cliente: httpx.AsyncClient, fake_ip: str) -> dict:
    headers = {"X-Forwarded-For": fake_ip}

    try:
        response = await cliente.get(URL_ALVO, headers=headers)
        return {"ip": fake_ip, "status": response.status_code}
    except Exception as err:
        return {"ip": fake_ip, "status": "erro", "error": str(err)}

# simula um cliente disparando vária requisições me sequencia rápida
async def simular_cliente(cliente: httpx.AsyncClient, cliente_index: int) -> list:
    fake_ip = gerar_ip_falso(cliente_index)
    resultados_list =[]

    for _ in range(REQUISICOES_POR_CLIENTE):
        resultado = await mandar_requisicao(cliente, fake_ip)
        resultados_list.append(resultado)

    return resultados_list

async def rodar_ataque():
    print(f"Iniciando ataque simulado: {NUM_CLIENTES} clientes x {REQUISICOES_POR_CLIENTE} requisições cada")
    print(f"Alvo: {URL_ALVO}\n")

    hora_inicio = time.time()

    # usar httpx pra manter conexões otimizadas
    async with httpx.AsyncClient() as cliente:
        # cria as tarefas para todos os clientes rodarem em paralelo
        tasks = [simular_cliente(cliente, i) for i in range(NUM_CLIENTES)]

        todos_resultados = await asyncio.gather(*tasks)

    # comprime a lista de listas em uma única lista
    flat_results = [resultado for resultados_cliente in todos_resultados for resultado in resultados_cliente]

    segundos_passado = round(time.time() - hora_inicio, 2)

    # resumo por código de status
    sumario = {}
    for r in flat_results:
        status = r["status"]
        sumario[status] = sumario.get(status, 0) + 1

    print(f"Ataque concluído em {segundos_passado}s")
    print(f"Total de requisições enviadas: {len(flat_results)}")
    print("Resumo por status:", sumario)
    print("  200 = aceita | 429 = bloqueada pelo rate limiter | 403 = IP já banido")

    if __name__ == "__main__":
        asyncio.run(rodar_ataque())
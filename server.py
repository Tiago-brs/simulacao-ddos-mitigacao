from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import time

from mitigation import checar_blacklist, checar_rate_limiter, get_status_mitigacao, alternar_mitigacao
import random

# contadores globais do servidor
total_requisicoes = 0
requisicoes_segundo_atual = 0
requisicoes_ultimo_segundo = 0

# histórico de tempo de resposta medido pelo "usuário fantasma"
# guarda só os últimos N pontos, para o gráfico não crescer infinitamente
LIMITE_HISTORICO_LATENCIA = 60
historico_latencia = []  # cada item: {"timestamp": epoch_ms, "tempoRespostaMs": float, "sucesso": bool}

# configuração da rota "pesada" - simula uma operação real de aplicação
# (ex: consulta de produto que faz processamento e espera de I/O)
INTERVALO_USUARIO_FANTASMA_S = 0.5  # a cada quantos segundos o usuário fantasma faz uma requisição
TIMEOUT_USUARIO_FANTASMA_S = 3.0    # tempo máximo que o usuário fantasma espera por resposta

async def att_requisicoes_por_segundo():
    # global diz que é para alterar uma variavel definida fora da função
    global requisicoes_segundo_atual, requisicoes_ultimo_segundo

    # atualiza a contagem de requisições a cada segundo, colocando a thread de contagem pra dormir por 1 segundo
    while True:
        requisicoes_ultimo_segundo = requisicoes_segundo_atual
        requisicoes_segundo_atual = 0
        await asyncio.sleep(1)

# "usuário fantasma": simula um usuário legítimo usando o sistema continuamente,
# medindo o tempo de resposta da rota pesada. É essa métrica que mostra o impacto
# real do ataque do ponto de vista de quem usa o serviço - não só contagem de bloqueios.
async def usuario_fantasma():
    import httpx

    async with httpx.AsyncClient() as cliente:
        while True:
            inicio = time.time()
            sucesso = True

            try:
                await cliente.get(
                    f"http://127.0.0.1:{PORTA}/produto/{random.randint(1, 1000)}",
                    timeout=TIMEOUT_USUARIO_FANTASMA_S,
                )
            except Exception:
                # timeout ou conexão recusada = servidor não conseguiu atender a tempo
                sucesso = False

            tempo_resposta_ms = round((time.time() - inicio) * 1000, 1)

            historico_latencia.append({
                "timestamp": int(time.time() * 1000),
                "tempoRespostaMs": tempo_resposta_ms,
                "sucesso": sucesso,
            })

            # mantém só os últimos N pontos no histórico
            if len(historico_latencia) > LIMITE_HISTORICO_LATENCIA:
                historico_latencia.pop(0)

            await asyncio.sleep(INTERVALO_USUARIO_FANTASMA_S)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # o que está antes de yield roda quando o servidor liga
    # cria thread para contar as requisições com uma tarefa (task)
    task_contador = asyncio.create_task(att_requisicoes_por_segundo())
    # cria a task do usuário fantasma, que mede a latência continuamente em background
    task_usuario_fantasma = asyncio.create_task(usuario_fantasma())

    yield   # servidor roda nesta fase

    task_contador.cancel()          # após yield roda quando o servidor desliga
    task_usuario_fantasma.cancel()

# cria o app com lifespan
app = FastAPI(lifespan=lifespan)
PORTA = 3000

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # colocar as URLs do front deploy e localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# contador global das requisições com dependencia logger
async def dependencia_logger():
    global requisicoes_segundo_atual, total_requisicoes
    total_requisicoes += 1
    requisicoes_segundo_atual += 1

# ROTAS PARA TESTE DE ATAQUE

# usa depends pra fazer a contagem  de requisições, que roda antes da requisição em si
# além de também fazer as verificações de mitigação
@app.get("/", dependencies=[ Depends(dependencia_logger), Depends(checar_blacklist), Depends(checar_rate_limiter)])
async def raiz_get():
    return {"message": "Requisição processada com sucesso"}

# rota post para o ataque POST Flood
@app.post("/", dependencies=[ Depends(dependencia_logger), Depends(checar_blacklist), Depends(checar_rate_limiter)])
async def raiz_post(request: Request):
    # força o servidor a ler o pyload JSON, simulando uma leitura real de uma requisição de login
    try:
        body = await request.json()
    except Exception:
        pass

    return {"message": "POST processado com sucesso"}


# rota "pesada" - simula uma operação real de aplicação (ex: busca de produto
# com consulta/processamento), diferente das rotas acima que respondem "de graça".
# É essa rota que o usuário fantasma consulta continuamente, e é nela que o
# impacto de um ataque aparece de verdade em tempo de resposta.
@app.get("/produto/{produto_id}", dependencies=[Depends(dependencia_logger), Depends(checar_blacklist), Depends(checar_rate_limiter)])
async def buscar_produto(produto_id: int):
    # simula espera de I/O, como uma consulta a banco de dados
    await asyncio.sleep(0.05)

    # simula processamento de CPU real (não é só devolver um JSON pronto)
    resultado = sum(i * i for i in range(50_000))

    return {"produto_id": produto_id, "checksum": resultado}


# endpoint que liga/desliga a mitigação em tempo real, usado pelo botão do dashboard
# permite comparar o mesmo servidor, sob a mesma carga, com e sem defesa ativa
@app.post("/mitigacao/toggle")
async def toggle_mitigacao():
    novo_estado = alternar_mitigacao()
    return {"mitigacaoAtiva": novo_estado}


# rota de estaticas para usar no dashboard
@app.get("/stats")
async def status():
    status_mitigacao = get_status_mitigacao()

    return {
        "totalRequests": total_requisicoes,
        "requestsPerSecond": requisicoes_ultimo_segundo,
        "latencyHistory": historico_latencia,
        **status_mitigacao
        # ** é para desempacotar o dicionario de valores que recebeu, colocando um por um, 
        # colocando por exemplo: "blockedCount": 5, E: "attackDetected": true
    }

# pra rodar com "python server.py"
if __name__ == "__main__":
    import uvicorn
    print(f"Servidor rodando em http://localhost:{PORTA}")
    print(f"Estatísticas em http://localhost:{PORTA}/stats")
    uvicorn.run("server:app", host="0.0.0.0", port=PORTA, reload=True, limit_concurrency=150)
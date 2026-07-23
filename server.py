from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from mitigation import checar_blacklist, checar_rate_limiter, get_status_mitigacao

# contadores globais do servidor
total_requisicoes = 0
requisicoes_segundo_atual = 0
requisicoes_ultimo_segundo = 0

async def att_requisicoes_por_segundo():
    # global diz que é para alterar uma variavel definida fora da função
    global requisicoes_segundo_atual, requisicoes_ultimo_segundo

    # atualiza a contagem de requisições a cada segundo, colocando a thread de contagem pra dormir por 1 segundo
    while True:
        requisicoes_ultimo_segundo = requisicoes_segundo_atual
        requisicoes_segundo_atual = 0
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # o que está antes de yield roda quando o servidor liga
    # cria thread para contar as requisições com uma tarefa (task)
    task = asyncio.create_task(att_requisicoes_por_segundo())

    yield   # servidor roda nesta fase

    task.cancel()   # após yield roda quando o servidor desliga

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

# ROTAS

# usa depends pra fazer a contagem  de requisições, que roda antes da requisição em si
# além de também fazer as verificações de mitigação
@app.get("/", dependencies=[Depends(checar_blacklist), Depends(checar_rate_limiter), Depends(dependencia_logger)])
async def raiz():
    return {"message": "Requisição processada com sucesso"}

# rota de estaticas para usar no dashboard
@app.get("/stats")
async def status():
    status_mitigacao = get_status_mitigacao()

    return {
        "totalRequests": total_requisicoes,
        "requestsPerSecond": requisicoes_ultimo_segundo,
        **status_mitigacao
        # ** é para desempacotar o dicionario de valores que recebeu, colocando um por um, 
        # colocando por exemplo: "blockedCount": 5, E: "attackDetected": true
    }

# pra rodar com "python server.py"
if __name__ == "__main__":
    import uvicorn
    print(f"Servidor rodando em http://localhost:{PORTA}")
    print(f"Estatísticas em http://localhost:{PORTA}/stats")
    uvicorn.run("server:app", host="0.0.0.0", port=PORTA, reload=True)
# Sistema de mitigação Ver.1: rate limiting, blacklist de ip e logs de eventos

import time
from datetime import datetime
from fastapi import Request, HTTPException, status

# configurações das mitigações
# janela rate limiting e duração blacklist em milisegundo
JANELA_RATE_LIMITING_MS = 5000  # 5 segundos
REQUISICOES_MAX_RATE_LIMITING = 10
DURACAO_BLACKLIST_MS = 30000    # 30 segundos

# estados em memoria
log_requisicoes = {}    # { ip: [timestamps das requisições recentes] }
blacklist = {}          # { ip: timestamp de quando o bloqueio expira }
eventos = []            # histórico de eventos para o dashboard (log)

count_bloqueios = 0

# estado do "interruptor" de mitigação - controla se as defesas estão ativas
# usado para comparar o comportamento do servidor com e sem mitigação, ao vivo
mitigacao_ativa = True

def alternar_mitigacao() -> bool:
    """Inverte o estado da mitigação (liga/desliga) e retorna o novo estado."""
    global mitigacao_ativa
    mitigacao_ativa = not mitigacao_ativa
    log_eventos(f"Mitigação {'ATIVADA' if mitigacao_ativa else 'DESATIVADA'} manualmente")
    return mitigacao_ativa

# adiciona os eventos ao log, com limite de mostrar os 100 ultimos
LIMITE_LOG = 100
def log_eventos(message: str):
    horario = datetime.now().strftime("%H:%M:%S")
    eventos.append(f"[{horario}] {message}")    # adicona ao final da lista

    if len(eventos) > LIMITE_LOG:   # deleta o ultimo item do log caso chegue no limite
        eventos.pop(0)

# extrai o IP da rquisição
# usando header "X-Forwarded-For" pra simular múltiplos IPs vindos do attacker, 
# já que localmente todo mundo teria o mesmo IP real.
def get_ip_cliente(request: Request):
    ip_real = request.client.host

    # se o sistema for windows, todas as requisições locais chegam como 127.0.0.1
    # por conta disso é usado o header "X-Forwarded-For" pra simular varios atacantes
    if ip_real == "127.0.0.1":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded

    # se for linux/mac, os pacotes vão com IPs reais. então retorna o IP real
    return ip_real

# dependencia blacklist 
# verifica se o ip está bloqueado antes de continuar a requisição
async def checar_blacklist(request: Request):
    # se a mitigação está desligada, não verifica blacklist - deixa tudo passar
    if not mitigacao_ativa:
        return

    ip = get_ip_cliente(request)
    # hora que o ip expira e sai da blacklist
    expira_em = blacklist.get(ip)

    hora_atual = time.time() * 1000 # converte o tempo para milisegundos

    # se o ip está na blacklist, verifica o tempo para expirar
    if expira_em:
        if hora_atual < expira_em:
            # se o ip esta bloqueado, sobe uma exceção HTTP e a retorna
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="IP bloqueado temporariamente")
        else:
            # se o bloqueio expirou, libera o ip
            del blacklist[ip]
            log_eventos(f"IP {ip} desbloqueado (tempo expirado)")

# dependencia rate limiter
# conta as requisições por um IP em uma janela de tempo
# bloqueia e o adiciona a blacklist se exceder o limite de requisições
async def checar_rate_limiter(request: Request):
    global count_bloqueios

    # se a mitigação está desligada, não verifica rate limit - deixa tudo passar
    if not mitigacao_ativa:
        return

    ip = get_ip_cliente(request)
    hora_atual = time.time() * 1000 # converte o tempo para milisegundos

    # salva o ip no log de requisições pela primeira vez
    if ip not in log_requisicoes:
        log_requisicoes[ip] = []

    # remove os horarios fora da janela de tempo com List comprehension do python
    log_requisicoes[ip] = [horario for horario in log_requisicoes[ip] if hora_atual - horario < JANELA_RATE_LIMITING_MS]

    log_requisicoes[ip].append(hora_atual)

    if len(log_requisicoes[ip]) > REQUISICOES_MAX_RATE_LIMITING:
        # bloqueia o ip se exceder o limite de requisições
        blacklist[ip] = hora_atual + DURACAO_BLACKLIST_MS
        count_bloqueios += 1
        # cria o evento para o log do dashboard
        log_eventos(f"IP {ip} BLOQUEADO por excesso de requisições ({len(log_requisicoes[ip])} em {JANELA_RATE_LIMITING_MS // 1000}s)")

        # deleta o log de requisições desse ip (pois foi pra blacklist) e sobe a exceção http
        del log_requisicoes[ip]
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitas requisições. IP bloqueado.")

# função auxiliar para montar as respostas de /stats
def get_status_mitigacao():
    hora_atual = time.time() * 1000 # converte o tempo para milisegundos

    # lista os ips que ja passaram do tempo de expiração
    ips_expirados = [ip for ip, expira_em in blacklist.items() if hora_atual >= expira_em]

    # limpa a blacklist antes de mandar os dados pro dashboard
    for ip in ips_expirados:
        del blacklist[ip]
        log_eventos(f"IP {ip} desbloqueado (tempo expirado)")

    return {
        "blockedIps": list(blacklist.keys()),
        "blockedCount": count_bloqueios,
        "attackDetected": len(blacklist) > 0,
        "events": eventos[-LIMITE_LOG:], # últimos 20 eventos
        "mitigacaoAtiva": mitigacao_ativa
    }
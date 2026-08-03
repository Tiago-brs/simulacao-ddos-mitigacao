# Simulação de Ataques DDoS e Mecanismos de Mitigação

Projeto acadêmico de Segurança Computacional.

## Componentes
- `server.py` — servidor web, expõe rotas e a API de estatísticas
- `mitigation.py` — sistema de mitigação (rate limiting, blacklist de IPs, logs)
- `attacker.py` — simulador de ataque DDoS (múltiplos IPs simulados em paralelo)
- `dashboard.html` — painel de monitoramento em tempo real (HTML+CSS com JavaScript imbutido)

## Como rodar
1. Instalar e criar ambiente virtual python (Usar python 3.13 ou mais recente)
    - Instalar python no seu sistema operacional
    - Criar ambiente virtual. Windows: `python -m venv .venv`. Linux ou Mac: `python3 -m venv .venv` (ou `python3.X`. X sendo a versão escolhida)
2. Ativar ambiente vitual python 
    - Windows: `.venv\Scripts\activate`
    - Linux: `source .venv/bin/activate`
3. Baixar bibliotecas python necessarias:
    - `pip install -r requirements.txt`
4. Rodar servidor simulado: `python3 server.py`
5. Abrir `dashboard.html` no navegador
6. Em outro terminal, rode o ataque: `python3 attacker.py`

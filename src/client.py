import socket
import sys
import time

from functions import *

def test():
    pass

def connect_server(host, port):
    # create socket
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as error:
        print(str(error))
        sys.exit(0)

    # connect server socket
    while True:
        try:
            client_socket.connect((host, port))
            break
        except socket.error:
            print('Failed to connect. Trying again...')

            SLEEP_TIME = 2
            time.sleep(SLEEP_TIME)

    # confirm msg from server
    received_packet = receive(client_socket)
    if not received_packet:
        print('Server did not response')
    else:
        print(received_packet.decode('utf-8'))

    # start testing
    while True:
        to_send_msg = input('Type message: ')
        send(client_socket, to_send_msg.encode())

        received_packet = receive(client_socket)
        if not received_packet:
            print('Server did not response')
        else:
            print(received_packet.decode('utf-8'))


# start
HOST = '127.0.0.1'
PORT = 2808

connect_server(HOST, PORT)

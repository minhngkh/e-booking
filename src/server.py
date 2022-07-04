import socket
import sys

from threading import Thread

from functions import *


def validate_infos(username, password):
    pass


def handle_client_img(client_socket, address):
    send(client_socket, 'Successfully connected to server'.encode())

    while True:
        print('Receiving...')
        received_packet = receive(client_socket)
        if not received_packet:
            break

        try:
            save_img(received_packet, 'test.png')
            print('Image received')
        except Exception as e:
            print(e)

    client_socket.close()
    print(f'{address} disconnected')


def handle_client_login(client_socket, address):
    # send confirm message
    send(client_socket, 'Successfully connected to server'.encode())

    # waiting for packets as long as the connection is not terminated
    while True:
        try:
            received_packet = receive(client_socket)

            # connection is terminated, get out of the loop
            if not received_packet:
                break

            # print received content
            response = 'Server received: "{}"'.format(received_packet.decode('utf-8'))
            print(response)
        except Exception as e:
            print(e)
            continue

    # close the connection
    client_socket.close()
    print(f'{address} disconnected')


def accept_incoming_connections(server_socket):
    '''
    Each client connected will be handled in a different thread, so server can process multiple one at a time
    '''

    while True:
        # accept connection
        client_socket, address = server_socket.accept()
        print(f'{address[0]}:{address[1]} connected')

        # create a new thread to put in
        #curr_thread = Thread(target=handle_client_login, args=(client_socket, address))
        curr_thread = Thread(target=handle_client_img, args=(client_socket, address))
        curr_thread.start()


def stop_server(server_socket):
    '''
    Stop the server whenever user types 'q' or 'quit'
    '''

    print('Type \'q\' or \'quit\' to stop the server')

    while input() not in ('q', 'quit'):
        pass

    server_socket.close()


def start_server(host, port):
    # create and bind socket
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
    except socket.error as error:
        print(str(error))
        sys.exit(0)

    # start listening
    server_socket.listen(MAX_CLIENTS)
    print(f'Server is listening on port {port}')

    # create a thread dedicated to accepting connections
    Thread(daemon=True, target=accept_incoming_connections, args=(server_socket,)).start()

    return server_socket


# start
HOST = ''
PORT = 2808
MAX_CLIENTS = 5

server_socket = start_server(HOST, PORT)

stop_server(server_socket)

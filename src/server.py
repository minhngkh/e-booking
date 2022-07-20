import socket
import sys
import pickle

from threading import Thread

from functions import *
import database as db

# global vars
MAX_CLIENTS = 5
DB_PATH = 'data/db.sqlite'
DEFAULT_IMG_SIZE = 400


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


def handle_search(client_socket, address, request):
    # request contains start_date and end_date
    hotel, start_date, end_date = (request.get(key) for key in ('hotel', 'start_date', 'end_date'))

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to get list of hotels
    get_query = f"""
    SELECT
        room_types.id,
        room_types.name,
        room_types.description,
        room_types.price,
        (room_types.total_rooms -
        SUM(CASE
                WHEN start_date BETWEEN date('{start_date}') AND date('{end_date}', '-1 day')
                OR end_date BETWEEN date('{start_date}', '+1 day') AND date('{end_date}')
                THEN number_rooms
                ELSE 0
            END)
        ) as rooms_left,
        room_types.image
    FROM room_types
    LEFT JOIN reserved_rooms ON reserved_rooms.room_type_id = room_types.id
    INNER JOIN hotels ON hotels.id = room_types.hotel_id
    WHERE room_types.hotel_id = '{hotel}'
    OR hotels.name = '{hotel}' COLLATE NOCASE
    GROUP BY room_types.id
    """

    room_types = [list(tup) for tup in db.execute_query(db_connection, get_query, True)]

    # when server respond nothing
    if not room_types:
        send(client_socket, pickle.dumps(Packet('fail')))
        print(f'{address} : hotel not found')
        return

    for room_type in room_types:
        # open file in binary stream & resize it before sending
        image_path = room_type[5]
        img = Image.open(image_path)
        bin_img = img_to_bin(img)
        resized_bin_img = img_to_bin(img, DEFAULT_IMG_SIZE)
        img.close()

        room_type[5] = resized_bin_img

    send(client_socket, pickle.dumps(Packet('success', room_types)))
    print(f'{address} : search successful')


def handle_list_hotels(client_socket, address, request=None):
    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to get list of hotels
    list_query = f"""
    SELECT id, name
    FROM hotels
    """

    hotels = db.execute_query(db_connection, list_query, True)
    send(client_socket, pickle.dumps(Packet('success', hotels)))
    print(f'{address} : list of hotels responded')


def handle_client_register(client_socket, address, request):
    # request contains username, password, card_number
    username, password, card_number = (request.get(key) for key in ('username', 'password', 'card_number'))

    # validate format
    if not (len(username) >= 5 and username.isalnum() and
            len(password) >= 3 and
            len(card_number) == 10 and card_number.isdecimal()):
        send(client_socket, pickle.dumps(Packet('fail')))
        print(f'{address} : register failed')

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # find if register information is already in database
    find_query = f"""
    SELECT EXISTS(
        SELECT 1
        FROM users
        WHERE username = '{username}'
        LIMIT 1
        )
    """

    # the query will return [(1,)] if info is found in database, otherwise [(0,)]
    if db.execute_query(db_connection, find_query, True)[0][0] == 0:
        # add new register info to database
        insert_query = f"""
            INSERT INTO users (username, password, card_number)
            VALUES ('{username}', '{password}', '{card_number}')
            """
        db.execute_query(db_connection, insert_query)

        send(client_socket, pickle.dumps(Packet('success')))
        print(f'{address} : register successful')

        return

    send(client_socket, pickle.dumps(Packet('fail')))
    print(f'{address} : register failed')


def handle_client_login(client_socket, address, content):
    # request contains username, password
    username, password = (content.get(key) for key in ('username', 'password'))

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # validate login information
    find_query = f"""
    SELECT EXISTS(
        SELECT 1
        FROM users
        WHERE (username, password) = ('{username}', '{password}')
        LIMIT 1
        )
    """

    # the query will return [(1,)] if login info is found in database, otherwise [(0,)]
    if db.execute_query(db_connection, find_query, True)[0][0] == 1:
        send(client_socket, pickle.dumps(Packet('success')))
        print(f'{address} : login successful')

        return

    send(client_socket, pickle.dumps(Packet('fail')))
    print(f'{address} : login failed')


VALID_REQUESTS = {'login': handle_client_login,
                  'register': handle_client_register,
                  'list: hotels': handle_list_hotels,
                  'search': handle_search}


def handle_client(client_socket, address):
    # send confirm message
    send(client_socket, 'Successfully connected to server'.encode())

    # waiting for packets as long as the connection is not terminated
    while True:
        try:
            received_packet = receive(client_socket)

            # connection is terminated, get out of the loop
            if not received_packet:
                break

            # validate request header
            request = pickle.loads(received_packet)
            func = VALID_REQUESTS.get(request.header)

            if func:
                print(f'{address} : requested \'{request.header}\'')
                func(client_socket, address, request.content)
            else:
                raise Exception('Invalid request')

        except Exception as e:
            print(f'{address} : {e}')
            send(client_socket, pickle.dumps(Packet('fail')))

    # close the connection
    client_socket.close()
    print(f'{address} : disconnected')


def accept_incoming_connections(server_socket):
    '''
    Each client connected will be handled in a different thread, so server can process multiple one at a time
    '''

    while True:
        # accept connection
        client_socket, address = server_socket.accept()
        address = f'{address[0]}:{address[1]}'

        print(f'{address} : connected')

        # create a new thread to put in
        curr_thread = Thread(target=handle_client, args=(client_socket, address))
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
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

server_socket = start_server(HOST, PORT)

stop_server(server_socket)

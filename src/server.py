import socket
import sys
import pickle
import time
from datetime import datetime, timedelta

from threading import Thread

from functions import *
import database as db

# global vars
MAX_CLIENTS = 5
DB_PATH = 'data/db.sqlite'
DEFAULT_IMG_SIZE = 400


def handle_client_cancel(client_socket, address, request, username=None):
    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to search for date
    get_query = f"""
    SELECT time
    FROM reservations
    WHERE id = '{request}'
    """

    # validate date and time:
    created_date = db.execute_query(db_connection, get_query, True)[0][0]

    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    cur_date = datetime.now()
    created_date = datetime.strptime(created_date, TIME_FORMAT)

    if created_date + timedelta(hours=24) < cur_date:
        raise Exception('Cancel failed')

    # create query to get list of reservations
    del_query = f"""
    DELETE FROM reservations
    WHERE id = '{request}'
    """

    db.execute_query(db_connection, del_query)

    send(client_socket, pickle.dumps(Packet('success')))
    print(f'{address} : Cancel successful')


def handle_client_list_reservations(client_socket, address, request, username):
    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to get list of reservations
    get_query = f"""
    SELECT
        id, time, notes
    FROM reservations
    WHERE username = '{username[0]}'
    """

    reservations = db.execute_query(db_connection, get_query, True)

    did = False
    hotel_name = start_date = end_date = None
    data = []
    for reservation_id, date, notes in reservations:
        # create query to get list of reserved rooms
        get_query = f"""
        SELECT
            hotels.name,
            room_types.name,
            reserved_rooms.price,
            reserved_rooms.number_rooms,
            reserved_rooms.start_date,
            reserved_rooms.end_date
        FROM reserved_rooms
        INNER JOIN room_types ON room_types.id = reserved_rooms.room_type_id
        INNER JOIN hotels ON hotels.id = room_types.hotel_id
        WHERE reservation_id = '{reservation_id}'
        """

        cur_data = db.execute_query(db_connection, get_query, True)

        if not did:
            hotel_name = cur_data[0][0]
            start_date = cur_data[0][4]
            end_date = cur_data[0][5]

        # only send necessary data
        data.append({'reservation_id': reservation_id,
                     'date': date,
                     'hotel_name': hotel_name,
                     'start_date': start_date,
                     'end_date': end_date,
                     'notes': notes,
                     'rooms_info': [room[1:4] for room in cur_data]})

    send(client_socket, pickle.dumps(Packet('success', data)))
    print(f'{address} : Get reservations successful')


def handle_client_reserve(client_socket, address, request, username):
    # request contains data, start_date and end_date
    # data contains list of room type id and number of rooms to be reserved
    data, hotel_id, start_date, end_date, notes = (request.get(key)
                                                   for key in ('data', 'hotel_id', 'start_date', 'end_date', 'notes'))

    # validate date and time:
    TIME_FORMAT = '%Y-%m-%d'
    cur_date = time.strftime(TIME_FORMAT, time.localtime())
    cur_date = time.strptime(cur_date, TIME_FORMAT)

    if (time.strptime(start_date, TIME_FORMAT) < cur_date or
            time.strptime(start_date, TIME_FORMAT) >= time.strptime(end_date, TIME_FORMAT)):
        raise Exception('Invalid date(s)')

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to insert reservation
    insert_query = f"""
    INSERT INTO reservations (time, username, notes)
    VALUES ('{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}', '{username[0]}', '{notes}')
    """

    row_id = db.execute_query(db_connection, insert_query)

    # create query to get reservation id
    get_query = f"""
        SELECT id
        FROM reservations
        WHERE rowid = '{row_id}'
    """

    reservation_id = db.execute_query(db_connection, get_query, True)[0][0]

    for room_type_id, number_rooms in data:
        # create query to get price
        get_query = f"""
            SELECT price
            FROM room_types
            WHERE id = {room_type_id}
        """

        price = db.execute_query(db_connection, get_query, True)[0][0]

        # create query to insert reserved room
        insert_query = f"""
            INSERT INTO reserved_rooms 
            (room_type_id, reservation_id, number_rooms, price, start_date, end_date)
            VALUES ({room_type_id}, {reservation_id}, {number_rooms}, '{price}', '{start_date}', '{end_date}')
        """

        db.execute_query(db_connection, insert_query)

    send(client_socket, pickle.dumps(Packet('success')))
    print(f'{address} : Reserve successful')


def handle_simple_search(client_socket, address, request, username=None):
    # request contains start_date and end_date
    hotel, start_date, end_date = (request.get(key) for key in ('hotel', 'start_date', 'end_date'))

    # validate date and time:
    TIME_FORMAT = '%Y-%m-%d'
    cur_date = time.strftime(TIME_FORMAT, time.localtime())

    if (time.strptime(start_date, TIME_FORMAT) < time.strptime(cur_date, TIME_FORMAT) or
            time.strptime(start_date, TIME_FORMAT) >= time.strptime(end_date, TIME_FORMAT)):
        raise Exception('Invalid date(s)')

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to get hotel name and id
    validate_query = f"""
    SELECT
        id, name
    FROM hotels
    WHERE id = '{hotel}'
    OR name = '{hotel}' COLLATE NOCASE
    """

    result = db.execute_query(db_connection, validate_query, True)

    if not result:
        raise Exception('Hotel not found')

    hotel_id, hotel_name = result[0]

    # create query to get list of hotels
    get_query = f"""
    SELECT
        room_types.id,
        room_types.name,
        room_types.price,
        (room_types.total_rooms -
        SUM(CASE
                WHEN start_date BETWEEN date('{start_date}') AND date('{end_date}', '-1 day')
                OR end_date BETWEEN date('{start_date}', '+1 day') AND date('{end_date}')
                THEN number_rooms
                ELSE 0
            END)
        ) as rooms_left
    FROM room_types
    LEFT JOIN reserved_rooms ON reserved_rooms.room_type_id = room_types.id
    WHERE room_types.hotel_id = {hotel_id}
    GROUP BY room_types.id
    """

    room_types = db.execute_query(db_connection, get_query, True)

    send(client_socket, pickle.dumps(Packet('success', {'data': room_types,
                                                        'hotel_id': hotel_id,
                                                        'hotel_name': hotel_name})))
    print(f'{address} : Simple search successful')


def handle_search(client_socket, address, request, username=None):
    # request contains start_date and end_date
    hotel, start_date, end_date = (request.get(key) for key in ('hotel', 'start_date', 'end_date'))

    # validate date and time:
    TIME_FORMAT = '%Y-%m-%d'
    cur_date = time.strftime(TIME_FORMAT, time.localtime())

    if (time.strptime(start_date, TIME_FORMAT) < time.strptime(cur_date, TIME_FORMAT) or
            time.strptime(start_date, TIME_FORMAT) >= time.strptime(end_date, TIME_FORMAT)):
        raise Exception('Invalid date(s)')

    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # create query to get hotel name and id
    validate_query = f"""
    SELECT
        id, name
    FROM hotels
    WHERE id = '{hotel}'
    OR name = '{hotel}' COLLATE NOCASE
    """

    result = db.execute_query(db_connection, validate_query, True)

    if not result:
        raise Exception('Hotel not found')

    hotel_id, hotel_name = result[0]

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
    WHERE room_types.hotel_id = {hotel_id}
    GROUP BY room_types.id
    """

    # convert returned tuple to list
    room_types = [list(tup) for tup in db.execute_query(db_connection, get_query, True)]

    # replace image path with binary image
    for room_type in room_types:
        # open file in binary stream & resize it before sending
        image_path = room_type[5]
        img = Image.open(image_path)
        bin_img = img_to_bin(img)
        resized_bin_img = img_to_bin(img, DEFAULT_IMG_SIZE)
        img.close()

        room_type[5] = resized_bin_img

    send(client_socket, pickle.dumps(Packet('success', {'data': room_types,
                                                        'hotel_id': hotel_id,
                                                        'hotel_name': hotel_name})))
    print(f'{address} : Search successful')


def handle_list_hotels(client_socket, address, request=None, username=None):
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
    print(f'{address} : List of hotels responded')


def handle_client_register(client_socket, address, request, username=None):
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
    if db.execute_query(db_connection, find_query, True)[0][0] == 1:
        raise Exception('Register failed')

    # add new register info to database
    insert_query = f"""
        INSERT INTO users (username, password, card_number)
        VALUES ('{username}', '{password}', '{card_number}')
        """
    db.execute_query(db_connection, insert_query)

    send(client_socket, pickle.dumps(Packet('success')))
    print(f'{address} : Register successful')

    return


def handle_client_login(client_socket, address, content, username_glob):
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
    if db.execute_query(db_connection, find_query, True)[0][0] == 0:
        raise Exception('Login failed')

    send(client_socket, pickle.dumps(Packet('success')))
    print(f'{address} : Login successful')

    username_glob[0] = username


VALID_REQUESTS = {'login': handle_client_login,
                  'register': handle_client_register,
                  'list: hotels': handle_list_hotels,
                  'search': handle_search,
                  'simple search': handle_simple_search,
                  'reserve': handle_client_reserve,
                  'list: reservations': handle_client_list_reservations,
                  'cancel': handle_client_cancel}


def handle_client(client_socket, address):
    # send confirm message
    send(client_socket, 'Successfully connected to server'.encode())

    # waiting for packets as long as the connection is not terminated
    USERNAME = [None]

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

                # can't request anything other than login and register when access has not been granted
                if not USERNAME[0] and request.header not in ('login', 'register'):
                    raise Exception('Invalid access')

                func(client_socket, address, request.content, USERNAME)
            else:
                raise Exception('Invalid request')

        except Exception as e:
            print(f'{address} : {e}')
            send(client_socket, pickle.dumps(Packet('fail', e)))

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
        # Configure to free port after server closed
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

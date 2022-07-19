import PySimpleGUI as sg
import socket
import sys
import time
import pickle

from PIL import Image

from functions import *

sg.theme('Dark Grey 9')
sg.set_options(font=('Lucida Console', 12))
TITLE = 'E-Booking'
DEFAULT_IMG_SIZE = 300


def blank_line():
    return sg.Text(font='_ 1')


def align(layout, mode='both'):
    if mode == 'both':
        return [
            [sg.VPush()],
            [sg.Push(), sg.Column(layout), sg.Push()],
            [sg.VPush()]
        ]
    if mode == 'vertical':
        return [
            [sg.VPush()],
            [sg.Column(layout)],
            [sg.VPush()]
        ]
    if mode == 'horizontal':
        return [
            [sg.Push(), sg.Column(layout), sg.Push()]
        ]


def collapse(layout, key, visible):
    '''
    Helper function that creates a Column that can be later made hidden, thus appearing "collapsed"
    :param layout: The layout for the section
    :param key: Key used to make this section visible / invisible
    :param visible: visible determines if section is rendered visible or invisible on initialization
    :return: A pinned column that can be placed directly into your layout
    :rtype: sg.pin
    '''

    return sg.pin(sg.Column(layout, key=key, visible=visible, pad=(0, 0)))


def popup_window(text, button='OK'):
    '''
        [TEXT]
        [BUTTON:OK]
    '''

    layout = [
        [sg.Text(text)],
        [sg.Column([[sg.Button(button)]], justification='center')]
    ]

    window = sg.Window(TITLE, layout, keep_on_top=True)

    while True:
        event, values = window.read()

        # when user presses close button
        if event == sg.WIN_CLOSED or event == button:
            break

    window.close()


def image_window(sock):
    '''
    Path [INPUT:PATH] [BUTTON:BROWSE]
        [IMAGE]
    [ERROR]
    [BUTTON:SUBMIT] [BUTTON:CLOSE]

    '''
    extensions_allowed = (('IMAGE files', '*.png *.jpg *.jpeg'),
                          ('ALL files', '*.*'))

    image = sg.Image(key='-IMG-')
    image_center = [[sg.Column([[image]], justification='center')]]

    error = [[sg.Text(font='_ 9 italic', key='-ERROR-')]]

    layout = [
        [sg.Text('Path:'), sg.In(key='-BROWSE-', enable_events=True), sg.FileBrowse(file_types=extensions_allowed)],
        [collapse(image_center, key='sec_img', visible=False)],
        [collapse(error, key='sec_error', visible=False)],
        [sg.Button('Submit'), sg.Button('Close')]]

    window = sg.Window(TITLE, layout)

    toggle_sec_error = toggle_sec_img = file_error = False

    img = bin_img = resized_bin_img = None

    while True:
        event, values = window.read()

        # when user press close button
        if event == sg.WIN_CLOSED or event == 'Close':
            break
        # When user press browse button
        elif (event == '-BROWSE-'):
            try:
                # try to open file in binary stream (for sending), & resized version also in binary
                # stream (for displaying)
                path = values['-BROWSE-']

                img = Image.open(path)
                bin_img = img_to_bin(img)
                resized_bin_img = img_to_bin(img, DEFAULT_IMG_SIZE)
                img.close()

                # display preview image and hide previous error line
                toggle_sec_img = True
                window['-IMG-'].update(data=resized_bin_img)
                window['sec_img'].update(visible=toggle_sec_img)

                file_error = toggle_sec_error = False
                window['sec_error'].update(visible=toggle_sec_error)
            except:
                # hide preview image and display error line
                toggle_sec_img = False
                window['sec_img'].update(visible=toggle_sec_img)

                file_error = toggle_sec_error = True
                window['-ERROR-'].update('Cannot open the file')
                window['sec_error'].update(visible=toggle_sec_error)

        elif (event == 'Submit'):
            try:
                # if user still has not selected a valid image, skip
                if file_error:
                    continue

                # send file to server
                send(sock, bin_img)
                print(f'{path} is sent')
                file_error = False
            except Exception as e:
                # show error about connection
                toggle_sec_error = True
                window['-ERROR-'].update('Cannot connect to server')
                window['sec_error'].update(visible=toggle_sec_error)

                print(e)


def list_hotels_menu(sock):
    '''
        LIST OF HOTELS
        [LIST]
    '''

    WIN_SIZE = (420, 330)

    # default layout when there is not hotel
    default_col = [
        [sg.Text('List of Hotels', font='* 14 bold')],
        [sg.Text('No hotel available')]
    ]

    layout = [
        [sg.Push(), sg.Column(default_col, element_justification='center'), sg.Push()]
    ]

    window = sg.Window(TITLE, layout, size=WIN_SIZE)

    # send request to get the list of hotels
    list_hotels_request = Packet('list: hotels')
    send(sock, pickle.dumps(list_hotels_request))

    # receive list of hotels
    received_packet = receive(sock)

    # if connection is terminated
    if not received_packet:
        pass

    response = pickle.loads(received_packet)

    hotels = response.content
    print(hotels)

    # if there are hotels available, change layout
    if hotels:
        COLS = 2
        ROWS = len(hotels)
        ROWS_SHOW = 10
        COL_WIDTHS = (6, 30)
        PADDING = (4, 2)

        data = [[val[i] for val in hotels] for i in range(COLS)]

        all_listbox = [sg.Listbox(data[i], size=(COL_WIDTHS[i], ROWS), pad=PADDING,
                                  no_scrollbar=True, enable_events=True, key=f'listbox {i}',
                                  font=('Lucida Console', 12),
                                  select_mode=sg.LISTBOX_SELECT_MODE_SINGLE) for i in range(COLS)]

        title = [sg.Text('List of Hotels', font='* 14 bold')]

        layout = [
            [sg.Column([title], pad=PADDING, justification='center')],
            [sg.Text('Id'.center(COL_WIDTHS[0]), pad=PADDING), sg.Text('Name'.center(COL_WIDTHS[1]), pad=PADDING)],
            [sg.Column([all_listbox], size=(None, min(ROWS_SHOW, ROWS) * 20), pad=PADDING, scrollable=True,
                       vertical_scroll_only=True)],
            [sg.VPush()],
            [sg.Button('Back')]
        ]

        window = sg.Window(TITLE, layout, finalize=True, size=WIN_SIZE)

        # align content of list to center & remove underline in listbox
        for i in range(COLS):
            listbox = window[f'listbox {i}'].Widget
            listbox.configure(justify='center', activestyle='none')

    while True:
        event = window.read()[0]
        if event == sg.WINDOW_CLOSED:  # , if user closes window
            break
        elif event == 'Back':
            window.close()
            return main_menu
        elif event.startswith('listbox'):  # highlight line when user selects
            row = window[event].get_indexes()[0]
            for i in range(COLS):
                window[f'listbox {i}'].update(set_to_index=row)

    window.close()


def main_menu(sock=None):
    SIZE = (20, 1)

    col = [
        [sg.Text('Main menu', font='* 14 bold')],
        [blank_line()],
        [sg.Button('List of hotels', size=SIZE)],
        [sg.Button('Your reservations', size=SIZE)],
        [sg.Button('Search', size=SIZE)],
        [sg.Button('Logout', size=SIZE)],
        [blank_line()]
    ]

    layout = [
        [sg.Push(), sg.Column(col, element_justification='center'), sg.Push()]
    ]

    window = sg.Window(TITLE, layout)

    event = window.read()[0]

    if event == sg.WIN_CLOSED:  # if user closes the window
        window.close()
        return None
    elif event == 'Logout':  # if user presses back button
        window.close()
        return welcome_window
    elif event == 'List of hotels':
        window.close()
        return list_hotels_menu
    elif event == 'Your reservations':
        pass
    elif event == 'Search':
        pass


def register_window(sock):
    '''
        Register
    username:    [INPUT:USERNAME]
    password:    [INPUT:PASSWORD]
    card number: [INPUT:CARD_NUMBER]
    [ERROR]
    [BUTTON:REGISTER] [BUTTON:EXIT]
    '''

    WIN_SIZE = (420, 220)

    title = [sg.Text('Register', font='* 14 bold')]
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([title], justification='center')],
        [blank_line()],
        [sg.Text('Username', size=(11, 1)), sg.Input(key='-USERNAME-')],
        [sg.Text('Password', size=(11, 1)), sg.Input(key='-PASSWORD-', password_char='*')],
        [sg.Text('Card number', size=(11, 1)), sg.Input(key='-CARD_NUMBER-')],
        [collapse(error, 'sec_error', visible=True)],  # temporally disable collapsable error line
        [sg.Button('Register'), sg.Button('Back')]
    ]

    window = sg.Window(TITLE, layout, size=WIN_SIZE)

    while True:  # event Loop
        event, values = window.read()

        if event == sg.WIN_CLOSED:  # if user closes the window
            window.close()
            return None
        elif event == 'Back':  # if user presses back button
            window.close()
            return welcome_window
        elif event == 'Register':  # if user presses login button
            username = values['-USERNAME-']
            password = values['-PASSWORD-']
            card_number = values['-CARD_NUMBER-']

            # hide error line by default
            toggle_sec_error = False

            # 1. check if all fields are not empty
            for field, value in (('Username', username), ('Password', password), ('Card number', card_number)):
                if not value:
                    toggle_sec_error = True
                    error_msg = f'{field} cannot be empty'

                    break

            # 2. no empty field means no error yet, now validate the format of input information
            if not toggle_sec_error:
                # set error to true just for now
                toggle_sec_error = True

                if len(username) < 5:
                    error_msg = 'Username is too short (min. 5)'
                elif not username.isalnum():
                    error_msg = 'Invalid username'
                elif len(password) < 3:
                    error_msg = 'Password is too short (min. 3)'
                elif len(card_number) != 10 or not card_number.isdecimal():
                    error_msg = 'Invalid card number'
                else:
                    # set to false since there is no error
                    toggle_sec_error = False

            # 3. still no error so now send input info to server
            if not toggle_sec_error:
                # send register_request
                register_request = Packet('register', {'username': username,
                                                       'password': password,
                                                       'card_number': card_number})

                send(sock, pickle.dumps(register_request))

                # receive response from server (either success or fail)
                received_packet = receive(sock)

                # if connection is terminated
                if not received_packet:
                    toggle_sec_error = True
                    error_msg = 'Cannot connect to server'

                response = pickle.loads(received_packet)

                # close register window if successful
                if response.header == 'success':
                    window.close()
                    popup_window('Login successful')
                    return main_menu
                else:
                    toggle_sec_error = True
                    error_msg = 'Username was taken'

            # update the error message and display it
            window['-ERROR-'].update(error_msg)
            window['sec_error'].update(visible=True)

            # clear password input field
            window['-PASSWORD-'].update('')


def login_window(sock):
    '''
        Login
    username:    [INPUT:USERNAME]
    password:    [INPUT:PASSWORD]
    [ERROR]
    [BUTTON:LOGIN] [BUTTON:EXIT]
    '''

    WIN_SIZE = (420, 190)
    BUTTON_SIZE = (5, 1)

    title = [sg.Text('Login', font='* 14 bold')]
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([title], justification='center')],
        [blank_line()],
        [sg.Text('Username', size=(11, 1)), sg.Input(key='-USERNAME-')],
        [sg.Text('Password', size=(11, 1)), sg.Input(key='-PASSWORD-', password_char='*')],
        [collapse(error, 'sec_error', visible=True)],  # temporally disable collapsable error line
        [sg.Button('Login', size=BUTTON_SIZE), sg.Button('Back', size=BUTTON_SIZE)],
    ]

    window = sg.Window(TITLE, layout, size=WIN_SIZE)

    while True:  # event Loop
        event, values = window.read()

        if event == sg.WIN_CLOSED:  # if user closes the window
            window.close()
            return None
        elif event == 'Back':  # if user presses back button
            window.close()
            return welcome_window
        elif event == 'Login':  # if user presses login button
            username = values['-USERNAME-']
            password = values['-PASSWORD-']

            # hide error line by default
            toggle_sec_error = False

            # 1. check if all fields are not empty
            for field, value in (('Username', username), ('Password', password)):
                if not value:
                    toggle_sec_error = True
                    error_msg = f'{field} cannot be empty'

                    break

            # 2. no error so now send login info to server
            if not toggle_sec_error:
                # send login_request
                login_request = Packet('login', {'username': username,
                                                 'password': password})

                send(sock, pickle.dumps(login_request))

                # receive response from server (either success or fail)
                received_packet = receive(sock)

                # if connection is terminated
                if not received_packet:
                    toggle_sec_error = True
                    error_msg = 'Cannot connect to server'

                response = pickle.loads(received_packet)

                # close login window if successful
                if response.header == 'success':
                    window.close()
                    popup_window('Login successful')
                    return main_menu
                else:
                    toggle_sec_error = True
                    error_msg = 'Incorrect username or password'

            # update the error message and display it
            window['-ERROR-'].update(error_msg)
            window['sec_error'].update(visible=True)

            # clear password input field
            window['-PASSWORD-'].update('')


def welcome_window(sock=None):
    '''
        Welcome
    [BUTTON:LOGIN] [BUTTON:REGISTER]
    '''

    WIN_SIZE = (420, 190)
    BUTTON_SIZE = (8, 1)

    title = [sg.Text('Welcome', font='* 14 bold')]

    layout = [
        [sg.Column([title], justification='center')],
        [blank_line()],
        [sg.Button('Login', size=BUTTON_SIZE)],
        [sg.Button('Register', size=BUTTON_SIZE)]
    ]

    window = sg.Window(TITLE, align(layout), size=WIN_SIZE)

    # display window
    event = window.read()[0]

    if event == sg.WIN_CLOSED:  # if user closes the window
        window.close()
        return None
    if event == 'Login':  # if user pressed login button
        window.close()
        return login_window
    # user presses register button
    window.close()
    return register_window


def connect_server(host, port):
    # create socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as error:
        print(str(error))
        sys.exit(0)

    # connect server socket
    while True:
        try:
            sock.connect((host, port))
            break
        except socket.error:
            print('Failed to connect. Trying again...')

            SLEEP_TIME = 2
            time.sleep(SLEEP_TIME)

    # confirm message from server
    received_packet = receive(sock)
    if not received_packet:
        print('Server did not response')
    else:
        print(received_packet.decode('utf-8'))

    # start
    cur_window = welcome_window()
    while(cur_window):
        cur_window = cur_window(sock)


# start
HOST = '127.0.0.1'
PORT = 2808

connect_server(HOST, PORT)

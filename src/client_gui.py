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


def collapse(layout, key, visible, alignment=None):
    '''
    Helper function that creates a Column that can be later made hidden, thus appearing "collapsed"
    :param layout: The layout for the section
    :param key: Key used to make this section visible / invisible
    :param visible: visible determines if section is rendered visible or invisible on initialization
    :return: A pinned column that can be placed directly into your layout
    :rtype: sg.pin
    '''

    return sg.pin(sg.Column(layout, key=key, visible=visible, pad=(0, 0), element_justification=alignment))


def popup_window(text, button='OK'):
    '''
        [TEXT]
        [BUTTON:OK]
    '''

    layout = [
        [sg.Text(text)],
        [sg.Column([[sg.Button(button)]], justification='center')]
    ]

    window = sg.Window(TITLE, layout, keep_on_top=True, modal=True)

    while True:
        event, values = window.read()

        # when user presses close button
        if event == sg.WIN_CLOSED or event == button:
            break

    window.close()


def my_reservations_window(sock):
    # send request to get the list of reservations
    list_reservations_request = Packet('list: reservations')
    send(sock, pickle.dumps(list_reservations_request))

    received_packet = receive(sock)

    # if connection is terminated
    if received_packet:
        response = pickle.loads(received_packet)

        if response.header == 'fail':
            popup_window('Cannot access')
            return main_menu_window

        reservations = response.content
    else:
        popup_window('Cannot access')
        return main_menu_window

    # list layout on the left
    L_COLS = 2
    L_ROWS = len(reservations)
    L_ROWS_SHOW = 10
    L_COL_WIDTHS = (4, 20)
    L_PADDING = (4, 2)

    list_data = [[val.get(key) for val in reservations] for key in ('reservation_id', 'date')]

    all_listbox = [sg.Listbox(list_data[i], size=(L_COL_WIDTHS[i], L_ROWS), pad=L_PADDING,
                              no_scrollbar=True, enable_events=True, key=f'listbox {i}',
                              font=('Lucida Console', 12), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)
                   for i in range(L_COLS)]

    list_col = [
        [sg.Text('ID'.center(L_COL_WIDTHS[0]), pad=L_PADDING), sg.Text('Date'.center(L_COL_WIDTHS[0]), pad=L_PADDING)],
        [sg.Column([all_listbox], size=(None, min(L_ROWS_SHOW, L_ROWS) * 20), pad=L_PADDING, scrollable=True,
                   vertical_scroll_only=True)]
    ]

    # detail layout on the right
    D_COLS = 3
    D_COL_WIDTHS = (30, 10, 6)
    D_PADDING = (4, 2)

    place_holder = ('place holder', '0', '0')

    all_detailbox = [sg.Listbox(place_holder[i], size=(D_COL_WIDTHS[i], 1), pad=D_PADDING,
                                no_scrollbar=True, enable_events=True, key=f'detailbox {i}',
                                font=('Lucida Console', 12), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)
                     for i in range(D_COLS)]

    detail_col = [
        [sg.Column([[sg.Text(key='-HOTEL-', font='* 14 bold')]], element_justification='center')],
        [sg.Text('Reservation ID:'), sg.Text(key='-RESERVATION_ID-')],
        [sg.Text('Check-in:'), sg.Text(key='-DATE_IN-')],
        [sg.Text('Check-out:'), sg.Text(key='-DATE_OUT-')],
        [sg.Text('Notes:')],
        [sg.Multiline(disabled=True, key='-NOTES-', size=(None, 3))],
        [blank_line()],
        [sg.Text('Room type'.center(D_COL_WIDTHS[0]), pad=D_PADDING),
         sg.Text('Price'.center(D_COL_WIDTHS[1]), pad=D_PADDING),
         sg.Text('Amount'.center(D_COL_WIDTHS[2]), pad=D_PADDING)],
        [sg.Column([all_detailbox], pad=D_PADDING)],
        [blank_line()],
        [sg.Text('Total Price:'), sg.Text(key='-TOTAL_PRICE-')],
        [blank_line()],
        [sg.Column([[sg.Button('Cancel')]], element_justification='center')]
    ]

    title = [sg.Text('MY RESERVATIONS', font='* 14 bold')]

    layout = [
        [sg.Column([title], pad=L_PADDING, justification='center')],
        [blank_line()],
        [sg.Column(list_col, size=(300, 300)),
         collapse([[sg.VerticalSeparator(), sg.Column(detail_col)]],
                  visible=False, key='sec_detail', alignment='center')],
        [blank_line()],
        [sg.Button('Back')]
    ]

    window = sg.Window(TITLE, layout, finalize=True)

    details = None

    # align content of reservations list
    window['listbox 0'].Widget.configure(justify='center', activestyle='none')
    window['listbox 1'].Widget.configure(justify='center', activestyle='none')
    window['detailbox 0'].Widget.configure(justify='center', activestyle='none')
    window['detailbox 1'].Widget.configure(justify='right', activestyle='none')
    window['detailbox 2'].Widget.configure(justify='center', activestyle='none')

    while True:  # event loop
        event = window.read()[0]
        if event == sg.WINDOW_CLOSED:  # if user closes window
            window.close()
            return None
        elif event == 'Back':
            window.close()
            return main_menu_window
        elif event.startswith('listbox'):  # highlight line when user selects
            try:
                row = window[event].get_indexes()[0]
            except:  # list is empty
                continue
            for i in range(L_COLS):
                window[f'listbox {i}'].update(set_to_index=row)

            details = reservations[row]

            window['-HOTEL-'].update(details['hotel_name'])
            window['-RESERVATION_ID-'].update(details['reservation_id'])
            window['-RESERVATION_ID-'].update(details['reservation_id'])
            window['-DATE_IN-'].update(details['start_date'])
            window['-DATE_OUT-'].update(details['end_date'])
            window['-NOTES-'].update(details['notes'])

            rooms_data = [[], [], []]
            for val in details['rooms_info']:
                rooms_data[0].append(val[0])
                rooms_data[1].append(f'{val[1]:,}')
                rooms_data[2].append(val[2])

            for i in range(D_COLS):
                window[f'detailbox {i}'].update(rooms_data[i])
                window[f'detailbox {i}'].Widget.configure(height=len(rooms_data[0]))

            # rooms info contains hotel name, price and number of rooms
            total_price = sum([int(val[1]) * int(val[2]) for val in details['rooms_info']])
            window['-TOTAL_PRICE-'].update(f'{total_price:,}')

            # show the detail panel
            window['sec_detail'].update(visible=True)

        elif event.startswith('detailbox'):  # highlight line when user selects detailbox
            try:
                row = window[event].get_indexes()[0]
            except:  # list is empty
                continue

            for i in range(D_COLS):
                window[f'detailbox {i}'].update(set_to_index=row)
        elif event == 'Cancel':  # when user presses cancel button
            send(sock, pickle.dumps(Packet('cancel', details['reservation_id'])))
            received_packet = receive(sock)

            # if connection is terminated
            if received_packet:
                response = pickle.loads(received_packet)

                if response.header == 'fail':
                    popup_window('Cancel failed')
                else:
                    popup_window('Cancel successful')
                    window.close()
                    return my_reservations_window
            else:
                popup_window('Cannot access')


def reserve_window(sock):

    # date picker (calendar)
    check_in_out_cols = [[
        [sg.Text(f'Check-{name} date')],
        [sg.Multiline(size=(10, 1), key=f'-DATE_{name.upper()}-', no_scrollbar=True, disabled=True)],
        [sg.CalendarButton('Choose', target=f'-DATE_{name.upper()}-', format='%Y-%m-%d')]
    ] for name in ('in', 'out')]

    # add a place holder line
    room_types = [['place holder', 0, '0/0']]

    COLS = 3
    COL_WIDTHS = (30, 11, 8)
    PADDING = (4, 2)

    # use listbox for displaying room types
    all_listbox = [sg.Listbox(room_types, size=(COL_WIDTHS[i], 1), pad=PADDING,
                              no_scrollbar=True, enable_events=True, key=f'listbox {i}',
                              font=('Lucida Console', 12), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)
                   for i in range(COLS)]

    # layout for the result
    result = [
        [sg.Text(key='-RESULT_TITLE-', font='* 14 bold')],
        [sg.Text('Room type'.center(COL_WIDTHS[0]), pad=PADDING),
         sg.Text('Price'.center(COL_WIDTHS[1]), pad=PADDING),
         sg.Text('Amount'.center(COL_WIDTHS[2]), pad=PADDING)],
        [sg.Column([all_listbox], pad=PADDING)],
        [blank_line()],
        [sg.Button('+'), sg.Button('-')],
        [blank_line()],
        [sg.Text('Total'), sg.Multiline(0, size=(12, 1), disabled=True, no_scrollbar=True, key='-TOTAL_PRICE-')]
    ]

    result = [
        [sg.HorizontalSeparator()],
        [blank_line()],
        [sg.Frame(None, result, element_justification='center')],
        [sg.Button('Submit')]
    ]

    # layout for the input form
    form = [
        [blank_line()],
        [sg.Text('Hotel name or ID')],
        [sg.Input(key='-HOTEL-', size=(40, None))],
        [sg.Column(col, element_justification='center') for col in check_in_out_cols],
        [sg.Text('Notes')],
        [sg.Multiline(autoscroll=True, do_not_clear=True, size=(50, 3), key='-NOTES-')],
        [blank_line()],
    ]

    title = [[sg.Text(f"{'SEARCH':^100}", font='* 14 bold')]]

    # master layout
    layout = [
        [sg.Column(title, justification='center')],
        [sg.Frame(None, form, element_justification='center')],
        [blank_line()],
        [sg.Button('Search'), sg.Button('Back')],
        [blank_line()],
        [collapse(result, 'sec_result', visible=False, alignment='center')],
    ]

    window = sg.Window(TITLE, layout, finalize=True, element_justification='center')

    # align column in result listbox
    for i in range(COLS):
        window[f'listbox {i}'].Widget.configure(justify='center', activestyle='none')

    start_date = end_date = data = hotel_id = None

    while True:  # event loop
        event, values = window.read()

        if event == sg.WINDOW_CLOSED:  # when user closes window
            window.close()
            return None
        elif event == 'Back':  # when user presses back button
            window.close()
            return main_menu_window
        elif event == 'Search':  # when user presses search button
            start_date = values['-DATE_IN-']
            end_date = values['-DATE_OUT-']
            hotel = values['-HOTEL-']

            if not (start_date and end_date and hotel):
                popup_window('Missing information')
                continue

            # send request to server to get info needed
            search_request = Packet('simple search', {'hotel': hotel,
                                                      'start_date': start_date,
                                                      'end_date': end_date})
            send(sock, pickle.dumps(search_request))

            received_packet = receive(sock)

            # if connection is terminated
            if not received_packet:
                print('cannot connect to server')
                continue

            response = pickle.loads(received_packet)

            # if there is error
            if response.header == 'fail':
                window['sec_result'].update(visible=False)
                popup_window(response.content)
                continue

            # response data contains room type id, room type, price, available rooms
            room_types = response.content['data']

            # update result title
            hotel_id, hotel_name = response.content['hotel_id'], response.content['hotel_name']
            window['-RESULT_TITLE-'].update(f'{hotel_id} - {hotel_name}')

            # append room type, price and available rooms into 3 columns and 1 additional for room type id
            data = [[], [], [], []]
            for room_type in room_types:
                data[0].append(room_type[1])
                data[1].append(f'{int(room_type[2]):,}')
                data[2].append(f'0/{int(room_type[3])}')
                data[3].append(room_type[0])

            window['sec_result'].update(visible=True)

            for i in range(COLS):
                window[f'listbox {i}'].update(data[i])
                window[f'listbox {i}'].Widget.configure(height=len(room_types))

        elif event.startswith('listbox'):  # highlight line when user selects line
            row = window[event].get_indexes()[0]
            for i in range(COLS):
                window[f'listbox {i}'].update(set_to_index=row)
        elif event == '+':  # when user presses + button
            try:
                idx = window['listbox 2'].get_indexes()[0]
                to_reserve, available_rooms = data[2][idx].split('/')

                to_reserve = int(to_reserve)
                available_rooms = int(available_rooms)

                if to_reserve == available_rooms:
                    continue

                data[2][idx] = f'{to_reserve + 1}/{available_rooms}'
                window['listbox 2'].update(data[2], set_to_index=idx)

                # update total_price
                cur_price = int(values['-TOTAL_PRICE-'].replace(',', ''))
                to_add = int(data[1][idx].replace(',', ''))
                window['-TOTAL_PRICE-'].update(cur_price + to_add)
            except:  # this happens when user has not select any line
                pass
        elif event == '-':  # when user presses - button
            try:
                idx = window['listbox 2'].get_indexes()[0]
                to_reserve, available_rooms = data[2][idx].split('/')

                to_reserve = int(to_reserve)
                available_rooms = int(available_rooms)

                if to_reserve == 0:
                    continue

                data[2][idx] = f'{to_reserve - 1}/{available_rooms}'
                window[f'listbox 2'].update(data[2], set_to_index=idx)

                # update total_price
                cur_price = int(values['-TOTAL_PRICE-'].replace(',', ''))
                to_subtract = int(data[1][idx].replace(',', ''))
                window['-TOTAL_PRICE-'].update(cur_price - to_subtract)
            except:  # this happens when user has not select any line
                pass
        elif event == 'Submit':  # when user presses submit button
            send_data = []
            for i, amount in enumerate(data[2]):
                to_reserve = int(amount.split('/')[0])

                if to_reserve == 0:
                    continue

                # send_data contains room type id & number of rooms
                send_data.append([data[3][i], to_reserve])

            # if there is no data to send
            if not send_data:
                popup_window('There is nothing to reserve')

            # send request to server
            reserve_request = Packet('reserve', {'data': send_data,
                                                 'hotel_id': hotel_id,
                                                 'start_date': start_date,
                                                 'end_date': end_date,
                                                 'notes': values['-NOTES-']})
            send(sock, pickle.dumps(reserve_request))

            received_packet = receive(sock)

            # if connection is terminated
            if not received_packet:
                print('cannot connect to server')
                continue

            response = pickle.loads(received_packet)

            # if there is error
            if response.header == 'fail':
                window['sec_result'].update(visible=False)
                popup_window('Reserve failed')
                continue
            window['sec_result'].update(visible=False)
            popup_window('Reserve successful')


def details_window(bin_image, description):
    '''
    [IMAGE] | [DESCRIPTION]
    '''

    image = [[sg.Image(bin_image)]]
    des = [[sg.Text(description, key='-DESCRIPTION-')]]

    layout = [
        [sg.Column(image), sg.VSeparator(), sg.Column(des)],
        [sg.Button('Close')]
    ]

    window = sg.Window(TITLE, layout, element_justification='center', modal=True, finalize=True)

    window['-DESCRIPTION-'].Widget.configure(wrap=400)

    while True:
        event = window.read()[0]

        if event == sg.WINDOW_CLOSED or event == 'Close':
            break

    window.close()


def search_window(sock):
    '''
        SEARCH
    HOTEL NAME/ID:  [INPUT:HOTEL_NAME/HOTEL_ID]
    CHECK-IN DATE:  [INPUT:CHECK_IN_DATE]
    CHECK-OUT DATE: [INPUT:CHECK_OUT_DATE]
        [BUTTON:SUBMIT]

    [ROOM TYPE] [ROOMS LEFT] [PRICE]
    [              DATA            ]
        [BUTTON:DETAILS]
    '''

    # date picker (calendar)
    check_in_out_cols = [[
        [sg.Text(f'Check-{name} date')],
        [sg.Multiline(size=(10, 1), key=f'-DATE_{name.upper()}-', no_scrollbar=True, disabled=True)],
        [sg.CalendarButton('Choose', target=f'-DATE_{name.upper()}-', format='%Y-%m-%d')]
    ] for name in ('in', 'out')]

    # add a place holder line
    room_types = [['place holder', 0, 0]]

    COLS = 3
    COL_WIDTHS = (30, 9, 11)
    PADDING = (4, 2)

    # use listbox for displaying room types
    all_listbox = [sg.Listbox(room_types, size=(COL_WIDTHS[i], 1), pad=PADDING,
                              no_scrollbar=True, enable_events=True, key=f'listbox {i}',
                              font=('Lucida Console', 12), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)
                   for i in range(COLS)]

    # layout for the result
    result = [
        [sg.HorizontalSeparator()],
        # [blank_line()],
        [sg.Text(key='-RESULT_TITLE-', font='* 14 bold')],
        [sg.Text('Room type'.center(COL_WIDTHS[0]), pad=PADDING),
         sg.Text('Available'.center(COL_WIDTHS[1]), pad=PADDING),
         sg.Text('Price'.center(COL_WIDTHS[2]), pad=PADDING)],
        [sg.Column([all_listbox], pad=PADDING)],
        [blank_line()],
        [sg.Button('Details')]
    ]

    # layout for the input form
    form = [
        [blank_line()],
        [sg.Text('Hotel name or ID')],
        [sg.Input(key='-HOTEL-', size=(40, None))],
        [sg.Column(col, element_justification='center') for col in check_in_out_cols],
        [blank_line()],
    ]

    title = [[sg.Text(f"{'SEARCH':^100}", font='* 14 bold')]]

    # master layout
    layout = [
        [sg.Column(title, justification='center')],
        [sg.Frame(None, form, element_justification='center')],
        [blank_line()],
        [sg.Button('Submit'), sg.Button('Back')],
        [blank_line()],
        [collapse(result, 'sec_result', visible=False, alignment='center')],
    ]

    window = sg.Window(TITLE, layout, finalize=True, element_justification='center')

    # align column in result listbox
    window[f'listbox 0'].Widget.configure(justify='center', activestyle='none')
    window[f'listbox 1'].Widget.configure(justify='center', activestyle='none')
    window[f'listbox 2'].Widget.configure(justify='right', activestyle='none')

    while True:  # event loop
        event, values = window.read()

        if event == sg.WINDOW_CLOSED:  # when user closes window
            window.close()
            return None
        elif event == 'Back':  # when user presses back button
            window.close()
            return main_menu_window
        elif event == 'Submit':  # when user presses submit button
            start_date = values['-DATE_IN-']
            end_date = values['-DATE_OUT-']
            hotel = values['-HOTEL-']

            if not (start_date and end_date and hotel):
                popup_window('Missing information')
                continue

            # send request to server to get info needed
            search_request = Packet('search', {'hotel': hotel,
                                               'start_date': start_date,
                                               'end_date': end_date})
            send(sock, pickle.dumps(search_request))

            received_packet = receive(sock)

            # if connection is terminated
            if not received_packet:
                print('cannot connect to server')
                continue

            response = pickle.loads(received_packet)

            # if there is error
            if response.header == 'fail':
                window['sec_result'].update(visible=False)
                popup_window(response.content)
                continue

            # response data contains id, name, description, price, available rooms, binary image
            room_types = response.content['data']
            hotel_id = response.content['hotel_id']
            hotel_name = response.content['hotel_name']

            # update result title
            window['-RESULT_TITLE-'].update(f'{hotel_id} - {hotel_name}')

            # append name and rooms left into 2 separate columns
            data = [[val[i] for val in room_types] for i in (1, 4)]
            # append 1 more column for price
            data.append([f'{int(val[3]):,}' for val in room_types])

            window['sec_result'].update(visible=True)

            for i in range(COLS):
                window[f'listbox {i}'].update(data[i])
                window[f'listbox {i}'].Widget.configure(height=len(room_types))

        elif event.startswith('listbox'):  # highlight line when user selects line
            row = window[event].get_indexes()[0]
            for i in range(COLS):
                window[f'listbox {i}'].update(set_to_index=row)
        elif event == 'Details':  # when user pressed Details button
            try:
                idx = window['listbox 0'].get_indexes()[0]
                details_window(room_types[idx][5], room_types[idx][2])
            except:  # this happens when user has not select any line
                pass


def list_hotels_window(sock):
    '''
        LIST OF HOTELS
        [LIST]
    '''

    WIN_SIZE = (420, 350)

    # send request to get the list of hotels
    list_hotels_request = Packet('list: hotels')
    send(sock, pickle.dumps(list_hotels_request))

    received_packet = receive(sock)

    # if connection is terminated
    if received_packet:
        response = pickle.loads(received_packet)
        hotels = response.content
    else:
        hotels = None

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
                                  font=('Lucida Console', 12), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)
                       for i in range(COLS)]

        title = [sg.Text('LIST OF HOTELS', font='* 14 bold')]

        layout = [
            [sg.Column([title], pad=PADDING, justification='center')],
            [blank_line()],
            [sg.Text('Id'.center(COL_WIDTHS[0]), pad=PADDING), sg.Text('Name'.center(COL_WIDTHS[1]), pad=PADDING)],
            [sg.Column([all_listbox], size=(None, min(ROWS_SHOW, ROWS) * 20), pad=PADDING, scrollable=True,
                       vertical_scroll_only=True)],
            [sg.VPush()],
            [sg.Button('Back')]
        ]

        window = sg.Window(TITLE, layout, finalize=True, size=WIN_SIZE)

        # align content of list to center & remove underline in listbox
        for i in range(COLS):
            window[f'listbox {i}'].Widget.configure(justify='center', activestyle='none')
    else:  # default layout when there is not hotel
        default_col = [
            [sg.Text('List of Hotels', font='* 14 bold')],
            [sg.Text('No hotel available')]
        ]

        layout = [
            [sg.Push(), sg.Column(default_col, element_justification='center'), sg.Push()]
        ]

        window = sg.Window(TITLE, layout, size=WIN_SIZE)

    while True:  # event loop
        event = window.read()[0]
        if event == sg.WINDOW_CLOSED:  # if user closes window
            window.close()
            return None
        elif event == 'Back':
            window.close()
            return main_menu_window
        elif event.startswith('listbox'):  # highlight line when user selects
            row = window[event].get_indexes()[0]
            for i in range(COLS):
                window[f'listbox {i}'].update(set_to_index=row)


def main_menu_window(sock=None):
    SIZE = (15, 1)

    col = [
        [sg.Text('MAIN MENU', font='* 14 bold')],
        [blank_line()],
        [sg.Button('List of hotels', size=SIZE)],
        [sg.Button('Search', size=SIZE)],
        [sg.Button('Reserve', size=SIZE)],
        [sg.Button('My reservations', size=SIZE)],
        [sg.Button('Close', size=SIZE)],
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
    elif event == 'Close':  # if user presses back button
        window.close()
        return None
    elif event == 'List of hotels':
        window.close()
        return list_hotels_window
    elif event == 'Reserve':
        window.close()
        return reserve_window
    elif event == 'My reservations':
        window.close()
        return my_reservations_window
    elif event == 'Search':
        window.close()
        return search_window


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

    title = [sg.Text('REGISTER', font='* 14 bold')]
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
                    popup_window('Register successful')
                    window.close()
                    return welcome_window
                else:
                    toggle_sec_error = True
                    error_msg = 'Username or Card number was taken'

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

    title = [sg.Text('LOGIN', font='* 14 bold')]
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
                    popup_window('Login successful')
                    window.close()
                    return main_menu_window
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

    title = [sg.Text('WELCOME', font='* 14 bold')]

    layout = [
        [sg.Column([title], justification='center')],
        [blank_line()],
        [sg.Button('Login', size=BUTTON_SIZE)],
        [sg.Button('Register', size=BUTTON_SIZE)],
        [blank_line()]
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
    try:
        cur_window = welcome_window()
        while(cur_window):
            cur_window = cur_window(sock)
    except socket.error as e:
        print(e)

    # my_reservations_window(sock)


# start
HOST = '127.0.0.1'
PORT = 2808

connect_server(HOST, PORT)

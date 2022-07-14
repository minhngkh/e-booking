import PySimpleGUI as sg
import socket
import sys
import time
import json
import io,os
from PIL import Image

from functions import *

sg.theme('Dark Grey 9')
TITLE = 'E-Booking'
DEFAULT_IMG_SIZE = 300


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

    window.close()


def login_window(sock):
    '''
        Login
    username: [INPUT:USERNAME]
    password: [INPUT:PASSWORD]
    [ERROR]
    [BUTTON:LOGIN] [BUTTON:EXIT]
    '''

    title = sg.Text('Login', font='* 12 bold')
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text('Username', size=(11, 1)), sg.Input(key='-USERNAME-')],
        [sg.Text('Password', size=(11, 1)), sg.Input(key='-PASSWORD-', password_char='*')],
        [sg.Text('Card number', size=(11, 1)), sg.Input(key='-CARD_NUMBER-')],
        [collapse(error, 'sec_error', visible=False)],
        [sg.Button('Login'), sg.Button('Exit')]
    ]

    window = sg.Window(TITLE, layout)

    while True:  # Event Loop
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        elif event == 'Login':
            username = values['-USERNAME-']
            password = values['-PASSWORD-']
            card_number = values['-CARD_NUMBER-']

            # hide previous error line
            toggle_sec_error = False

            for field, value in (('Username', username), ('Password', password), ('Card number', card_number)):
                if not value:
                    toggle_sec_error = True
                    window['-ERROR-'].update(f'{field} cannot be empty')
                    window['sec_error'].update(visible=toggle_sec_error)

                    break

            if toggle_sec_error:
                window['-PASSWORD-'].update('')

                continue
            else:
                window['-ERROR-'].update('')

            send(sock, username.encode())
            send(sock, password.encode())
            send(sock, card_number.encode())

    window.close()

def jsonDatabase():
    with open("database/hotellist.json", "r") as f:
        data = json.load(f)    
    return data


def booking(sock):
    '''
        Booking Form
    Hotel Name: [HOTELNAME]
    Room Reference: [BUTTON:STANDARD] [BUTTON:DELUXE] [BUTTON:SUITE]
    Check-in Date: [CHECKIN]
    Check-out Date: [CHECKOUT]
    '''

    title = sg.Text('Booking Form', font='* 12 bold')
    submit = sg.Button('Submit', font='* 12 bold')

    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text('Hotel Name', size=(12, 1)), sg.Input(key='-HOTELNAME-')],
        [sg.Text('Room Reference', size=(12, 1)), 
                                sg.Radio('Standard', 'group 1', key='-ST-'), 
                                sg.Radio('Deluxe', 'group 1',key='-DE-'), 
                                sg.Radio('Suite', 'group 1',key='-SU-')],
        [sg.CalendarButton("Check-in Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKIN-', size=(45,1)) ],
        [sg.CalendarButton("Check-out Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKOUT-', size=(45,1)) ],
        [sg.Column([[submit]], justification='center')],
        [collapse(error, 'sec_error', visible=False)]   
       
    ]

    window = sg.Window(TITLE, layout)

    while True:  # Event Loop
        event, values = window.read()     

        if event == sg.WIN_CLOSED or event == 'Submit':
            break
    

    window.close()



def displayHotel(index,data):
    hotelname = data['hotel'][index]['name']
    price = data['hotel'][index]['price']
    des = data['hotel'][index]['des']
    img = data['hotel'][index]['img']
    
    STprice = 'Standard: ' + price['ST'] + '$'
    DEprice = 'Deluxe: ' + price['DE'] + '$'
    SUprice = 'Suite: ' + price['SU'] + '$'

    '''
        Hotel Details
    Description
    Room Reference with price (eg. Delux: 350$)
    Image
    '''

    title = sg.Text('Hotel Details', font='* 12 bold')
    submit = sg.Button('Submit', font='* 12 bold')

    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    extensions_allowed = (('IMAGE files', '*.png *.jpg *.jpeg'),
                          ('ALL files', '*.*'))
    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text(hotelname, size = (12,1))],
        [sg.Text(des, size = (55,1))],
        [sg.Text(STprice, size = (12,1))],
        [sg.Text(DEprice, size = (12,1))],
        [sg.Text(SUprice, size = (12,1))],
        [sg.Image(filename = img)],
    ]

    window = sg.Window(TITLE, layout)

    while True:  # Event Loop
        event, values = window.read()     

        if event == sg.WIN_CLOSED:
            break
    window.close()



def checkAvailable(userCheckin,index,data):
    Checkout = data['hotel'][index]['checkout']
    if (userCheckin > Checkout): return 1
    else: return 2



def listOfHotel():
    data = jsonDatabase()
    numberOfHotel = len(data['hotel'])  
    s = ""
    title = sg.Text('List of Hotel', font='* 12 bold')
    for i in range(numberOfHotel):
        s += data['hotel'][i]['name'] + '\n'

    sg.PopupScrolled("Hotel List\n", f"{s}")  

    
        
                    


def searching(sock):
    '''
        Searching
    Hotel Name: [HOTELNAME]
    ID of Hotel: [ID]
    Check-in Date: [CHECKIN]
    Check-out Date: [CHECKOUT]
    '''

    title = sg.Text('Searching', font='* 12 bold')
    submit = sg.Button('Submit', font='* 12 bold')
    list = sg.Button('List of Hotel', font='* 12 bold')
    bookingButton = sg.Button('Booking', font='* 12 bold')

    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text('Hotel Name', size=(12, 1)), sg.Input(key='-HOTELNAME-')],    
        [sg.CalendarButton("Check-in Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKIN-', size=(45,1)) ],
        [sg.CalendarButton("Check-out Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKOUT-', size=(45,1)) ],
        [sg.Column([[submit]], justification='center'), sg.Column([[list]], justification='center'),sg.Column([[bookingButton]], justification='center')],        
        [collapse(error, 'sec_error', visible=False)]   
       
    ]

    window = sg.Window(TITLE, layout)
    data = jsonDatabase()
    
    while True:  # Event Loop
        event, values = window.read()     

        if event == sg.WIN_CLOSED:
            break
        elif event == 'List of Hotel':
            listOfHotel()
        elif event == 'Booking':
            booking(sock)
        elif event == 'Submit':           
            flg = 0 # 0: Not found, 2: Not available, 1: Passed
            numberOfHotel = len(data['hotel'])  
            hotel = values['-HOTELNAME-']
            
            for i in range(numberOfHotel):
                if(hotel == (data['hotel'][i]['name'])):
                    userCheckin = values['-CHECKIN-']
                    flg = checkAvailable(userCheckin,i,data)
                    if(flg == 1): displayHotel(i,data)
                    else: sg.Popup(hotel, 'not available.')
                    break
            if(flg == 0): sg.Popup(hotel, 'not found. Please try again')  
        else:
            sg.Popup("Error")
    
    

    window.close()
   
   


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
    # login_window(sock)
    #image_window(sock)
    #booking(sock)
    searching(sock)
   


# start
HOST = '127.0.0.1'
PORT = 2808

connect_server(HOST, PORT)

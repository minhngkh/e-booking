from turtle import update
import PySimpleGUI as sg
import socket
import sys
import time
import pickle

from PIL import Image

from functions import *

#dev_phuc library
import database as db
import io,os
import textwrap

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


def main_menu(sock=None):
    title = [sg.Text('Main menu', font='* 12 bold')]
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([title], justification='center')],
        [sg.Button('Search')],
        [sg.Button('Book')],
        [sg.Button('Cancel')]
    ]
    
    window = sg.Window(TITLE, layout)

    window.read()


def register_window(sock):
    '''
        Register
    username:    [INPUT:USERNAME]                          
    password:    [INPUT:PASSWORD]
    card number: [INPUT:CARD_NUMBER]
    [ERROR] 
    [BUTTON:REGISTER] [BUTTON:EXIT]
    '''

    title = [sg.Text('Register', font='* 12 bold')]
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([title], justification='center')],
        [sg.Text('Username', size=(11, 1)), sg.Input(key='-USERNAME-')],
        [sg.Text('Password', size=(11, 1)), sg.Input(key='-PASSWORD-', password_char='*')],
        [sg.Text('Card number', size=(11, 1)), sg.Input(key='-CARD_NUMBER-')],
        [collapse(error, 'sec_error', visible=False)],
        [sg.Button('Register'), sg.Button('Back')]
    ]

    window = sg.Window(TITLE, layout)

    while True:  # event Loop
        event, values = window.read()

        if event == sg.WIN_CLOSED:  # if user closes the window
            window.close()
            sys.exit(0)
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
                    sg.popup('Register Successful', title=TITLE)
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

    title = [sg.Text('Login', font='* 12 bold')]
    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([title], justification='center')],
        [sg.Text('Username', size=(11, 1)), sg.Input(key='-USERNAME-')],
        [sg.Text('Password', size=(11, 1)), sg.Input(key='-PASSWORD-', password_char='*')],
        [collapse(error, 'sec_error', visible=False)],
        [sg.Button('Login'), sg.Button('Back')]
    ]

    window = sg.Window(TITLE, layout)

    while True:  # event Loop
        event, values = window.read()

        if event == sg.WIN_CLOSED:  # if user closes the window
            window.close()
            sys.exit(0)
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
                    sg.popup('Login successful', title=TITLE)
                    return main_menu, username
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

    title = [sg.Text('Welcome', font='* 12 bold')]

    layout = [
        [sg.Column([title], justification='center')],
        [sg.Button('Login'), sg.Button('Register')]
    ]

    window = sg.Window(TITLE, layout)

    # display window
    event, values = window.read()

    if event == sg.WIN_CLOSED:  # if user closes the window
        window.close()
        sys.exit(0)
    elif event == 'Back':  # if user presses back button
        window.close()
        return welcome_window
    if event == 'Login':  # if user pressed login button
        window.close()
        return login_window
    # user presses register button
    window.close()
    return register_window
    
    
    
def checkHotelName(hotelname,id):
    # connect to database
    db_connection = db.create_connection(DB_PATH)

    if not db_connection:
        raise Exception('Cannot connect to database')

    # validate login information
    find_query = f"""
    SELECT EXISTS(
        SELECT 1
        FROM hotels     
        WHERE (id,name) = ('{id}','{hotelname}')
        )
    """
    if db.execute_query(db_connection,find_query,True)[0][0] == 1:
        return 1
    else: return 0


def checkInputRoom(userRoom,roomTypes):
    for room in roomTypes:
        if(userRoom == room[0]):
            return 1
    
    return 0


def getRoomRef(typeID,db_connection):
    c=db_connection.cursor()
    c.execute(f"""
        SELECT type_name
        FROM room_type
        WHERE id = ('{typeID}')"""
        )
    type_name = c.fetchall()[0][0]
    return type_name
    
def checkAvailableType(userType,roomTypes):
    for typeID in roomTypes:
        if (typeID[0] == userType):
            return 1
    
    return 0

def userTypeID(values):
    for index in range(1,6):
        if values[index] == True:
            return index    
    return 0

def dataRoom(typeID,hotelID):
# connect to database
    db_connection = db.create_connection(DB_PATH)
    
    if not db_connection:
        raise Exception('Cannot connect to database')

    
    #Createacursor
    c=db_connection.cursor()
    #Query The Database
    
    
    c.execute(f"""
        SELECT*
        FROM rooms
        WHERE (hotel_id,type_id) = ('{hotelID}','{typeID}')
        """)
    data = c.fetchall()
    
    #Commit our command
    db_connection.commit()
    #Close our connection
    db_connection.close()
    return data

def formatdate(date2):
    from datetime import date
    yymmddhhmmss = date2.split(" ")
    date2 = yymmddhhmmss[0]
    yymmdd = date2.split("-")
    yy = int(yymmdd[0])
    mm = int(yymmdd[1])
    dd = int(yymmdd[2])
    d = date(yy,mm,dd)
    return d

def getUserTotalCost(userCheckin,userCheckout,data):
    checkinDate = formatdate(userCheckin)
    checkoutDate = formatdate(userCheckout)
    totalDays = (checkoutDate - checkinDate).days
    pricePerDay = data[0][3]
    totalCost = totalDays * pricePerDay
    return totalCost


def displayHotel(roomKey,hotelname,roomNumber,userRoomType,roomDes,userCheckin,userCheckout,userTotalCost,roomImage):
    '''
        Hotel Detailing Receipt
    Hotel Name
    Room number
    Room Reference
    Description
    Check-in Date
    Check-out Date
    Total Cost
    [Image]
    '''
    title = sg.Text("Hotel Detailing Receipt", font='* 12 bold')
    submit = sg.Button('Submit', font='* 12 bold')

    cwd  = os.getcwd() # Current Working Directory
    roomImage = cwd + roomImage


    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text("Hotel Name:\t", font='* 10 bold'), sg.Text(hotelname)],
        [sg.Text("Room Number:\t", font='* 10 bold'), sg.Text(roomNumber)],
        [sg.Text("Room Reference:\t", font='* 10 bold'), sg.Text(userRoomType)],
        [sg.Text("Description:\t", font='* 10 bold'), sg.Multiline(roomDes,size = (60,5))],
        [sg.Text("Check-in Date:\t", font='* 10 bold'), sg.Text(userCheckin)],        
        [sg.Text("Check-out Date:\t", font='* 10 bold'), sg.Text(userCheckout)], 
        [sg.Text("Total Cost:\t", font='* 10 bold'), sg.Text(userTotalCost + "$")],   
        [sg.Image(filename = roomImage)]
    ]

    window = sg.Window(TITLE, layout)
    while True:  # Event Loop
        event, values = window.read()     
        if event == sg.WIN_CLOSED:
            break
    

    window.close()
    

def roomType(hotelname,hotelID):
    '''
        Booking Form
    Room Reference: [BUTTON:STANDARD] [BUTTON:SUPERIOR] [BUTTON:DELUXE] [BUTTON:SUITE] [BUTTON:PREMIER]
    Check-in Date: [CHECKIN]
    Check-out Date: [CHECKOUT]
    '''
        # connect to database
    db_connection = db.create_connection(DB_PATH)
    
    if not db_connection:
        raise Exception('Cannot connect to database')

    c=db_connection.cursor()
    
    c.execute(f"""
        SELECT type_id
        FROM rooms
        WHERE hotel_id = '{hotelID}'"""
        ) 
    roomTypes=c.fetchall()
    #Commit our command
    db_connection.commit()
    


    title = sg.Text(hotelname, font='* 12 bold')
    submit = sg.Button('Submit', font='* 12 bold')

    error = [[sg.Text(font='_ 9 italic', text_color='yellow', key='-ERROR-')]]

    layout = [
        [sg.Column([[title]], justification='center')],
        [sg.Text('Room Reference', size=(12, 1)), 
                                sg.Radio('Standard', 'group 1', key=1), 
                                sg.Radio('Superior', 'group 1',key=2), 
                                sg.Radio('Deluxe', 'group 1',key=3),
                                sg.Radio('Suite', 'group 1',key=4),
                                sg.Radio('Premier', 'group 1',key=5)],
        [sg.CalendarButton("Check-in Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKIN-', size=(45,1)) ],
        [sg.CalendarButton("Check-out Date", close_when_date_chosen=True, location= (280,350), no_titlebar=False, size =(12,1) ),sg.Input(key='-CHECKOUT-', size=(45,1)) ],
        [sg.Column([[submit]], justification='center')],
        [collapse(error, 'sec_error', visible=False)]   
       
    ]

    window = sg.Window(TITLE, layout)
    

    
    while True:  # Event Loop
        event, values = window.read()     
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Submit':
            #Get user's room type ID
            userType = userTypeID(values)       
            #Get user's type name            
            userRoomType = getRoomRef(userType,db_connection)

            if (userTypeID == 0): sg.Popup("Something wrong with user's type ID.")
            if (checkAvailableType(userType,roomTypes)):
                data = dataRoom(userType,hotelID)
                roomKey = str(data[0][0])
                roomNumber = str(data[0][1])
                userRoomType = str(userRoomType)
                roomDes = str(data[0][2])
                userCheckin = str(values['-CHECKIN-'])
                userCheckout = str(values['-CHECKOUT-'])
                userTotalCost = str(getUserTotalCost(userCheckin,userCheckout,data))
                roomImage = str(data[0][7])
                displayHotel(roomKey,hotelname,roomNumber,userRoomType,roomDes,userCheckin,userCheckout,userTotalCost,roomImage)
            else: sg.Popup(userRoomType, "is not available. Please select other type of room!", title = TITLE)
   
    #Close our connection
    db_connection.close()
   
    window.close()



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
        [sg.Text('ID', size= (12,1)),sg.Input(key='-ID-')],
        [sg.Text('Hotel Name', size=(12, 1)), sg.Input(key='-HOTELNAME-')],
        [sg.Column([[submit]], justification='center')],
        [collapse(error, 'sec_error', visible=False)]   
       
    ]

    window = sg.Window(TITLE, layout)
    

    while True:  # Event Loop
        event, values = window.read()     

        if event == sg.WIN_CLOSED:
            break
        elif event == 'Submit':           
            flg = 0 # 0: Not found, 2: Not available, 1: Passed
            
            hotelname = values['-HOTELNAME-']
            id = values['-ID-']
            if(checkHotelName(hotelname,id)):
                roomType(hotelname,id)
            else: sg.Popup(hotelname, 'not found. Please try again')          

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
    global username
    
    booking(sock)
    # cur_window = welcome_window()
    # while(cur_window):
    #     cur_window,username = cur_window(sock)
   


# start
HOST = '127.0.0.1'
PORT = 2808
DB_PATH = 'data/db.sqlite'

connect_server(HOST, PORT)

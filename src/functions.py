from dataclasses import dataclass
import struct
import io

from PIL import Image


@dataclass
class Packet:
    header: str
    content: any = None


BUFFER_SIZE = 2048
HEADER_SIZE = 4

IMG_FORMAT = 'PNG'


def save_img(bin_img, path):
    ''' 
    Save binary stream as a file
    '''

    # create image object
    bin_img = Image.open(io.BytesIO(bin_img))

    # save object as image at path
    bin_img.save(path, format=IMG_FORMAT)

    bin_img.close()


def img_to_bin(img, resize=None):
    '''
    take an image object and return a binary stream of it (or its resized version)
    '''

    if resize:
        cur_width, cur_height = img.size

        # determine the optimal direction to resize to (follow width or height)
        scale = min(resize/cur_height, resize/cur_width)

        # resize image with anti-alias enabled
        img = img.resize((int(cur_width*scale), int(cur_height*scale)), Image.Resampling.LANCZOS)

    # save img object as binary stream
    bin_img = io.BytesIO()
    img.save(bin_img, format=IMG_FORMAT)

    return bin_img.getvalue()


def send(sock, packet):
    # send a 4-bytes chunk containing packet size
    sock.sendall(struct.pack('>I', len(packet)))

    # send the packet
    sock.sendall(packet)


def receive_exact(sock, size):
    data = bytearray()
    remaining_size = size
    while remaining_size > 0:
        received = sock.recv(BUFFER_SIZE if remaining_size > BUFFER_SIZE else remaining_size)
        if not received:
            return None

        data.extend(received)
        remaining_size -= len(received)

    return data


def receive(sock):
    raw_packet_size = receive_exact(sock, HEADER_SIZE)
    if not raw_packet_size:
        return None

    packet_size = struct.unpack('>I', raw_packet_size)[0]

    return receive_exact(sock, packet_size)

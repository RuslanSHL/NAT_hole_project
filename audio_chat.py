import pyaudio
from NAT_hole import *
import threading
import queue
import time
import socket
import os
import numpy as np


os.system("color")
os.makedirs("logs", exist_ok=True)
try:
    log_file_name = f"logs/{os.path.basename(__file__)} {time.strftime('%b %d %H.%M.%S')}.log"
except NameError:
    log_file_name = f"logs/{__name__} {time.strftime('%b %d %H.%M.%S')}.log"


with open(log_file_name, "a") as debug_logging_file:
    debug_logging_file.write("start new deb logging\n")
    debug_logging_file.flush()


def deb_print(*args, **argv):
    try:
        with open(log_file_name, "a") as debug_logging_file:
            debug_logging_file.write(f"D {time.time()}: ")
            print(*args, **argv, file=debug_logging_file)
            debug_logging_file.flush()
    except NameError:
        with open(log_file_name, "a") as debug_logging_file:
            debug_logging_file.write(f"D {time.time()}: ")
            print(*args, **argv, file=debug_logging_file)
            debug_logging_file.flush()



KEEP_ALIFE = b'\x00'
REQUEST_CONNECTION = b'\x01'
CONNECTION_CONFIRMATION = b'\x02'
CONNECTION_CHECK = b'\x03'
CONNECTION_CHECK_CONFIRMATION = b'\x04'
PING_REQUEST = b'\x05'
ECHO_ON_PING = b'\x06'
DEBUG_MESSAGE = b'\x07'
DATA = b"\x11"
END = b"\x12"


CHUNK=1024

audio = pyaudio.PyAudio()
info = audio.get_host_api_info_by_index(0)
num = info.get('deviceCount')
for i in range(0, num):
    info = audio.get_device_info_by_host_api_device_index(0, i)
    print("Input device id ", info.get("index"), info.get("name"), "input channels:", info.get("maxInputChannels"), "output:", info.get("maxOutputChannels"))

print("По умолчанию:", audio.get_default_input_device_info()['index'])
input_channel = int(input("Номер: "))

channel = audio.get_default_output_device_info()['index']
print("Устройство вывода:", channel)
audio_stream = audio.open(format=pyaudio.paInt16,
                          channels=1,
                          input_device_index=input_channel,
                          output_device_index=channel,
                          rate=16000,
                          input=True,
                          output=True,
                          frames_per_buffer=CHUNK)


def ping(connection, timeout=10):
        start_time = time.time()
        connection[0].sendto(PING_REQUEST, connection[1])
        try:
            while True:
                data = connection[2].get(timeout=timeout)
                print("Полученны данные в ping", data)
                if data[:1] == ECHO_ON_PING:
                    delta_time = time.time() - start_time
                    if delta_time:
                        return delta_time
                    else:
                        return 0.0001
        except queue.Empty:
            return False


def send_audio_stream(connections):
    deb_print("! start send audio")
    try:
        while running:
            data = audio_stream.read(CHUNK, exception_on_overflow=False)
            for socket, client, incoming_packets in connections:
                # audio_stream.write(data)
                socket.sendto(DATA + data, client)
                deb_print("send", data)
    except Exception as e:
        print("get error in send", e)


def incoming_handler(connections):
    try:
        global running
        while running:
            first = True
            all_data = None
            on_delete = None
            if connections:
                for i, connection in enumerate(connections):
                    socket, client, incoming_packets = connection
                    try:
                        data, addr = socket.recvfrom(9999)
                        deb_print("Get data", data, addr)
                        if data[:1] == PING_REQUEST:
                            socket.sendto(ECHO_ON_PING, client)
                            deb_print("Get PING req")
                        elif data[:1] == ECHO_ON_PING:
                            incoming_packets.put(ECHO_ON_PING)
                            deb_print("Get ECHO")
                        elif data[:1] == KEEP_ALIFE:
                            deb_print("Get KPL")
                        elif data[:1] == REQUEST_CONNECTION:
                            socket.sendto(CONNECTION_CONFIRMATION, client)
                            deb_print("get RQC, send CTC")
                        elif data[:1] == DATA:
                            #data = np.float32(data[1:])
                            _data = np.frombuffer(data[1:], dtype=np.int16).copy()
                            if first:
                                all_data = _data
                                first = False
                            else:
                                all_data += _data
                        elif data[:1] == END:
                            print("Один из участников вышел")
                            on_delete = i
                    except BlockingIOError as e:
                        pass
                    except ConnectionResetError as e:
                        print("Участник вне доступа, отключение")
                        on_delete = i
                    except Exception as e:
                        print('error in incoming_handler:', e, type(e))
                if not first:
                    # with open("audio_history.txt", "ab") as file:
                    #    file.write(all_data)
                    audio_stream.write(all_data.tobytes())
                    first = True
                if on_delete is not None:
                    print(connections.pop(on_delete), "отсоеденился")
                    on_delete = None
            else:
                time.sleep(0.1)
    except Exception as e:
        print("get error in reader", e)


action = input("Ваш порт(оставьте пустым если нужен случайный)")
if action:
    local_port = int(action)
else:
    local_port = get_random_port()
external_ip, external_port = get_my_addr(port=local_port)

print("Ваш ip и порт")
print(external_ip, external_port)
ip, port = input('Введите адресс и порт').split()
port = int(port)
socket = make_NAT_hole_socket(local_port, ip, port)
print("Соеденение установленно")

connections = [(socket, (ip, port), queue.Queue()),]

running = True
th = threading.Thread(target=incoming_handler, args=(connections,))
th.start()

print("Пинг...")
for connection in connections:
    print(*connection[1], "...")
    for i in range(4):
        ping_time = ping(connection, timeout=3)
        if ping_time:
            print(ping_time)
        else:
            print("Нет ответа")

input("нажмите Enter чтобы начать говорить")
th = threading.Thread(target=send_audio_stream, args=(connections,))
th.start()

while True:
    action = input("a - добавить участника e - завершить звонок")
    if action == 'a':
        action = input("Ваш порт(оставьте пустым если нужен случайный)")
        if action:
            local_port = int(action)
        else:
            local_port = get_random_port()
        external_ip, external_port = get_my_addr(port=local_port)

        print("Ваш ip и порт")
        print(external_ip, external_port)
        ip, port = input('Введите адресс и порт').split()
        port = int(port)
        socket = make_NAT_hole_socket(local_port, ip, port)
        print("Соеденение установленно")
        connections.append((socket, (ip, port), queue.Queue()))

        print("Пинг...")
        for i in range(4):
            ping_time = ping(connections[-1], timeout=3)
            if ping_time:
                print(ping_time)
            else:
                print("Нет ответа")


    elif action == 'e':
        for socket, client, incoming_packets in connections:
            socket.sendto(END, client)
        break


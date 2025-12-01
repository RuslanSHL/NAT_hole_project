import socket
import time
import random
import threading
import os
import queue


KEEP_ALIFE = b'\x00'
REQUEST_CONNECTION = b'\x01'
CONNECTION_CONFIRMATION = b'\x02'
CONNECTION_CHECK = b'\x03'
CONNECTION_CHECK_CONFIRMATION = b'\x04'
PING_REQUEST = b'\x05'
ECHO_ON_PING = b'\x06'
DEBUG_MESSAGE = b'\x07'


_alreadyused = set()

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


def stun(port, host="stun.ekiga.net"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.setblocking(0)
    server = socket.gethostbyname(host)
    work = True
    while work:
        sock.sendto(
            b"\x00\x01\x00\x00!\x12\xa4B\xd6\x85y\xb8\x11\x030\x06xi\xdfB",
            (server, 3478),
        )
        for i in range(20):
            try:
                ans, addr = sock.recvfrom(2048)
                work = False
                break
            except:
                time.sleep(0.01)

    sock.close()
    return socket.inet_ntoa(ans[28:32]), int.from_bytes(ans[26:28], byteorder="big")


def randomport():
    global _alreadyused
    p = random.randint(16000, 65535)
    while p in _alreadyused:
        p = random.randint(16000, 65535)
    _alreadyused.update({p})
    return p


class Session:
    def __init__(self, local_port=None, use_queue=True):
        self.use_queue = use_queue

        self.outgoing = queue.Queue()
        self.incoming = queue.Queue()
        self.last_incoming = None

        self.running = True
        self.socket = None
        self.client = None
        self.input_thread = None
        self.output_thread = None

        if local_port is None:
            self.local_port = randomport()
        else:
            self.local_port = local_port
        for i in range(10):
            stun(self.local_port)
        self.external_ip, self.external_port = stun(self.local_port)
        deb_print(f"get stun info: {self.external_ip} {self.external_port}")

    def make_connection(self, ip, port):
        deb_print(f"request connection on {ip} {port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.local_port))
        sock.setblocking(0)
        while True:
                sock.sendto(b"RQC", (ip, port))
                time.sleep(2)
                try:
                    data, addr = sock.recvfrom(9999)
                    sock.sendto(b"RQC", (ip, port))
                    sock.close()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind(('0.0.0.0', self.local_port))
                    # sock.setblocking(0)
                    self.socket = sock
                    self.client = (ip, port)
                    deb_print(f"Соедениение с {addr} установленно")
                    break
                except Exception as e:
                    print(e)
                    deb_print(f"E: get error {e} in process make_connection")

    def backlife_cycle(self):
        th = threading.Thread(target=self.incoming_handler)
        th.start()
        self.input_thread = th

        th = threading.Thread(target=self.outgoing_handler)
        th.start()
        self.output_thread = th

        deb_print("life cycle started")

    def incoming_handler(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(9999)
                deb_print("Get data: ", addr, data)
            except BlockingIOError as e:
                print(e)
                continue
            except Exception as e:
                deb_print("E: Get error: ", e)
                break
            if data[:4] == PING_REQUEST:
                self.socket.sendto(ECHO_ON_PING, self.client)
                deb_print("Get PING req")
            elif data[:4] == ECHO_ON_PING:
                self.incoming.put(ECHO_ON_PING)
                deb_print("Get ECHO")
            elif data[:4] == KEEP_ALIFE:
                deb_print("Get KPL")
            elif data[:4] == REQUEST_CONNECTION:
                self.socket.sendto(CONNECTION_CONFIRMATION, self.client)
                deb_print("get RQC, send CTC")
            elif data[:4] == CONNECTION_CHECK:
                self.socket.sendto(CONNECTION_CHECK_CONFIRMATION, self.client)
                deb_print("get CON CHECK")
            elif data[:4] == DEBUG_MESSAGE:
                print("Полученно сообщение", data[0:].decode("utf-8"), data.decode("utf-8"))
                deb_print("get MSG", data[0:].decode("utf-8"))
            elif data[:1] == CONNECTION_CHECK_CONFIRMATION:
                self.incoming.put(data)
                deb_print("get CON CHECK CONF")
            else:
                deb_print(f"Get {data} from {addr}")
                if self.use_queue:
                    self.incoming.put(data)
                else:
                    self.last_incoming = data

    def outgoing_handler(self):
        while True:
            if self.running:
                try:
                    data_on_send = self.outgoing.get(timeout=5)
                    self.socket.sendto(data_on_send, self.client)
                    deb_print(f"send {data_on_send}")
                except queue.Empty:
                    self.socket.sendto(KEEP_ALIFE, self.client)
                except Exception as e:
                    deb_print(f"error: {e}")
            else:
                break

    def check_connection(self, timeout=5):
        self.outgoing.put(CONNECTION_CHECK)
        try:
            while True:
                data = self.incoming.get(timeout=timeout)
                if data[:4] == CONNECTION_CHECK_CONFIRMATION:
                    return True
        except queue.Empty:
            return False

    def ping(self, timeout=10):
        start_time = time.time()
        self.outgoing.put(PING_REQUEST)
        try:
            while True:
                data = self.incoming.get(timeout=timeout)
                if data[:4] == ECHO_ON_PING:
                    delta_time = time.time() - start_time
                    if delta_time:
                        return delta_time
                    else:
                        return 0.0001
        except queue.Empty:
            return False

    def stop(self):
        self.running = False
        deb_print("running = False")

    def __exit__(self):
        print("завершение работы класса")
        self.running = False



#ЗАЧЕМ?
import socket
import time
import random
import os

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


REQUEST_CONNECTION = b'\x01'
CONNECTION_CONFIRMATION = b'\x02'
_alreadyused = set()


def get_my_addr(port, host="stun.ekiga.net"):
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


def get_random_port():
    global _alreadyused
    p = random.randint(16000, 65535)
    while p in _alreadyused:
        p = random.randint(16000, 65535)
    _alreadyused.update({p})
    return p


def make_NAT_hole_socket(local_port, ip, port):
    deb_print(f"request connection on {ip} {port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', local_port))
    sock.setblocking(0)
    while True:
            sock.sendto(REQUEST_CONNECTION, (ip, port))
            time.sleep(2)
            try:
                data, addr = sock.recvfrom(9999)
                sock.sendto(REQUEST_CONNECTION, (ip, port))
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('0.0.0.0', local_port))
                # sock.setblocking(0)
                deb_print(f"Соедениение с {addr} установленно")
                break
            except Exception as e:
                print(e)
                deb_print(f"E: get error {e} in process make_connection")
    return sock

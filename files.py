from p2p import Session, DEBUG_MESSAGE
from tkinter import filedialog
import time
import queue


READINESS_CHECK = '\x10'
CONFIRMATION_OF_READINESS = '\x11'
DATA = '\x12'

def main():
    action = input("Ваш порт(оставьте пустым если нужен случайный)")
    if action:
        sess = Session(local_port=int(action))
    else:
        sess = Session()
    print("Ваш ip и порт")
    print(sess.external_ip, sess.external_port)
    ip, port = input('Введите адресс и порт').split()
    port = int(port)
    sess.make_connection(ip, port)
    print("Соеденение установленно")
    sess.backlife_cycle()
    print("Цикл запущен")
    c = 0
    while True:
        print("Проверка соеденения...")
        if sess.check_connection(timeout=1):
            print("Соеденение работает")
            break
        else:
            print("Соеденение не работает")
            print("Ожидание и повторная проверка...")
            c += 1
            if c > 3:
                if 'n' == input("Продолжить попытки? (y(es)/n(o))"):
                    break
                else:
                    c = 0
            time.sleep(1)

    print("Пинг...")
    for i in range(4):
        result = sess.ping(timeout=2)
        if result:
            print(f"Пинг успешен: {result} сек")
        else:
            print(f"Нет ответа")


    while True:
        action = input("p - принять файл, s - отправить")
        if action == "s":
            print("Выбор файла")
            sess.outgoing.put(DEBUG_MESSAGE + b'start send')
            file_path = filedialog.askopenfilename()
            # file_path = 'image_test.png'
            print("Файл выбран")
            if file_path:
                sess.outgoing.put(DEBUG_MESSAGE + b'trying send RDY')
                sess.outgoing.put(b"RDY")
                while True:
                    try:
                        data = sess.incoming.get(timeout=1)
                        print('\t', data)
                        if data == b'RDY':
                            print("Полученно")
                            break
                    except queue.Empty:
                        sess.outgoing.put(b"RDY")
                print("Готов")
                time.sleep(3)
                print("Начинаем")
                with open(file_path, "rb") as file:
                    # window_size = 8192
                    window_size = 1024
                    need_for_window_size = 5
                    count_succerfuly = 0
                    count_no_succerfuly = 0
                    past_size_packet = 0
                    data_chunk = file.read(window_size)
                    while True:
                        if data_chunk:
                            print(len(data_chunk), file.tell())
                            past_size_packet = len(data_chunk)
                            sess.outgoing.put(b"DTA" + data_chunk)
                            print("пакет данных отправлен")
                            sess.outgoing.put(b"SND")
                            try:
                                data = sess.incoming.get(timeout=5)
                                if data == b'GTS':  # get succerfuly
                                    count_succerfuly += 1
                                    if count_succerfuly >= need_for_window_size:
                                        # window_size *= 2
                                        count_succerfuly = 0
                                    data_chunk = file.read(window_size)
                                elif data == b'GTN':  # no get data
                                    file.seek(file.tell() - past_size_packet)
                                    window_size //= 2
                                    print('window_size now', window_size)
                                    time.sleep(1)
                                    count_no_succerfuly += 1
                                    if count_no_succerfuly >= 3:
                                        need_for_window_size += 5
                                    data_chunk = file.read(window_size)
                            except queue.Empty:
                                print("Нет ответа")
                        else:
                            print("Данные закончились")
                            sess.outgoing.put(b"END")
                            break
                        # time.sleep(0.05)
        elif action == 'p':
            sess.outgoing.put(DEBUG_MESSAGE + b'start get')
            file_path = filedialog.asksaveasfilename()
            if file_path:
                while True:
                    try:
                        data = sess.incoming.get(timeout=5)
                        if data == b'RDY':
                            print('get ready')
                            break
                    except queue.Empty:
                        pass

                with open(file_path, "wb") as file:
                    sess.outgoing.put(b"RDY")
                    print("Готов")
                    data_get = False
                    while True:
                        data = sess.incoming.get()
                        print("Get", data[:3])
                        if data[:3] == b"DTA":
                            print('get data')
                            data_get = True
                            file.write(data[3:])
                        elif data[:3] == b"END":
                            print("END")
                            break
                        elif data[:3] == b'SND':
                            if data_get:
                                sess.outgoing.put(b'GTS')
                            else:
                                sess.outgoing.put(b'GTN')
                                print('data no get')
                            data_get = False
                    print("Файл передан")


if __name__ == "__main__":
    main()

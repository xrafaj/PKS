import socket
import struct
import crcmod
import os
import time
import threading

POCET_FRAGMENTOV_ZALOHA = 20

#stop_threads = False


def keep_alive(IP, PORT, MSG, SOCKET):                                          # odosielanie keep alive sprav
    temp_counter = 0                                                            # každých 10s, avšak max 12x
    while True:
        time.sleep(10)
        try:
            SOCKET.sendto(MSG, (IP, PORT))
        except:
            print('Server connection was closed.')
            break
        temp_counter = temp_counter + 10
        if temp_counter > 120:
            break


def split_len(seq, length):                                                     # rozfragmentovanie zadaneho
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def main_function():                                                            # hlavna funkcia, obsahuje vyber
    global stop_threads                                                         # klienta / serveru
    local_input = input('Please type 1 for client, 2 for server.\n')
    if local_input == '1':
        print('Client')                                                         # init základných hodnot, portov
        crc16_func = crcmod.predefined.mkCrcFun('crc-16')                       # definicia CRC funkcie
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('Put server / communication IP address (127.0.0.1)')
        socket_client_IP = input()
        print('Put server port to send data to (1234)')
        socket_client_PORT = int(input())

        socket_client_PORT2 = 1235

        socket_client.bind((socket_client_IP, socket_client_PORT2))

        what_to_do = -1
        TYPE = b'a'
        POCET_FRAGMENTOV = 0
        PORADOVE_CISL0 = 0
        VELKOST = 0
        CRC = 0

        header = struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC)
                                                                                # 3 way handshake packetmi b'a' a b'b'
        socket_client.sendto(header, (
            socket_client_IP, socket_client_PORT))

        data, address = socket_client.recvfrom(1472)
        data = struct.unpack('ciiii', data[:20])
        if data[0] == b'b':                                                     # úspešný 3w handshake
            print('Server successfully responded.')
        while 1:
            if what_to_do == 0:                                                 # spustenie klient menu
                message_lcl = struct.pack('ciiii', b'X', 0, 0, 0, CRC)
                t1 = threading.Thread(target=keep_alive,
                                      args=(socket_client_IP, socket_client_PORT, message_lcl, socket_client))
                t1.start()
            what_to_do = input('Please, choose an option -> 1 - Send file | 2 - Quit (return 0) | 3 - Send text\n')
            if what_to_do == '1':                                               # posielanie suboru
                file_location = input('Please put file location\n')             # zadanie init udajov
                f = open(file_location, 'rb')
                print(os.path.abspath(file_location))
                f_data = f.read()
                f.close()
                fragments_len = int(input(
                    'Please put size of 1 fragmental (possible -> 1-1452) In case of other input, program crashes.\n'))
                if bytes(f_data) < bytes(fragments_len):
                    print(bytes(f_data))
                    print(bytes(fragments_len))
                    print('Too low')
                fragments = split_len(f_data, fragments_len)

                print('Total size of fragments in bytes :')
                print(len(f_data))
                print('Total amount of fragments :')                            # vlozenie indexu na chybu
                print(len(fragments))                                           # ak vlozime 0, chyba sa nevykona
                vynutena_chyba = int(
                    input('On purpose error simulation, please put number from 1 to ' + str(len(fragments)) + '\n'))
                print('Sending file... please wait.')

                last_one = 0                                                    # vypocty dlzky fragmentov
                TYPE = b'c'                                                     # poctu sprav a tak podobne
                POCET_FRAGMENTOV = POCET_FRAGMENTOV_ZALOHA
                counter = POCET_FRAGMENTOV
                pocet_sprav = len(fragments) % POCET_FRAGMENTOV
                if pocet_sprav == 0:
                    pocet_sprav = len(fragments) // POCET_FRAGMENTOV
                else:
                    pocet_sprav = len(fragments) // POCET_FRAGMENTOV
                    if len(fragments) % POCET_FRAGMENTOV != 0:
                        pocet_sprav = pocet_sprav + 1

                index = 0                                                       # samotne posielanie fragmentov
                PORADOVE_CISL0 = 1                                              # aj resending fragmentov
                for i in range(pocet_sprav):
                    while counter != 0:                                         # tento while posiela balík napr. po 5 / 10 / 20 podľa nastavenia hore
                        if pocet_sprav * POCET_FRAGMENTOV - POCET_FRAGMENTOV <= index and len(fragments) % \
                                POCET_FRAGMENTOV != 0 and last_one == 0:
                            last_one = 1
                            POCET_FRAGMENTOV = len(fragments) % POCET_FRAGMENTOV                                        # posledný balík nemusí mať rovnakú veľkosť ako ostatné... preto dopočítame jeho veľkosť modulom
                        if index == len(fragments):
                            break
                        VELKOST = len(fragments[index])
                        message = struct.pack('ciii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST)
                        CRC = crc16_func(message + fragments[index])                                # vypočet CRC a dopacknutie CRCčka
                        if vynutena_chyba != 0:
                            if index == vynutena_chyba - 1:
                                CRC = CRC - 1
                        message = struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC)
                        message = message + fragments[index]
                        socket_client.sendto(message, (socket_client_IP, socket_client_PORT))       # odoslanie správy
                        counter = counter - 1
                        PORADOVE_CISL0 = PORADOVE_CISL0 + 1
                        index = index + 1
                    msg = struct.pack('ciii', TYPE, POCET_FRAGMENTOV, 0, 0)                         # tuto dochádza k príchodu reportu o poškodených / neprijatých packetoch
                    CRC = crc16_func(msg)                                                           # následne vo fore odosielame opravené fragmenty, ktoré server žiada
                    msg = struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, 0, 0, CRC)
                    socket_client.sendto(msg, (socket_client_IP, socket_client_PORT))
                    data, address = socket_client.recvfrom(1472)
                    z = list(data[20:])
                    if len(z) != 0:
                        prev_index = index - POCET_FRAGMENTOV
                        for k in range(len(z)):
                            if z[k] != -1:
                                message = struct.pack('ciii', b'r', POCET_FRAGMENTOV, prev_index + z[k], 0)
                                CRC = crc16_func(message + fragments[prev_index + z[k]])
                                message = struct.pack('ciiii', b'r', POCET_FRAGMENTOV, prev_index + z[k], 0, CRC)
                                message = message + fragments[prev_index + z[k]]
                                socket_client.sendto(message, (socket_client_IP, socket_client_PORT))
                    if index == len(fragments):                                                     # odoslanie finálnej spravy s názvom súboru
                        message = struct.pack('ciii', b'F', 0, 0, 0)
                        CRC = crc16_func(message + file_location.encode())
                        print('Successfully sent.\n')
                        message = struct.pack('ciiii', b'F', 0, 0, 0, CRC)
                        message = message + file_location.encode()
                        socket_client.sendto(message, (socket_client_IP, socket_client_PORT))
                        break
                    counter = POCET_FRAGMENTOV
                    PORADOVE_CISL0 = 1
                what_to_do = 0
            if what_to_do == '2':                                                                   # moznost ukoncenia programu a zatvorenie socketu
                TYPE = b'E'
                CRC = 0
                try:
                    socket_client.sendto(struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC), (
                        socket_client_IP, socket_client_PORT))
                except:
                    print('Server connection was already closed.')
                stop_threads = True
                socket_client.close()
                menu()
                # exit(0)

            if what_to_do == '3':                                                                   # posielanie spravy
                buffer = input('Please put your desired message\n')                                 # zadanie init hodnoty t.j. celu spravu na vstup
                fragments_len = int(input(
                    'Please put size of 1 fragmental (possible -> 1-1452) In case of other input, program crashes.\n'))
                print('Total size of fragments in bytes: ' + str(len(buffer)))
                fragments = split_len(buffer, fragments_len)
                print('Amount of fragments :' + str(len(fragments)))

                last_one = 0                                                                        # vypocet velkosti fragmentov, poctu sprav atd.
                TYPE = b'c'
                POCET_FRAGMENTOV = POCET_FRAGMENTOV_ZALOHA
                counter = POCET_FRAGMENTOV
                pocet_sprav = len(fragments) % POCET_FRAGMENTOV
                if pocet_sprav == 0:
                    pocet_sprav = len(fragments) // POCET_FRAGMENTOV
                else:
                    pocet_sprav = len(fragments) // POCET_FRAGMENTOV
                    if len(fragments) % POCET_FRAGMENTOV != 0:
                        pocet_sprav = pocet_sprav + 1
                                                                                                    # zistenie indexu, kde vykonat chybu, v prípade zadania 0 sa chyba nevykoná
                vynutena_chyba = int(
                    input('On purpose error simulation, please put number from 1 to ' + str(len(fragments)) + '\n'))
                print('Sending message... Please wait.')

                index = 0
                PORADOVE_CISL0 = 1
                TYPE = b's'
                for i in range(pocet_sprav):                                                        # už samotné posielanie, rovnaké prakticky ako u súboru s rozdielom .encode() a .decode() funkcii
                    while counter != 0:                                                             # dopočet posledného balíku, ktorý nemusí mať rovnakú veľkosť, pretože skončí skorej
                        if pocet_sprav * POCET_FRAGMENTOV - POCET_FRAGMENTOV <= index and len(fragments) % \
                                POCET_FRAGMENTOV != 0 and last_one == 0:
                            last_one = 1
                            POCET_FRAGMENTOV = len(fragments) % POCET_FRAGMENTOV
                        if index == len(fragments):
                            break
                        VELKOST = len(fragments[index])
                        message = struct.pack('ciii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST)
                        CRC = crc16_func(message + fragments[index].encode())                                           # vyrátanie CRC, vnútenie chyby
                        if vynutena_chyba != 0:
                            if index == vynutena_chyba - 1:
                                CRC = CRC - 1
                        message = struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC)
                        message = message + fragments[index].encode()
                        socket_client.sendto(message, (socket_client_IP, socket_client_PORT))
                        counter = counter - 1
                        PORADOVE_CISL0 = PORADOVE_CISL0 + 1
                        index = index + 1
                    msg = struct.pack('ciii', TYPE, POCET_FRAGMENTOV, 0, 0)
                    CRC = crc16_func(msg)
                    msg = struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, 0, 0, CRC)                       # odosielanie info a koncu balíka
                    socket_client.sendto(msg, (socket_client_IP, socket_client_PORT))
                    data, address = socket_client.recvfrom(1472)
                    z = list(data[20:])
                    if len(z) != 0:                                                                     # preposlanie vynechanych / chybnych fragmentov, ktore si server ziada
                        prev_index = index - POCET_FRAGMENTOV
                        for k in range(len(z)):
                            if z[k] != -1:
                                message = struct.pack('ciii', b'g', POCET_FRAGMENTOV, prev_index + z[k], 0)
                                CRC = crc16_func(message + fragments[prev_index + z[k]].encode())
                                message = struct.pack('ciiii', b'g', POCET_FRAGMENTOV, prev_index + z[k], 0, CRC)
                                message = message + fragments[prev_index + z[k]].encode()
                                socket_client.sendto(message, (socket_client_IP, socket_client_PORT))
                    if index == len(fragments):                                                         # poslanie o tom, že už prišlo všetko a môžeme teda napr. na serveri už vypísať túto správu
                        message = struct.pack('ciii', b'G', 0, 0, 0)
                        CRC = crc16_func(message)
                        message = struct.pack('ciiii', b'G', 0, 0, 0, CRC)
                        print('Succesfully sent.\n')
                        socket_client.sendto(message, (socket_client_IP, socket_client_PORT))
                        break
                    counter = POCET_FRAGMENTOV
                    PORADOVE_CISL0 = 1
                    what_to_do = 0
    if local_input == '2':                                                                          # server
        print('Server')                                                                             # zadanie init hodnot, v zadani som nenasiel, ze by sme mali zadavat IP serveru ale pre
                                                                                                    # istotu to naimplementujem a zakomentujem, čo je ale myslím detail
        crc16_func = crcmod.predefined.mkCrcFun('crc-16')
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #socket_server_PORT = int(input('Please input server IP (127.0.0.1)\n'))                    # urobil som tak tu
        socket_server_IP = '127.0.0.1'
        print('Please put server port (1234):')
        socket_server_PORT = int(input())
        socket_client_PORT2 = 1235
        print('Waiting for response...')
                                                                                                    # init servera
        socket_server.bind((socket_server_IP, socket_server_PORT))

        TYPE = b''
        data, address = socket_server.recvfrom(1472)
        data = struct.unpack('ciiii', data[:20])
        if data[0] == b'a':                                                                         # 3 way handshake
            print('Client connected.')
        POCET_FRAGMENTOV = 0
        PORADOVE_CISL0 = 0
        VELKOST = 0
        CRC = 0

        whole_array = []
        file_size = 0
        chybne_fragmenty = []
        curr_index = 0
        cntr = 0
        first_packet = 1
        temp_array = []
        if data[0] == b'a':                                                                         # 3 way handshake - potvrdenie
            TYPE = b'b'
            socket_server.sendto(struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC), (
                socket_server_IP, socket_client_PORT2))

        while 1:                                                            # cyklus pre prijímanie paketov
            try:
                socket_server.settimeout(45)                                # timeout 45 sekúnd na prijatie prvej správy od spustenia, pri hocijakej správe okrem keep-alive sa nastaví na None
                data, address = socket_server.recvfrom(1472)
                data_local = struct.unpack('ciiii', data[:20])
                CRC_local = crc16_func(data[:16] + data[20:])               # výratanie CRC
                if data_local[0] == b'X':                                   # sprava keep alive
                    socket_server.settimeout(None)
                    socket_server.settimeout(45)
                elif data_local[0] == b'E':                                 # sprava EXIT
                    socket_server.settimeout(None)
                    socket_server.close()
                    menu()
                    # exit(0)
                elif data_local[0] == b'c':                                 # sprava fragmentu suboru
                    socket_server.settimeout(None)
                    if first_packet == 1:                                   # v pripade ze ide o prvy fragment v akt baliku, urobi sa pole fragmentov, ktore maju prist v baliku
                        first_packet = 0
                        temp_array = []
                        for ff in range(data_local[1]):
                            temp_array.append(ff)
                    TYPE = b'c'
                    if data_local[2] != 0:                                  # v prípade, že nejde o špeciálny fragment a sedí CRC tak zapisujeme, ak nesedí CRC, prídame do chyby
                        if data_local[4] != CRC_local:
                            print('Incorrect packet number ' + str(curr_index + data_local[2] - 1))
                            chybne_fragmenty.append(data_local[2] - 1)
                        else:
                            cntr = cntr + 1
                            tmp = data_local[2] - 1                         # if tmp kontroluje, či už nejde o duplikátny fragment
                            if tmp in temp_array:
                                #print('Array ' + str(temp_array))
                                whole_array.insert(curr_index + data_local[2] - 1, data[20:])
                                print('Received packet number ' + str(
                                    curr_index + data_local[2] - 1) + ' with size of ' + str(data_local[3]) + ' bytes.')
                                file_size = file_size + data_local[3]
                                temp_array[data_local[2] - 1] = -1
                    if data_local[2] == 0 and data_local[4] == CRC_local:   # koniec balíku
                        print('End of packet.')
                        first_packet = 1
                        for kk in range(len(temp_array)):                   # spojenie chybnych(zle CRC) a neprijatých a nasledne redukcia z [ -1, -1, -1, -1, 5 ] na [ 5 ] , kde je jasné, že posledný fragment neprišiel
                            if temp_array[kk] != -1:
                                if len(chybne_fragmenty) != 0:
                                    for zz in range(len(chybne_fragmenty)):
                                        if chybne_fragmenty[zz] == temp_array[kk]:
                                            break
                                        elif zz == len(chybne_fragmenty) - 1:
                                            chybne_fragmenty.append(temp_array[kk])
                                else:
                                    chybne_fragmenty.append(temp_array[kk])

                        curr_index = curr_index + data_local[1]
                        redukovane_chybne = []

                        if len(chybne_fragmenty) != 0:                      # tu uz je spominana redukcia
                            for tt in range(len(chybne_fragmenty)):
                                if chybne_fragmenty[tt] != -1:
                                    redukovane_chybne.append(chybne_fragmenty[tt])

                        print('Corrupted or not received files: (n-1)th in package')            # Odoslanie array-u chybných a správa na výpis o tom, čo chýbalo
                        print(redukovane_chybne)
                        print('I am sending request to get them again.')
                        print('-------------------')
                        socket_server.sendto(
                            struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC) +
                            bytearray(redukovane_chybne), (socket_server_IP, socket_client_PORT2))
                        temp_array = []
                elif data_local[0] == b'r':                                 # sprava typu RESEND, kde sa vracaju opravene baliky, ich nasledny zapis
                    socket_server.settimeout(None)
                    if CRC_local == data_local[4]:
                        for hh in range(len(chybne_fragmenty)):
                            if chybne_fragmenty[hh] != -1:
                                if data_local[2] == curr_index + chybne_fragmenty[hh] - data_local[1]:
                                    chybne_fragmenty[hh] = -1
                                    print('Successfully re-received packet number ' + str(data_local[2]))
                                    print('-------------------')
                                    file_size = file_size + data_local[3]
                                    whole_array.insert(data_local[2], data[20:])
                elif data_local[0] == b'F':                                # sprava type FINAL, kde vlastne dochádza názov súboru, ktorý sa pridá k predefinovanej ceste a tam sa súbor vytvorí a zapíše
                    socket_server.settimeout(None)
                    if CRC_local == data_local[4]:
                        print('Received last packet containing name of the file....')
                        print(data[20:].decode())
                        file_name = data[20:].decode()                      # decodovanie nazvu suboru
                        ttt_size = 0
                        for ttt in range(len(whole_array)):                 # zistenie velkosti a dlzky
                            ttt_size = ttt_size + len(whole_array[ttt])
                        print('Saving as ' + file_name + ' with size of ' + str(ttt_size) + ' bytes in ' + str(len(whole_array)) + ' fragments.')
                        file_size = 0
                        save_path = 'C:/Users/Tomas/PycharmProjects/pks/files'
                        abs_file_path = os.path.join(save_path, file_name)          # definicia absolutnej cesty
                        file = open(abs_file_path, 'wb')

                        print(os.path.abspath(abs_file_path))
                        for i in range(len(whole_array)):
                            file.write(bytearray(whole_array[i]))
                        file.close()                                                # reset hodnot a zatvorenie suboru
                        whole_array = []
                        chybne_fragmenty = []
                        curr_index = 0
                        cntr = 0
                        POCET_FRAGMENTOV = 0
                        PORADOVE_CISL0 = 0
                        VELKOST = 0
                        CRC = 0
                        TYPE = 0
                        first_packet = 1
                        print('Waiting for response...')
                elif data_local[0] == b's':                                         # sprava typu SPRAVA, kde pried text
                    socket_server.settimeout(None)
                    if first_packet == 1:                                           # v prvom zbehnutí vytvoríme, čo všetko musí prísť v danom balík
                        first_packet = 0
                        temp_array = []
                        for ff in range(data_local[1]):
                            temp_array.append(ff)
                    TYPE = b's'
                    if data_local[2] != 0:                                          # v pripade ze nejde o specialnu spravu, ideme zapisovat
                        TYPE = b's'
                        if data_local[4] != CRC_local:                              # v pripade, ze nesedi CRC, pridame do chybnych
                            print('Incorrect packet number ' + str(curr_index + data_local[2] - 1))
                            chybne_fragmenty.append(data_local[2] - 1)
                        else:                                                       # ak sedi, pridame do array-u whole_array
                            cntr = cntr + 1
                            tmp = data_local[2] - 1
                            if tmp in temp_array:
                                print('Received packet number ' + str(
                                    curr_index + data_local[2] - 1) + ' with size of ' + str(data_local[3]) + ' bytes.')
                                whole_array.insert(curr_index + data_local[2] - 1, data[20:].decode())
                                temp_array[data_local[2] - 1] = -1
                    if data_local[2] == 0 and CRC_local == data_local[4]:           # ak skončilo resp. ide o nultý fragment / koncový, odosielame chybné
                        first_packet = 1
                        for kk in range(len(temp_array)):                           # spojenie a redukcia rovnaká ako u súborov
                            if temp_array[kk] != -1:
                                if len(chybne_fragmenty) != 0:
                                    for zz in range(len(chybne_fragmenty)):
                                        if chybne_fragmenty[zz] == temp_array[kk]:
                                            break
                                        elif zz == len(chybne_fragmenty) - 1:
                                            chybne_fragmenty.append(temp_array[kk])
                                else:
                                    chybne_fragmenty.append(temp_array[kk])
                        curr_index = curr_index + data_local[1]
                        redukovane_chybne = []

                        if len(chybne_fragmenty) != 0:                              # redukcia
                            for tt in range(len(chybne_fragmenty)):
                                if chybne_fragmenty[tt] != -1:
                                    redukovane_chybne.append(chybne_fragmenty[tt])
                                    # chybne_fragmenty[tt] = -1

                        print('Corrupted or not received files: (n-1)th in package')       # vypis, ktore sa vyziadaju nanovo
                        print(redukovane_chybne)
                        print('I am sending request to get them again.')
                        print('-------------------')
                        socket_server.sendto(
                            struct.pack('ciiii', TYPE, POCET_FRAGMENTOV, PORADOVE_CISL0, VELKOST, CRC) +
                            bytearray(redukovane_chybne), (socket_server_IP, socket_client_PORT2))
                        temp_array = []
                elif data_local[0] == b'g':                 # sprava RESEND pre spravu
                    socket_server.settimeout(None)
                    if CRC_local == data_local[4]:
                        for hh in range(len(chybne_fragmenty)):
                            if chybne_fragmenty[hh] != -1:
                                if data_local[2] == curr_index + chybne_fragmenty[hh] - data_local[1]:
                                    chybne_fragmenty[hh] = -1
                                    print('Successfully re-received packet number ' + str(data_local[2]))
                                    print('-------------------')
                                    whole_array.insert(data_local[2], data[20:].decode())
                elif data_local[0] == b'G':                 # sprava FINAL pre spravu
                    socket_server.settimeout(None)
                    if CRC_local == data_local[4]:
                        print('Received ending packet')
                        print('Amount of fragments : ' + str(len(whole_array)))             # spojenie fragmentov a nasledny vypis, z dovodu lahsieho vyratania
                        whole_array = ''.join([str(elem) for elem in whole_array])
                        print('Total size in bytes : ' + str(len(whole_array)))
                        print(whole_array)
                        whole_array = []                                                    # reset hodnot
                        chybne_fragmenty = []
                        curr_index = 0
                        cntr = 0
                        POCET_FRAGMENTOV = 0
                        PORADOVE_CISL0 = 0
                        VELKOST = 0
                        CRC = 0
                        TYPE = 0
                        first_packet = 1
                        print('Waiting for response...')
            except:                                         # v pripade neodpovede do 45s návrat do menu
                print('No response.')
                print('Exiting...')
                socket_server.close()
                menu()


def menu():
    local_menu_input = input('Please tell me what to do... !s to start | !q to quit\n')
    if local_menu_input == '!s':
        main_function()
    if local_menu_input == '!q':
        exit(0)


menu()

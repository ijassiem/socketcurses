import socket
import pickle
import multiprocessing
import time
import curses
import datetime

HEADERSIZE = 10
IDSIZE = 5
IPV4 = socket.AF_INET
TCP = socket.SOCK_STREAM
PORT = 1234
#IPADDRESS = 'dbelab04'
IPADDRESS = 'localhost' # localhost or 127.0.0.1

def comms(shared_dict):
    s = socket.socket(IPV4, TCP)  # create socket object
    s.connect((IPADDRESS, PORT))  # waits here and attempt connection to server
    while True:
        full_msg = b''  # create empty variable
        new_msg = True  # set new_msg flag
        while True:
            msg = s.recv(16)  # buffer size 16 bytes for incoming message
            if new_msg:
                msg_len = int(msg[:HEADERSIZE])  # convert value in HEADER(expected message length) to int
                new_msg = False  # clear new_msg flag

            full_msg += msg  # append messages

            if len(full_msg) - HEADERSIZE == msg_len:  # execute when complete message is received based on size indicated in HEADER
                matrix_received = pickle.loads(full_msg[HEADERSIZE + IDSIZE:])
                #print matrix_received
                shared_dict['t'] = matrix_received
                new_msg = True  # set new_msg flag
                full_msg = b""  # clear/empty message

def pr(shared_dict):
    while True:
        print 'from pr:', shared_dict['t']
        time.sleep(2)

def dateinfo(shared_dict):
    #shared_dict['t'] = str(datetime.datetime.now())  # update time info
    x = 9*2
    shared_dict['t'] = x  # update time info

def dspl_scr(stdscr, shared_dict):
    curses.curs_set(True)  # blinking cursor invisible
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)  # set colors
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLUE)  # set colors
    curses.init_pair(3, curses.COLOR_BLUE, -1)  # set colors

    while True:
        stdscr.addstr(0, 0, str(shared_dict['t']), curses.color_pair(1))  # add string to screen
        stdscr.refresh()  # update screen
        time.sleep(2)  # delay
        stdscr.clear()  # clear screen
        stdscr.addstr(2, 0, 'Good bye', curses.color_pair(1))  # add string to screen
        stdscr.refresh()  # update screen
        time.sleep(2)  # delay
        stdscr.clear()  # clear screen

def dspl_scr_no_wrapper(shared_dict):
    stdscr = curses.initscr()
    curses.start_color()  # init colors
    # init_pair(color_pair, foreground, background)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)  # set colors
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLUE)  # set colors
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_RED)  # set colors
    # tweak terminal settings
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(False)
    # write something on the screen
    stdscr.addstr(1, 1, str(shared_dict['t'][0]), curses.color_pair(1) + curses.A_BOLD)
    # update the screen
    stdscr.refresh()
    # wait for 2 seconds
    time.sleep(2)
    # clear the screen
    stdscr.clear()
    # close the application
    curses.endwin()

def draw(stdscr, shared_dict):
    from decimal import Decimal

    def fexp(number):
        (sign, digits, exponent) = Decimal(number).as_tuple()
        return len(digits) + exponent - 1

    def fman(number):
        return Decimal(number).scaleb(-fexp(number)).normalize()

    # Clear screen
    stdscr.clear()
    lines = curses.LINES
    cols = curses.COLS

    matrix = shared_dict['t']

    m_rows = len(matrix)
    m_rows = m_rows+(m_rows/2)
    m_cols = len(matrix[0])
    #find max number size in matrix
    max_num =  max([x for x in [j for i in matrix for j in i] if isinstance(x,int)])
    colw = fexp(max_num) + 1
    if colw < 9: colw=9
    blank_str = ' '*colw
    # Initialise windows and colours
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_BLACK, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)
    curses.init_pair(6, curses.COLOR_GREEN, -1)
    curses.init_pair(7, curses.COLOR_RED, -1)
    curses.init_pair(8, curses.COLOR_RED, -1)
    col_title = curses.newpad(1, m_cols*colw)
    row_title = curses.newpad(m_rows,colw)
    disp_wind = curses.newpad(m_rows,m_cols*colw)
    top_cornr = curses.newpad(1,colw)
    top_cornr.addstr(0,0, 'Rates', curses.A_BOLD | curses.A_UNDERLINE)
    # Data display block upper left-hand corner
    dminrow = 0
    dmincol = 0
    # Column title upper left-hand corner
    cminrow = 0
    cmincol = 0
    # Row title upper left-hand conrner
    rminrow = 1
    rmincol = 0
    # Data display window
    dwminrow = 1
    dwmincol = colw+1
    dwmaxrow = lines-1
    dwmaxcol = cols-1
    dwrows   = dwmaxrow-dwminrow
    dwcols   = dwmaxcol-dwmincol
    # Column title display window
    ctminrow = 0
    ctmincol = colw+1
    ctmaxrow = 0
    ctmaxcol = cols-1
    # Row title display window
    rtminrow = 1
    rtmincol = 0
    rtmaxrow = lines-1
    rtmaxcol = colw
    stdscr.nodelay(1)
    try:
        data_rdy = True
        blink = True
        #pool = ThreadPool(processes=1)
        while True:

            if data_rdy:
                data_rdy = False
                #thread_obj = pool.apply_async(get_rates, args=(switch_dict, ssh_list))
               # matrix = shared_dict['t']
                blankc = 0
                reverse = False
                for i,row in enumerate(matrix):
                    if i == 0:
                        for j,val in enumerate(row):
                            if j == 0:
                                pass
                                #col_title.addstr(i,j, 'Switch', curses.A_BOLD | curses.A_UNDERLINE)
                            else:
                                col_title.addstr(i,(j-1)*colw, '{0:>{1}}'.format(val,colw), curses.A_BOLD | curses.A_UNDERLINE)
                    else:
                        for j,val in enumerate(row):
                            if j == 0:
                                if val == 0:
                                    val = 'N/C'
                                col_pair = 1
                                if reverse: col_pair += 1
                                row_title.addstr(i+blankc-1,0, val, curses.color_pair(col_pair) | curses.A_BOLD)
                                if (i-1)%2 == 1:
                                    row_title.addstr(i+blankc-1+1,0,' ')
                            else:
                                width = colw-2
                                if not val:
                                    val = 0
                                man = fman(val)
                                exp = fexp(val)
                                if exp < 3:
                                    col_pair = 1
                                    if reverse: col_pair += 1
                                    rate = 'Bs'
                                    val = '{0:>{1}} {2}'.format(int(val),width-1,rate)
                                elif exp < 6:
                                    col_pair = 1
                                    if reverse: col_pair += 1
                                    rate = 'KB'
                                    man *= 10**(exp-3)
                                    man = man.normalize()
                                    if width-8 < 0:
                                        val = '{0:>{1}} {2}'.format(int(man),width-1,rate)
                                    else:
                                        val = '{0:{1}.1f} {2}'.format(man,width-1,rate)
                                elif exp < 9:
                                    col_pair = 3
                                    if reverse: col_pair += 1
                                    rate = 'MB'
                                    man *= 10**(exp-6)
                                    man = man.normalize()
                                    if width-8 < 0:
                                        val = '{0:>{1}} {2}'.format(int(man),width-1,rate)
                                    else:
                                        val = '{0:{1}.1f} {2}'.format(man,width-1,rate)
                                elif exp < 12:
                                    if man > 4.8:
                                        col_pair = 7
                                        if reverse: col_pair += 1
                                        col_title.addstr(0,(j-1)*colw, '{0:>{1}}'.format(matrix[0][j],colw), curses.color_pair(col_pair) | curses.A_BOLD | curses.A_UNDERLINE)
                                        row_title.addstr(i+blankc-1,0, matrix[i][0], curses.color_pair(col_pair) | curses.A_BOLD)
                                    else:
                                        col_pair = 5
                                        if reverse: col_pair += 1
                                    rate = 'GB'
                                    man *= 10**(exp-9)
                                    man = man.normalize()
                                    val = '{0:{1}.1f} {2}'.format(man,width-1,rate)
                                else:
                                    col_pair = 1
                                    rate = 'Bs'
                                    val = '{0:>{1}} {2}'.format(int(val),width-1,rate)
                                disp_wind.addstr(i+blankc-1,(j-1)*colw, val, curses.color_pair(col_pair))
                                if (i-1)%2 == 1:
                                    disp_wind.addstr(i+blankc-1+1,(j-1)*colw,' ')
                        if (i-1)%2 == 1:
                            blankc += 1
                            reverse = False #not(reverse)
                #prev_matrix = matrix
            else:
                char = stdscr.getch()
                if char == curses.ERR:
                    try:
                        #pass
                        matrix = shared_dict['t']
                        # if thread_obj.ready():
                        #     matrix = thread_obj.get()
                        data_rdy = True
                        if blink:
                            top_cornr.addstr(0,0, 'Rates', curses.A_BOLD | curses.A_UNDERLINE | curses.A_REVERSE)
                        else:
                            top_cornr.addstr(0,0, 'Rates', curses.A_BOLD | curses.A_UNDERLINE)
                            blink = not(blink)
                        # else:
                        #     time.sleep(0.1)
                    except:
                        return False
                else:
                    redraw = True
                    if char == curses.KEY_LEFT:
                        if dmincol > colw:
                            dmincol -= colw
                        else:
                            dmincol = 0
                    elif char == curses.KEY_RIGHT:
                        if dmincol < (m_cols-2)*colw - dwcols:
                            dmincol += colw
                        else:
                            dmincol = (m_cols-1)*colw - dwcols
                    elif char == curses.KEY_UP:
                        if dminrow > 0:
                            dminrow -= 1
                        else:
                            dminrow = 0
                    elif char == curses.KEY_DOWN:
                        if dminrow < m_rows-dwrows-2:
                            dminrow += 1
                        else:
                            dminrow = m_rows-dwrows-2
            # Shift titles with text
            cmincol = dmincol
            rminrow = dminrow
            disp_wind.refresh(dminrow,dmincol,dwminrow,dwmincol,dwmaxrow,dwmaxcol)
            col_title.refresh(cminrow,cmincol,ctminrow,ctmincol,ctmaxrow,ctmaxcol)
            row_title.refresh(rminrow,rmincol,rtminrow,rtmincol,rtmaxrow,rtmaxcol)
            top_cornr.refresh(0,0,0,0,1,colw-1)
    except KeyboardInterrupt:
        return True


if __name__ == '__main__':
    manager = multiprocessing.Manager()

    default_matrix = [
        [0, 'S1', 'S2', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 0, 'S11', 'S12', 'S13', 'S14', 'S15', 'S16', 'S17', 'S18'],
        ['L1 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L1  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L2 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L2  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L3 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L3  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L4 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L4  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L5 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L5  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L6 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L6  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L7 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L7  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L8 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L8  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L9 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L9  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L10 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L10  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L11 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L11  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L12 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L12  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L13 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L13  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L14 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L14  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L15 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L15  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L16 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L16  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L17 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L17  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L18 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L18  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L19 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L19  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L20 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L20  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L21 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L21  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L22 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L22  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L23 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L23  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L24 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L24  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L25 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L25  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L26 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L26  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L27 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L27  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L28 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L28  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L32 out', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ['L32  in', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

    shared_dict = manager.dict({'t': default_matrix})
    #stdscr = curses.initscr()

    p1 = multiprocessing.Process(target=comms, args=(shared_dict, ))
    #p2 = multiprocessing.Process(target=curses.wrapper, args=(dspl_scr, shared_dict))
    p3 = multiprocessing.Process(target=curses.wrapper, args=(draw, shared_dict))
    p1.start()  # start comms function
    # p2.start()  # start curses.wrapper function
    time.sleep(4) # delay wait to assign matrix value to shared_dict
    p3.start()  # start draw

    while True:
        time.sleep(3)











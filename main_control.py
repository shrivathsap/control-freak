'''Program that throws a message every when you browse for far too long. I have set 1 hour as the base limit, incrementing by hours, although the sampling rate and
checking what tasks are running can change the accuracy. However, in the span of one hour these small changes are insignifact, and good enough for me.
'''

import time, subprocess, winsound, datetime, signal
import tkinter as tk
import win32api, win32gui, win32con
import atexit
import threading
import sys
import csv

log_file = 'C:\\Python\\My Programs\\OS and scheduling and stuff\\log.csv'
shutdown_log = 'C:\\Python\\My Programs\\OS and scheduling and stuff\\final_test.txt'

large_font = ("Times New Roman", 12)
hour = 3600#seconds in an hour
sample_rate = 600#how long to sleep between samples. In the long run, 10 or 15 seconds may be easier on the system
closing_time = 20#I will stop execution at 20:00 hours, after that, you are free to do whatever. I think this is better than having an infinite while true loop

last = {"chrome.exe":time.time(), "miktex-texworks.exe":time.time()}
thresholds = {"chrome.exe":1, "miktex-texworks.exe":1}
bool_vars = {"chrome.exe":False, "miktex-texworks.exe":False}
msg_texts = {"chrome.exe":"browsing", "miktex-texworks.exe":"LaTex-ing"}

msg2 = "\n Go read a book or study or exercise."
msg3 = "\n For your own good, please stop!"

forever = True #a boolean that basically continues the loop
noted = False #have I noted the time of shut down or any other reason the program may have stopped? Only reason to include this is that signal and atexit
              #are sometimes triggered together

main_thread_id = win32api.GetCurrentThreadId()#obtain id of main thread to later send a quit message

wind_messages = [win32con.WM_DESTROY, win32con.WM_QUIT, win32con.WM_QUERYENDSESSION,
                   win32con.WM_ENDSESSION,
                   win32con.WM_QUIT,
                   win32con.WM_DESTROY,
                   win32con.WM_CLOSE]   #all possible signals windows might throw, I don't know which one it does throw while shutting down etc.

def is_program_on():#returns if chrome is open or not
    global bool_vars
    task_list = [line.split() for line in subprocess.getoutput("tasklist").splitlines()][3:]#need to run this every sample_rate seconds because the tasklist changes
    tasks = [task[0] for task in task_list]
    for item in bool_vars.keys():
        if item in tasks:
            bool_vars[item] = True
        else:
            bool_vars[item] = False
    
def popupmsg(task, msg):# throws a pop up message
    global bool_vars
    if task and not bool_vars[task]:#if bool_var, i.e. tex_on, chrome_on is false, then do nothing. This is only a contingency, it may happen that just before the popup happens
                           #I close the program, then there is no need for a popup. However, it is true that this function is called only when I have used the program
                           #for too long
        return
    else:
        popup = tk.Tk()
        popup.geometry("600x400")

        popup.wm_title("Warning!")
        label = tk.Label(popup, text = msg, font = large_font)
        label.pack(side = "top", fill = "x", pady = 10)
        B1 = tk.Button(popup, text = "Okay", command = popup.destroy)
        B1.pack(side = "bottom", fill = "x")
        popup.lift()#this and the next line are so that the pop up appears on the front, to the face and doesn't go away if clicked elsewhere
        popup.attributes("-topmost", True)
##        winsound.PlaySound("*", winsound.SND_ALIAS)#Icing on the cake, we can't have a warning without sound, can we?
        winsound.Beep(750, 200)#the previous one takes too long, but this is annoying as heck
        popup.mainloop()

def make_log():
    global bool_vars
    new_row = [None for _ in range(len(bool_vars))]
    tasks = list(bool_vars.keys())
    f = open(log_file, 'r')
    reader = csv.reader(f)
    mylist = list(reader)#can read f only once using csv.reader because the seek goes to the end. To reuse list(reader), need to pass an f.seek(0) first
    f.close()
    if set(list(bool_vars.values())) != {False}:#rewrite log_file only if there is any change
        for i in range(len(bool_vars)):#go through tasks to be monitored
            if bool_vars[tasks[i]]:#add datetime.datetime.now() only if task is currently active
                empty_row_found = False
                for row in mylist:#go through all rows till the first one that has an empty entry, this is the row immediately after the task was last performed
                    if row[i] == '':
                        empty_row_found = True
                        row[i] = datetime.datetime.now()#change the row entry to current date and time and stop scanning the rows
                        break
                if not empty_row_found:
                    new_row[i] = datetime.datetime.now()#in case there is no row with None in it, change the new rows ith entry and add it to mylist
                    mylist.append(new_row)#this happens only once because for subsequent tasks, there is already a row with None entry
        f = open(log_file, 'w', newline = '')#open the log_file and basically rewrite the entire thing.
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(mylist)
        f.close()        

def graceful_end(*args):
    global forever, noted, main_thread_id
    forever = False
    if not noted:
        with open(shutdown_log, 'a') as f:
            f.write("It works! "+str(datetime.datetime.now())+"\n")
        noted = True
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)

def wndProc(hWnd, message, wParam, lParam):
    global noted, forever
    if message in wind_messages or noted:#in case noted = True by other means (eg. closing time) then stop listening and close the window
        forever = False
        if not noted:
            with open(shutdown_log, 'a') as f:
                f.write("It works! "+str(datetime.datetime.now())+"\n")
            noted = True
        win32gui.PostQuitMessage(0)
        return 0               
    else:
        return win32gui.DefWindowProc(hWnd, message, wParam, lParam)

#win32gui.PumpMessages freezes the code, and doesn't move past its line - like a while True loop, therefore I have to resort to threads. Make one thread containing
#the main loop of the code - that which looks at whether chrome/tex are open etc and run pump messages elsewhere

def mainloop():
    global forever, noted, main_thread_id
    popupmsg(None, "You are under observation")
    ##while True:
    while int(str(datetime.datetime.now()).split()[1].split(':')[0]) < closing_time and forever:#go through the loop as long as it is not yet closing time and forever
        is_program_on()
        make_log()
    ##    print([time.time()-last[item] for item in last.keys()])
##        the following block keeps adding unnecessary "False" entries, so instead call make_log()
##        with open(log_file, 'a', newline = '') as f:
##            writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
##            writer.writerow([str(datetime.datetime.now()), bool_vars["chrome.exe"], bool_vars["miktex-texworks.exe"]])
        for item in bool_vars.keys():
            if time.time()-last[item]> hour*thresholds[item]:
                msg = "You have been {} for over {} hours.\n Time for a break.".format(msg_texts[item], thresholds[item])
                if thresholds[item] == 2:
                    msg += msg2
                if thresholds[item] >= 3:
                    msg += msg3
                popupmsg(item, msg)
                thresholds[item] += 1
            if not bool_vars[item]:
                last[item] = time.time()
                thresholds[item] = 1
        time.sleep(sample_rate)
    popupmsg(None, "You are good to go.")
    if not noted:
        with open(shutdown_log, 'a') as f:
            f.write("It works! " +str(datetime.datetime.now())+"\n")
            f.write("Stopping daemon thread\n")
        noted = True
        
    win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)#once the task is complete, send quit message to main thread to stop listening to windows

daemon_thread = threading.Thread(target = mainloop)
daemon_thread.daemon = True

def main():

    #Set up other potential ways - Ctrl-C/taskkill etc that could close the program
    win32api.SetConsoleCtrlHandler(graceful_end, True)            
##    atexit.register(graceful_end)
    signal.signal(signal.SIGINT, graceful_end)
    signal.signal(signal.SIGTERM, graceful_end)
    
    #Set up win32 window, but don't show it. This listens to shutdown/restart signals, and when it recieves them calls graceful_end
    wc = win32gui.WNDCLASS()
    wc.lpszClassName = 'Controller'
    wc.lpfnWndProc = wndProc
    wcAtom = win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindow(wcAtom, 'My Control App',
                0, 0, 0, 0, 0, 0, 0, 0, None)

    daemon_thread.start()
    win32gui.PumpMessages()    

if __name__ == '__main__':
    main()

import wx
import wx.adv

import sys
import time

import os

import subprocess 

from threading import Thread

TRAY_TOOLTIP = 'rs-backup-GUI'
TRAY_ICON = 'Flag-red.ico'

Myname = "rs-backup-GUI: A GUI front-end for rs_backup_suite"
Myversion = "Version 0.1"
Myauthor = "Copyright (C) 2018 Andrew Robinson"

MyNotice = "\nThis program is free software: you can redistribute it and/or modify \n\
it under the terms of the GNU General Public License as published by\n\
the Free Software Foundation, either version 3 of the License, or\n\
(at your option) any later version.\n\
\n\
This program is distributed in the hope that it will be useful,\n\
but WITHOUT ANY WARRANTY; without even the implied warranty of\n\
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n\
GNU General Public License for more details.\n\
\n\
You should have received a copy of the GNU General Public License\n\
along with this program.  If not, see <https://www.gnu.org/licenses/>"

def kill(proc_pid):
    command = ["c:\\cygwin64\\bin\\bash", "-lc", "kill -HUP -"+str(proc_pid)]
    subprocess.call(command, shell=True)

def getreturncode(filename):
    try:
        with open(filename, "r") as infile:
            r = infile.readline()
    except IOError:
        r = "Fail"
    return r
                  
     
def MyWorker():

    global kill_thread

    backup_freq = 600 #seconds

    command = ["c:\\cygwin64\\bin\\bash", "-lc", "(rs-backup-run -v --log-level=6) && echo 'OK' > /tmp/try.txt || echo 'Not OK' > /tmp/try.txt"]
    logfile = 'myfile.log'
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    while not kill_thread:

        with open(logfile, "w") as outfile:
            p = subprocess.Popen(command,
                     stdout=outfile,
                     stderr=subprocess.STDOUT,
                     startupinfo=startupinfo)

        epoch_time = time.time()
        localtime = time.asctime( time.localtime(epoch_time) )
        print '\nBackup running: '+localtime
        print ("- PID is {}").format(p.pid)
        while (p.poll() is None):
            time.sleep(1)
            if kill_thread:
                print 'Trying to kill backup ...'
                kill(p.pid)

        epoch_time = time.time()
        localtime = time.asctime( time.localtime(epoch_time) )
        print 'Backup finished: '+localtime
        returncode = getreturncode('c:\\cygwin64\\tmp\\try.txt')
        print ("- exit code was: {}").format(returncode)
        
        nexttime = time.asctime( time.localtime(epoch_time + backup_freq) )
        print '\nWaiting ..'
        print '- next Backup : '+nexttime
        for i in range(backup_freq):
            time.sleep(1)
            if kill_thread:
                return


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item

class MyForm(wx.Frame):
 
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, 
                          title=title,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
 
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)
        style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL
        log = wx.TextCtrl(panel, wx.ID_ANY, size=(300,100),
                          style=style)
        font1 = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Consolas')
        log.SetFont(font1)
##        btn = wx.Button(panel, wx.ID_ANY, 'Push me!')
##        self.Bind(wx.EVT_BUTTON, self.onButton, btn)
 
        # Add widgets to a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(log, 1, wx.ALL|wx.EXPAND, 5)
##        sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
        panel.SetSizer(sizer)
 
        # redirect text here
        sys.stdout=log
 
    def onClose(self, event):
        self.Hide()

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self):
        wx.adv.TaskBarIcon.__init__(self)
        self.set_icon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
        self.init_debug_window()
        self.init_backup_thread()

    def init_debug_window(self):
        self.debug_window = MyForm(root, "Debug Window")
        
    def init_backup_thread(self):
        self.backup_thread = Thread(target=MyWorker)
        self.backup_thread.start()

    def CreatePopupMenu(self):
        #This is bound by default to right mouse key click on the icon
        menu = wx.Menu()
        create_menu_item(menu, 'Configure...', self.on_configure)
        menu.AppendSeparator()
        create_menu_item(menu, 'Show debug window', self.on_debug)
        menu.AppendSeparator()
        create_menu_item(menu, 'About...', self.on_about)
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.Icon(wx.IconLocation(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        print 'Tray icon was left-clicked.'

    def on_hello(self, event):
        print 'Hello, world!'

    def on_debug(self, event):
        self.debug_window.Show(True)
        print 'Hello, world!'

    def on_configure(self, event):
        print 'Configure me'
        
    def on_about(self, event):
        about  = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_exit(self, event):

        global kill_thread
    
        kill_thread = True
        self.backup_thread.join()
        print 'Goodbye'

        wx.CallAfter(self.debug_window.Destroy)
        wx.CallAfter(self.Destroy)
        wx.CallAfter(root.Destroy)
        
def hello(name):
    print "Hello %s!" % name

kill_thread = False;

app = wx.App(False)
root = wx.Frame(None, -1, "top") # This is the top-level window.
root.Show(False)     # Don't show it

backup_icon = TaskBarIcon()

app.MainLoop()


import wx
import wx.adv

import sys

import subprocess 

from threading import Timer

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

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        print('starting ...')
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

def run_command(command):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with open('logfile.log', "w") as outfile:
        p = subprocess.Popen(command,
                         stdout=outfile,
                         stderr=subprocess.STDOUT,
                         startupinfo=startupinfo)
    return p

def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item

class MyFrame(wx.Frame):
    def __init__(self,parent,id,title, text):
        wx.Frame.__init__(self,parent,id,title)
        self.parent = parent
        self.initialize(text)
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def initialize(self, text):
        sizer = wx.GridBagSizer()
        self.entry = wx.StaticText(self,-1,label=text)
        sizer.Add(self.entry,(0,0),(1,1),wx.EXPAND)
        self.SetSizerAndFit(sizer)
        self.Show(True)
        
    def onClose(self, event):
        self.Hide()

class MyForm(wx.Frame):
 
    def __init__(self):
        wx.Frame.__init__(self, root, 
                          title="Debug Window")
 
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
#        sys.stdout=log
 
    def onClose(self, event):
        self.Hide()

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self):
        wx.adv.TaskBarIcon.__init__(self)
        self.set_icon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

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
        if self.p.poll:
            print 'Running'
        else
            print "Stopped"

    def on_hello(self, event):
    #       frame.Show(True)
        print 'Hello, world!'

    def on_debug(self, event):
        frame.Show(True)
        print 'Hello, world!'

    def on_configure(self, event):
        print 'Configure me'
##        command = ["c:\\cygwin64\\bin\\bash", "-lc", "time rs-backup-run -v --log-level=6"]
##        logfile = 'myfile.log'
##        myprocess = run_command(command, logfile)
        self.p = RepeatedTimer(600,  run_command, ["c:\\cygwin64\\bin\\bash", "-lc", "time rs-backup-run -v --log-level=6"])     
        
    def on_about(self, event):
        about  = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_exit(self, event):
        wx.CallAfter(root.Destroy)
        wx.CallAfter(self.Destroy)
        self.p.stop()
        print 'Goodbye'

def hello(name):
    print "Hello %s!" % name


app = wx.App(False)
root = wx.Frame(None, -1, "top") # This is the top-level window.
root.Show(False)     # Don't show it

frame = MyForm()

TaskBarIcon()
app.MainLoop()


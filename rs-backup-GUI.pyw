import wx
import wx.adv

import sys
import time

import os

import subprocess 

from threading import Thread

from ConfigFileEditor import ConfigFileEditPopup

import logging

class LoggerWriter(object):
    def __init__(self, writer):
        self._writer = writer
        self._msg = ''

    def write(self, message):
        self._msg = self._msg + message
        while '\n' in self._msg:
            pos = self._msg.find('\n')
            self._writer(self._msg[:pos])
            self._msg = self._msg[pos+1:]

    def flush(self):
        if self._msg != '':
            self._writer(self._msg)
            self._msg = ''

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

devnull = open(os.devnull, 'wb')

class BackupWorker(object):

    def __init__(self):
        self.kill_thread = False
        self.logfile = os.path.expanduser('~/.rs-backup/rs-backup-run.log')
        self.status = 'Initialising'

# Kill cygwin rsync process with gpid = proc_pid, using SIGHUP
# DANGER, WILL ROBINSON!! Need to ensure 'proc_pid' is not malicious!
    def _killrsync(self, proc_pid):
        command = ["c:/cygwin64/bin/bash", "-lc", "ps | grep " +str(proc_pid) + " | grep rsync | awk '{print $1;}' | xargs kill -HUP"]
        subprocess.call(command, shell=True)

    def backup_run(self):

        backup_freq = 600 #seconds

        runcommand = ["c:/cygwin64/bin/bash", "-lc", "(rs-backup-run -v) && echo 'OK' || echo 'Not OK' "]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while not self.kill_thread:

            with open(self.logfile, "w") as outfile:
                p = subprocess.Popen(runcommand,
                         stdin=devnull,
                         stdout=outfile,
                         stderr=subprocess.STDOUT,
                         startupinfo=startupinfo)
##                         shell=True)

                stime = time.time()
                print ("Backup running: PID is {}").format(p.pid)
                killcommand = ["c:/cygwin64/bin/bash", "-lc", "ps | grep " +str(p.pid) + " | grep rsync | awk '{print $1;}' | xargs kill -HUP"]
                while (p.poll() is None):
                    ntime = time.time()
                    self.status = 'Running '+ str(int(ntime-stime))
                    time.sleep(1)
                    if self.kill_thread:
                        logger.debug( 'Trying to kill rsync process ...')
                        subprocess.call(killcommand,
                                 stdin=devnull,
                                 stdout=outfile,
                                 stderr=subprocess.STDOUT,
                                 startupinfo=startupinfo)
##                                 shell=True)

            logger.debug( ("Backup finished: elapsed time was: {}").format(ntime-stime))
            try:
                all_lines = ''
                with open(self.logfile, "r") as infile:
                    all_lines = infile.read()
                    lines = all_lines.splitlines()
                    returncode = lines[-1]
            except IOError:
                returncode = "Fail"

            if returncode =='OK':
                logger.info('Backup completed successfully')
                logger.debug('Backup process log file follows - \n.........\n'+all_lines+'.........')
            else:
                logger.error('Backup completed with errors')
                logger.error(("Exit code was: {}").format(returncode))
                logger.error('Backup process log file follows - \n.........\n'+all_lines+'.........')
            
            ntime = time.time()
            if not self.kill_thread:
                wtime = int(max(0, backup_freq - (ntime-stime))+0.5)
                stime = ntime + wtime
                nexttime = time.asctime( time.localtime(stime) )
                print 'Waiting: Next backup at '+nexttime
                for i in range(wtime):
                    ntime = time.time()
                    self.status = 'Waiting '+ str(int(stime-ntime))
                    time.sleep(1)
                    if self.kill_thread:
                        return

    def run(self):
        self.kill_thread = False
        self.backup_thread = Thread(target=self.backup_run)
        self.backup_thread.start()

    def stop(self):
        self.kill_thread = True
        logger.warning('Backup abort requested!')
        logger.debug('Waiting for backup thread to finish ....')
        self.backup_thread.join(10)

        if not self.backup_thread.isAlive():
            print 'Done!'
        else:
            print "Woops - didn't finish in time"

        self.status = "Stopped"
 

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
        self.log = wx.TextCtrl(panel, wx.ID_ANY, size=(300,100),
                          style=style)
        font1 = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Consolas')
        self.log.SetFont(font1)
        self.readlog()
        btn = wx.Button(panel, wx.ID_ANY, 'Refresh')
        self.Bind(wx.EVT_BUTTON, self.on_refresh, btn)
 
        # Add widgets to a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log, 1, wx.ALL|wx.EXPAND, 5)
        sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
        panel.SetSizer(sizer)

    def readlog(self):
        self.log.Clear()
        try:
            with open(mainlogfile, "r") as infile:
                lines = infile.read()
                self.log.WriteText(lines)
        except IOError:
            pass

    def on_refresh(self, event):
        self.readlog()
 
    def onClose(self, event):
        self.Hide()

    def ShutDown(self):
        self.Destroy

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
        MyWorker.run()

    def CreatePopupMenu(self):
        #This is bound by default to right mouse key click on the icon
        menu = wx.Menu()
        create_menu_item(menu, 'Configure...', self.on_configure)
        menu.AppendSeparator()
        create_menu_item(menu, 'Show debug log', self.on_debug)
        menu.AppendSeparator()
        create_menu_item(menu, 'About...', self.on_about)
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.Icon(wx.IconLocation(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        print MyWorker.status

    def on_hello(self, event):
        print 'Hello, world!'

    def on_debug(self, event):
        self.debug_window.Show(True)

    def on_configure(self, event):
        logger.debug( 'Configure me')
        ConfigFileEditPopup('C:/cygwin64/etc/rs-backup/client-config')
        
    def on_about(self, event):
        about  = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_exit(self, event):
        MyWorker.stop()
        self.debug_window.ShutDown()
        self.Destroy()
        root.Destroy()

mainlogfile = os.path.expanduser('~/.rs-backup/rs-backup-GUI.log')
print mainlogfile

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=mainlogfile,
                    filemode='w')

logger = logging.getLogger()
sys.stderr = LoggerWriter(logger.error)
sys.stdout = LoggerWriter(logger.info)

MyWorker = BackupWorker()

app = wx.App()

root = wx.Frame(None, -1, "top") # This is the top-level window.
root.Show(False)     # Don't show it

backup_icon = TaskBarIcon()
app.MainLoop()





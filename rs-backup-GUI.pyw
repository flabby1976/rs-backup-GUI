import wx
import wx.adv

import sys
import time
import datetime

import tempfile

import os

import subprocess 

from threading import Thread

from ConfigParser import SafeConfigParser

from ConfigFileEditor import ConfigFileEditPopup
from ConfigFileEditor2 import ConfigParserEditPopup

import logging, logging.handlers

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
Myversion = "Version 0.2+develop"
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
        self.force_flag=False
        self.status = 'Initialising'
        self.interface = None

        ## Defaults for the configurable parameters
        self.mainlogfile = os.path.expanduser('~/.rs-backup/rs-backup-GUI.log')
        self.logging_level = logging.DEBUG
        self.backup_freq = 600
        self.logging_rotate_time = datetime.timedelta(hours=24)
        self.config_file = os.path.expanduser('~/.rs-backup/rs-backup-GUI.cfg')

    def backup_run(self):
        self.logger = logging.getLogger('Main_Logger')
        self.logger.setLevel(logging.DEBUG)

        self.configure()

        handler = logging.handlers.RotatingFileHandler(self.mainlogfile, backupCount=7)
        handler.setLevel(self.logging_level)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)      
        self.logger.addHandler(handler)

        self.next_rotate = datetime.datetime.now() + self.logging_rotate_time

        sys.stderr = LoggerWriter(self.logger.error)
        print >> sys.stderr, "Checking sys.stderr redirect"

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while not self.kill_thread:

            with tempfile.TemporaryFile() as outfile:

                if self.force_flag:
                    runcommand = ["c:/cygwin64/bin/bash", "-lc", "(rs-backup-run -vf) && echo 'OK' || echo 'Not OK' "]
                    self.force_flag = False
                else:
                    runcommand = ["c:/cygwin64/bin/bash", "-lc", "(rs-backup-run -v) && echo 'OK' || echo 'Not OK' "]
            
                p = subprocess.Popen(runcommand,
                         stdin=devnull,
                         stdout=outfile,
                         stderr=subprocess.STDOUT,
                         startupinfo=startupinfo)

                stime = time.time()
                
                self.interface.notify('Backup Running', flags=wx.ICON_INFORMATION)
                self.status = 'Backup Running'
                self.logger.info( ("Backup running: PID is {}").format(p.pid) )
                while (p.poll() is None):
                    time.sleep(1)
                    if self.kill_thread:
                        self.logger.debug( 'Trying to kill rsync process ...')
                        self.interface.notify('Aborting backup', flags=wx.ICON_ERROR)
                        killcommand = ["c:/cygwin64/bin/bash", "-lc", "ps | grep " +str(p.pid) + " | awk '{print $1;}' |  while read pid; do /bin/kill -- -${pid}; done;"]
                        self.logger.debug(killcommand)
                        subprocess.call(killcommand,
                                 stdin=devnull,
#                                 stdout=outfile,
                                 stderr=subprocess.STDOUT,
                                 startupinfo=startupinfo)

                ntime = time.time()
                self.logger.debug( ("Backup finished: elapsed time was: {}").format(ntime-stime))
                all_lines = ''
                try:
                    outfile.seek(0)
                    all_lines = outfile.read()
                    lines = all_lines.splitlines()
                    returncode = lines[-1]
                except IOError:
                    returncode = "Fail"

            if returncode =='OK':
                self.logger.info('Backup completed successfully')
                self.interface.notify('Backup completed successfully', flags=wx.ICON_INFORMATION)
                self.logger.debug('Backup process log file follows - \n.........\n'+all_lines+'.........')
            else:
                self.logger.error('Backup completed with errors')
                self.interface.notify('Backup completed with errors', flags=wx.ICON_ERROR)
                self.logger.error('Backup process log file follows - \n.........\n'+all_lines+'.........')
            
            if not self.kill_thread:
                ntime = time.time()
                wtime = int(max(0, self.backup_freq - (ntime-stime))+0.5)
                nexttime = time.asctime( time.localtime(ntime + wtime) )
                self.status = 'Next backup at '+nexttime
                self.logger.info( 'Waiting: Next backup at '+nexttime )
                self.interface.notify('Next backup at '+nexttime , flags=None)
                for i in range(wtime):
                    n = datetime.datetime.now()
                    if n>self.next_rotate:
                        self.logger.info('Rotating logfile')
                        sys.stderr = sys.__stderr__
                        self.logger.removeHandler(handler)
                        handler.doRollover()
                        self.logger.addHandler(handler)
                        sys.stderr = LoggerWriter(self.logger.error)
                        self.logger.info('Succesfully rotated logfile')
                        self.next_rotate = self.next_rotate + self.logging_rotate_time
                        self.logger.info('Next logfile rotate at '+ str(self.next_rotate))
                        print >> sys.stderr, "Checking sys.stderr redirect"
                    time.sleep(1)
                    if self.kill_thread or self.force_flag:
                        break
                        

    def configure(self):

        config = SafeConfigParser()
        found = config.read(self.config_file)

        if found:
            self.backup_freq = float(config.get('backup','frequency'))
            rt = float(config.get('logging','rotate_time'))
            l = config.get('logging','level')
            self.mainlogfile = config.get('logging','location')
        else:
            self.backup_freq = 300
            rt = 24
            l = "DEBUG"
            self.mainlogfile = "rs-backup-GUI.log"

        self.logging_rotate_time = datetime.timedelta(hours=rt)

        if l=='DEBUG':
            self.logging_level = logging.DEBUG
        elif l=='INFO':
            self.logging_level = logging.INFO
        elif l=='WARNING	':
            self.logging_level = logging.WARNING
        elif l=='ERROR':
            self.logging_level = logging.ERROR
        elif l=='CRITICAL':
            self.logging_level = logging.CRITICAL
        else:
            self.logging_level = logging.NOTSET

        self.mainlogfile = os.path.expanduser(self.mainlogfile)


    def run(self):
        self.kill_thread = False
        self.backup_thread = Thread(target=self.backup_run)
        self.backup_thread.start()

    def stop(self):
        self.kill_thread = True
        self.logger.warning('Backup abort requested!')
        self.logger.debug('Waiting for backup thread to finish ....')
        self.backup_thread.join(20)

        if not self.backup_thread.isAlive():
            self.logger.debug( 'Backup thread finished!' )
        else:
            self.logger.warning( "Woops! Backup thread didn't finish in time" )

        self.status = "Stopped"


class DebugLogWindow(wx.Frame):
 
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, 
                          title=title,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
 
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)

        style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL
        self.log = wx.TextCtrl(panel, wx.ID_ANY, style=style)
        font1 = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Consolas')
        self.log.SetFont(font1)
        self._set_textctrl_size_by_chars(self.log, 80, 20)
        self.readlog()
        btn = wx.Button(panel, wx.ID_ANY, 'Refresh')
        self.Bind(wx.EVT_BUTTON, self.on_refresh, btn)
 
        # Add widgets to a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log, 1, wx.ALL|wx.EXPAND, 5)

        sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
        panel.SetSizer(sizer)

        sizer.Fit(self)

    def _set_textctrl_size_by_chars(self, tc, w, h):
        sz = tc.GetTextExtent('X')
        sz = wx.Size(sz.x * w, sz.y * h)
        tc.SetInitialSize(tc.GetSizeFromTextSize(sz))
    
    def readlog(self):
        self.log.Clear()
        try:
            with open(MyWorker.mainlogfile, "r") as infile:
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


## https://stackoverflow.com/questions/35542551/how-to-create-a-taskbaricon-only-application-in-wxpython
class TaskBarIcon(wx.adv.TaskBarIcon):
    
    def __init__(self):
        wx.adv.TaskBarIcon.__init__(self)
        self.my_icon = wx.Icon(wx.IconLocation(TRAY_ICON))
        
        self.notify('Initialising ...', flags=None)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_debug)
        self.init_debug_window()

        self.worker = None

    def init_debug_window(self):
        self.debug_window = DebugLogWindow(root, "Debug Window")
        
    def create_menu_item(self, menu, label, func):
        item = wx.MenuItem(menu, -1, label)
        self.Bind(wx.EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def CreatePopupMenu(self):
        #This is bound by default to right mouse key click on the icon
        menu = wx.Menu()
        configmenu = wx.Menu()
        menu.AppendSubMenu(configmenu, 'Configure...')
        self.create_menu_item(configmenu, 'Configure rs-backup', self.on_configure1)
        self.create_menu_item(configmenu, 'Configure GUI', self.on_configure2)
        self.create_menu_item(configmenu, 'Choose files to backup', self.on_configure3)
        menu.AppendSeparator()
        self.create_menu_item(menu, 'Show debug log', self.on_debug)
        menu.AppendSeparator()
        self.create_menu_item(menu, 'About...', self.on_about)
        self.create_menu_item(menu, 'Set --force-run flag for next backup', self.on_force)
        self.create_menu_item(menu, 'Exit', self.on_exit)
        
        return menu

    def notify(self, text, flags = wx.ICON_INFORMATION):
        if flags:
            self.ShowBalloon('rs_backup', text, flags)
        self.SetIcon(self.my_icon, 'rs_backup:\n'+text)

    def on_debug(self, event):
        self.debug_window.Show(True)
        self.debug_window.readlog()

    def on_configure1(self, event):
        ConfigFileEditPopup('C:/cygwin64/etc/rs-backup/client-config')

    def on_configure2(self, event):
        ConfigParserEditPopup(self.worker.config_file)
        
    def on_configure3(self, event):
        with wx.DirDialog (None, "Choose input directory", "",
                    wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()

            self.worker.logger.debug(pathname)

        pass

    def on_about(self, event):
        about  = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_force(self, event):
        self.worker.force_flag=True

    def on_exit(self, event):
        self.worker.stop()
        self.debug_window.ShutDown()
        self.Destroy()
        root.Destroy()

app = wx.App()

root = wx.Frame(None, -1, "top") # This is the top-level window.
root.Show(False)     # Don't show it

MyWorker = BackupWorker()
backup_icon = TaskBarIcon()

MyWorker.interface = backup_icon
backup_icon.worker = MyWorker

MyWorker.run()

app.MainLoop()






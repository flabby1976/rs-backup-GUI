import wx
import wx.adv

import sys
import time
import datetime

import tempfile

import os

import subprocess 

from threading import Thread

from configparser import ConfigParser

import logging
import logging.handlers


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
Myversion = "Version 0.3 + Python 3 + dev"
Myauthor = "Copyright (C) 2018, 2019 Andrew Robinson"
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
        self.force_flag = False
        self.status = 'Initialising'
        self.interface = None

        self.backup_thread = None

        # Defaults for the configurable parameters
        self.default_config_file = os.path.expanduser('rs-backup-GUI.cfg')
        # Local configurable parameters
        self.config_file = os.path.expanduser('~/.rs-backup/rs-backup-GUI.cfg')

        self.include_file = os.path.expanduser('c:/cygwin64/tmp/rs-backup-GUI.inc')

        self.logger = logging.getLogger('Main_Logger')
        self.logger.setLevel(logging.DEBUG)

        self.handler = None

        self.mainlogfile = None
        self.logging_level = None
        self.logging_rotate_time = datetime.timedelta(0)
        self.backup_freq = 0

        self.remote_host = None
        self.remote_user = None
        self.push_module = None
        self.rsync_options = None

        self.configure()

        self.next_rotate = datetime.datetime.now() + self.logging_rotate_time

    def backup_run(self):

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while not self.kill_thread:

            self.configure()

            with tempfile.TemporaryFile(mode='w+t') as outfile:

                backup_command = "rs-backup-run -v"

                if self.force_flag:
                    backup_command = backup_command + " -f"
                    self.force_flag = False

                backup_command = backup_command + " -r " + self.remote_host
                backup_command = backup_command + " --remote-user=" + self.remote_user
                backup_command = backup_command + " --push-module=" + self.push_module
                backup_command = backup_command + " -o " + self.rsync_options
                backup_command = backup_command + " -i /tmp/rs-backup-GUI.inc"

                self.logger.debug(backup_command)

                runcommand = ["c:/cygwin64/bin/bash", "-lc", "("+backup_command+") && echo 'OK' || echo 'Not OK' "]
            
                self.logger.debug(runcommand)

                p = subprocess.Popen(runcommand,
                                     stdin=devnull,
                                     stdout=outfile,
                                     stderr=subprocess.STDOUT,
                                     startupinfo=startupinfo)

                stime = time.time()

                self.interface.notify('Backup Running', flags=wx.ICON_INFORMATION)
                self.status = 'Backup Running'
                self.logger.info("Backup running")
                self.logger.debug(("Backup job PID is {}".format(p.pid)))
                while p.poll() is None:
                    time.sleep(1)
                    if self.kill_thread:
                        self.logger.debug('Trying to kill rsync process ...')
                        self.interface.notify('Aborting backup', flags=wx.ICON_ERROR)
                        killcommand = ["c:/cygwin64/bin/bash", "-lc", "ps | grep " + str(p.pid) +
                                       " | awk '{print $1;}' |  while read pid; do /bin/kill -- -${pid}; done;"]
                        self.logger.debug(killcommand)
                        subprocess.call(killcommand,
                                        stdin=devnull,
                                        stdout=outfile,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=startupinfo)

                ntime = time.time()
                self.logger.debug(("Backup finished: elapsed time was: {}".format(ntime-stime)))
                all_lines = ''
                try:
                    outfile.seek(0)
                    all_lines = outfile.read()
                    lines = all_lines.splitlines()
                    returncode = lines[-1]
                except IOError:
                    returncode = "Fail"

            if returncode == 'OK':
                self.logger.info('Backup completed successfully')
                self.interface.notify('Backup completed successfully', flags=wx.ICON_INFORMATION)
                self.logger.debug('Backup process log file follows - \n.........\n'+all_lines+'.........')
            else:
                self.logger.error('Backup completed with errors')
                self.interface.notify('Backup completed with errors', flags=wx.ICON_ERROR)
                self.logger.error('Backup process log file follows - \n.........\n'+all_lines+'.........')
            
            if not self.kill_thread:
                ntime = time.time()
                wtime = int(max(0.0, self.backup_freq - (ntime-stime))+0.5)
                nexttime = time.asctime(time.localtime(ntime + wtime))
                self.status = 'Next backup at '+nexttime
                self.logger.info('Waiting: Next backup at '+nexttime)
                self.interface.notify('Next backup at '+nexttime, flags=None)
                for i in range(wtime):
                    n = datetime.datetime.now()
                    if n > self.next_rotate:
                        self.logger.info('Rotating logfile')
                        sys.stderr = sys.__stderr__
                        self.logger.removeHandler(self.handler)
                        self.handler.doRollover()
                        self.logger.addHandler(self.handler)
                        sys.stderr = LoggerWriter(self.logger.error)
                        self.logger.info('Successfully rotated logfile')
                        self.next_rotate = self.next_rotate + self.logging_rotate_time
                        self.logger.info('Next logfile rotate at ' + str(self.next_rotate))
#                        print >> sys.stderr, "Checking sys.stderr redirect"
                    time.sleep(1)
                    if self.kill_thread or self.force_flag:
                        break
                        
    def configure(self):

        config = ConfigParser(allow_no_value=True)

        found = config.read([self.default_config_file, self.config_file])

        if found:
            self.backup_freq = float(config.get('backup', 'frequency'))
            rt = float(config.get('logging', 'rotate_time'))
            level = config.get('logging', 'level')
            self.mainlogfile = config.get('logging', 'location')
            self.remote_host = config.get('rs-backup-run', 'remote_host')
            self.remote_user = config.get('rs-backup-run', 'remote_user')
            self.push_module = config.get('rs-backup-run', 'push_module')
            self.rsync_options = config.get('rs-backup-run', 'rsync_options')
        else:
            self.backup_freq = 300
            rt = 24
            level = "DEBUG"
            self.mainlogfile = "~/.rs-backup/rs-backup-GUI.log"

        self.logging_rotate_time = datetime.timedelta(hours=rt)

        if level == 'DEBUG':
            self.logging_level = logging.DEBUG
        elif level == 'INFO':
            self.logging_level = logging.INFO
        elif level == 'WARNING	':
            self.logging_level = logging.WARNING
        elif level == 'ERROR':
            self.logging_level = logging.ERROR
        elif level == 'CRITICAL':
            self.logging_level = logging.CRITICAL
        else:
            self.logging_level = logging.NOTSET

        self.mainlogfile = os.path.expanduser(self.mainlogfile)

        if self.handler:
            sys.stderr = sys.__stderr__
            self.logger.removeHandler(self.handler)

        self.handler = logging.handlers.RotatingFileHandler(self.mainlogfile, backupCount=7)
        self.handler.setLevel(self.logging_level)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

        sys.stderr = LoggerWriter(self.logger.error)
        # print >> sys.stderr, "Checking sys.stderr redirect"

        try_paths = config.items("Locations to backup")

        with open(self.include_file, 'w') as temp:
            self.logger.debug(temp.name)
            include_list = []
            for it, try_path in try_paths:

                drive, path_and_file = os.path.splitdrive(try_path)

                fbits = ['cygdrive', drive.lower()[0]]
                fbits.extend(path_and_file[1:].split(os.sep))
                fbits.append('***')

                self.logger.debug(fbits)
                k = ''
                for bit in fbits:
                    k = k + '/' + bit
                    if k not in include_list:
                        include_list.append(k)
                        temp.write(k+'\n')

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
            self.logger.debug('Backup thread finished!')
        else:
            self.logger.warning("Woops! Backup thread didn't finish in time")

        self.status = "Stopped"


class DebugLogWindow(wx.Frame):
 
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, 
                          title=title,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
 
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        self.log = wx.TextCtrl(panel, wx.ID_ANY, style=style)
        font1 = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, 'Consolas')
        self.log.SetFont(font1)
        self._set_textctrl_size_by_chars(self.log, 80, 20)
        self.readlog()
        btn = wx.Button(panel, wx.ID_ANY, 'Refresh')
        self.Bind(wx.EVT_BUTTON, self.on_refresh, btn)
 
        # Add widgets to a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log, 1, wx.ALL | wx.EXPAND, 5)

        sizer.Add(btn, 0, wx.ALL | wx.CENTER, 5)
        panel.SetSizer(sizer)

        sizer.Fit(self)

    @staticmethod
    def _set_textctrl_size_by_chars(tc, w, h):
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

    def on_refresh(self, _):
        self.readlog()
 
    def on_close(self, _):
        self.Hide()

    def shutdown(self):
        self.Destroy()


# https://stackoverflow.com/questions/35542551/how-to-create-a-taskbaricon-only-application-in-wxpython
class TaskBarIcon(wx.adv.TaskBarIcon):
    
    def __init__(self):
        wx.adv.TaskBarIcon.__init__(self)
        self.my_icon = wx.Icon(wx.IconLocation(TRAY_ICON))
        
        self.notify('Initialising ...', flags=None)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_debug)
        self.debug_window = DebugLogWindow(root, "Debug Window")
        self.worker = None

    def create_menu_item(self, menu, label, func):
        item = wx.MenuItem(menu, -1, label)
        self.Bind(wx.EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def CreatePopupMenu(self):
        # This is bound by default to right mouse key click on the icon
        menu = wx.Menu()
        self.create_menu_item(menu, 'Set --force-run flag and re-try backup', self.on_force)
        self.create_menu_item(menu, 'Show debug log', self.on_debug)
        menu.AppendSeparator()
        self.create_menu_item(menu, 'About...', self.on_about)
        self.create_menu_item(menu, 'Exit', self.on_exit)
        
        return menu

    def notify(self, text, flags=wx.ICON_INFORMATION):
        if flags:
            self.ShowBalloon('rs_backup', text, flags)
        self.SetIcon(self.my_icon, 'rs_backup:\n'+text)

    def on_debug(self, _):
        self.debug_window.Show(True)
        self.debug_window.readlog()

    @staticmethod
    def on_about(_):
        about = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_force(self, _):
        self.worker.force_flag = True

    def on_exit(self, _):
        self.worker.stop()
        self.debug_window.shutdown()
        self.Destroy()
        root.Destroy()


app = wx.App()

root = wx.Frame(None, -1, "top")  # This is the top-level window.
root.Show(False)     # Don't show it

MyWorker = BackupWorker()
backup_icon = TaskBarIcon()

MyWorker.interface = backup_icon
backup_icon.worker = MyWorker

MyWorker.run()

app.MainLoop()

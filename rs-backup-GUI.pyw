import wx
import wx.adv

import sys
import time

import tempfile

import os

import subprocess

from threading import Thread

from configparser import ConfigParser

import logging
import logging.handlers


class LoggerWriter(object):
    # From https://stackoverflow.com/a/51612402
    def __init__(self, writer):
        self._writer = writer
        self._msg = ''

    def write(self, message):
        self._msg = self._msg + message
        while '\n' in self._msg:
            pos = self._msg.find('\n')
            self._writer(self._msg[:pos])
            self._msg = self._msg[pos + 1:]

    def flush(self):
        if self._msg != '':
            self._writer(self._msg)
            self._msg = ''


# Defaults for the configurable parameters are in this file, in same directory as the executable
default_config_file = 'rs-backup-GUI.cfg'
# Location for local configurable parameters, in user's home directory
config_file = os.path.expanduser('~/.rs-backup/rs-backup-GUI.cfg')

TRAY_TOOLTIP = 'rs-backup-GUI'
TRAY_ICON = 'Flag-red.ico'

Myname = "rs-backup-GUI: A GUI front-end for rs_backup_suite"
Myversion = "Version 0.4 + simplify-definitions"
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


class MyNotifyException(Exception):
    pass


# https://stackoverflow.com/questions/35542551/how-to-create-a-taskbaricon-only-application-in-wxpython
class TaskBarIcon(wx.adv.TaskBarIcon):

    def __init__(self, menu_func):
        wx.adv.TaskBarIcon.__init__(self)
        self.my_icon = wx.Icon(wx.IconLocation(TRAY_ICON))

        self.notify('Initialising ...', balloon=None)
        self.menu_func = menu_func

    def create_menu_item(self, menu, label, func):
        item = wx.MenuItem(menu, -1, label)
        self.Bind(wx.EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def CreatePopupMenu(self):
        # This is bound by default to right mouse key click on the icon
        popup = self.menu_func()
        return popup

    def notify(self, text, balloon=wx.ICON_INFORMATION):
        self.SetIcon(self.my_icon, 'rs_backup:\n' + text)
        if balloon:
            # noinspection PyUnresolvedReferences
            # noinspection PyProtectedMember
            try:
                self.ShowBalloon('rs_backup', text, balloon)
            except wx._core.wxAssertionError as e:
                raise MyNotifyException(e)


class BackupWorker(object):

    def __init__(self):
        self.kill_thread = False
        self.force_flag = False
        self.status = 'Initialising'

        self.interface = TaskBarIcon(self.create_menu)

        self.interface.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_debug)

        self.cygwin_root = 'c:/cygwin64'

        self.backup_thread = None

        self.include_file = '/tmp/include'

        self.debug_window = DebugLogWindow(root, "Debug Window", mainlogfile)

        self.backup_freq = 300

        self.remote_host = None
        self.remote_user = None
        self.push_module = None
        self.rsync_options = None

    def configure(self):

        config = ConfigParser(allow_no_value=True)

        found = config.read([default_config_file, config_file])

        if not found:
            logger.error('Missing configuration files')
            return

        level = config.get('logging', 'level')

        if level == 'DEBUG':
            logging_level = logging.DEBUG
        elif level == 'INFO':
            logging_level = logging.INFO
        elif level == 'WARNING':
            logging_level = logging.WARNING
        elif level == 'ERROR':
            logging_level = logging.ERROR
        elif level == 'CRITICAL':
            logging_level = logging.CRITICAL
        else:
            logging_level = logging.NOTSET

        # self.mainlogfile = config.get('logging', 'location')
        # self.mainlogfile = os.path.expanduser(self.mainlogfile)

        # if self.handler:
        #     sys.stderr = sys.__stderr__
        #     self.logger.removeHandler(self.handler)

        # self.handler = logging.handlers.RotatingFileHandler(self.mainlogfile, backupCount=7)
        logger.setLevel(logging_level)
        # formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        # self.handler.setFormatter(formatter)
        # self.logger.addHandler(self.handler)
        #
        # sys.stderr = LoggerWriter(self.logger.error)

        # rt = float(config.get('logging', 'rotate_time'))
        # self.logging_rotate_time = datetime.timedelta(hours=rt)

        self.remote_host = config.get('rs-backup-run', 'remote_host')
        self.remote_user = config.get('rs-backup-run', 'remote_user')
        self.push_module = config.get('rs-backup-run', 'push_module')
        self.rsync_options = config.get('rs-backup-run', 'rsync_options')
        self.backup_freq = float(config.get('backup', 'frequency'))

        try_paths = config.items('Locations to backup')
        with open(self.cygwin_root + self.include_file, 'w') as temp:
            logger.debug(temp.name)
            include_list = []
            for it, try_path in try_paths:

                logger.debug(try_path)

                drive, path_and_file = os.path.splitdrive(try_path)

                fbits = ['cygdrive', drive.lower()[0]]
                fbits.extend(path_and_file[1:].split(os.sep))
                fbits.append('***')

                logger.debug(fbits)
                k = ''
                for bit in fbits:
                    k = k + '/' + bit
                    if k not in include_list:
                        include_list.append(k)
                        temp.write(k + '\n')

    def create_menu(self):

        menu = wx.Menu()
        self.interface.create_menu_item(menu, 'Set --force-run flag and re-try backup', self.on_force)
        self.interface.create_menu_item(menu, 'Show debug log', self.on_debug)
        menu.AppendSeparator()
        self.interface.create_menu_item(menu, 'About...', self.on_about)
        self.interface.create_menu_item(menu, 'Exit', self.on_exit)

        return menu

    def on_force(self, _):
        self.force_flag = True

    def on_debug(self, _):
        self.debug_window.Show(True)
        self.debug_window.readlog()

    @staticmethod
    def on_about(_):
        about = Myname + "\n" + Myversion + "\n" + Myauthor + "\n" + MyNotice
        wx.MessageBox(message=about, caption="About", style=wx.OK | wx.ICON_INFORMATION)

    def on_exit(self, _):
        self.stop()
        self.debug_window.shutdown()
        self.interface.Destroy()
        root.Destroy()

    def my_notify(self, text, balloon=wx.ICON_INFORMATION):
        try:
            self.interface.notify(text, balloon)
        except MyNotifyException as e:
            logger.error("Notify fail:")
            logger.error(str(e))
            if self.interface.IsOk():
                logger.debug("IsOk = True")
            else:
                logger.debug("IsOk = False")
            if self.interface.IsIconInstalled():
                logger.debug("IsIconInstalled = True")
            else:
                logger.debug("IsIconInstalled = False")
            self.interface.Destroy()
            self.interface = TaskBarIcon(self.create_menu)

    def backup_run(self):

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while not self.kill_thread:

            self.configure()

            with tempfile.TemporaryFile(mode='w+t') as outfile:

                backup_command = "rs-backup-run -v"

                if self.force_flag:
                    backup_command = backup_command + "f"
                    self.force_flag = False

                backup_command = backup_command + " -r " + self.remote_host
                backup_command = backup_command + " --remote-user=" + self.remote_user
                backup_command = backup_command + " --push-module=" + self.push_module
                backup_command = backup_command + " -o " + self.rsync_options
                backup_command = backup_command + " -i " + self.include_file

                logger.debug(backup_command)

                runcommand = [self.cygwin_root + "/bin/bash", "-lc",
                              "(" + backup_command + ") && echo 'OK' || echo 'Not OK' "]

                logger.debug(runcommand)

                p = subprocess.Popen(runcommand,
                                     stdin=devnull,
                                     stdout=outfile,
                                     stderr=subprocess.STDOUT,
                                     startupinfo=startupinfo)

                stime = time.time()

                self.my_notify('Backup Running', balloon=wx.ICON_INFORMATION)
                self.status = 'Backup Running'
                logger.info("Backup running")
                logger.debug(("Backup job PID is {}".format(p.pid)))
                while p.poll() is None:
                    time.sleep(1)
                    if self.kill_thread:
                        logger.debug('Trying to kill rsync process ...')
                        self.my_notify('Aborting backup', balloon=wx.ICON_ERROR)
                        killcommand = [self.cygwin_root + "/bin/bash", "-lc", "ps | grep " + str(p.pid) +
                                       " | awk '{print $1;}' |  while read pid; do /bin/kill -- -${pid}; done;"]
                        logger.debug(killcommand)
                        subprocess.call(killcommand,
                                        stdin=devnull,
                                        stdout=outfile,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=startupinfo)

                ntime = time.time()
                logger.debug(("Backup finished: elapsed time was: {}".format(ntime - stime)))
                all_lines = ''
                try:
                    outfile.seek(0)
                    all_lines = outfile.read()
                    lines = all_lines.splitlines()
                    returncode = lines[-1]
                except IOError:
                    returncode = "Fail"

            if returncode == 'OK':
                logger.info('Backup completed successfully')
                self.my_notify('Backup completed successfully', balloon=wx.ICON_INFORMATION)
                logger.debug('Backup process log file follows - \n.........\n' + all_lines + '.........')
            else:
                logger.error('Backup completed with errors')
                self.my_notify('Backup completed with errors', balloon=wx.ICON_ERROR)
                logger.error('Backup process log file follows - \n.........\n' + all_lines + '.........')

            if not self.kill_thread:
                ntime = time.time()
                wtime = int(max(0.0, self.backup_freq - (ntime - stime)) + 0.5)
                nexttime = time.asctime(time.localtime(ntime + wtime))
                self.status = 'Next backup at ' + nexttime
                logger.info('Waiting: Next backup at ' + nexttime)
                self.my_notify('Next backup at ' + nexttime, balloon=None)
                for i in range(wtime):
                    time.sleep(1)
                    if self.kill_thread or self.force_flag:
                        break

    def run(self):
        self.kill_thread = False
        self.backup_thread = Thread(target=self.backup_run)
        self.backup_thread.start()

    def stop(self):
        self.kill_thread = True
        logger.warning('Backup abort requested!')
        logger.debug('Waiting for backup thread to finish ....')
        self.backup_thread.join(20)

        if not self.backup_thread.isAlive():
            logger.debug('Backup thread finished!')
        else:
            logger.warning("Woops! Backup thread didn't finish in time")

        self.status = "Stopped"


class DebugLogWindow(wx.Frame):

    def __init__(self, parent, title, logfile):
        wx.Frame.__init__(self, parent,
                          title=title,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.logfile = logfile

        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        self.log = wx.TextCtrl(panel, wx.ID_ANY, style=style)
        # noinspection PyUnresolvedReferences
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
        # https://stackoverflow.com/questions/14269880/the-right-way-to-find-the-size-of-text-in-wxpython
        font2 = tc.GetFont()
        dc = wx.ScreenDC()
        dc.SetFont(font2)
        sz = dc.GetTextExtent('X')
        sz = wx.Size(sz.x * w, sz.y * h)
        tc.SetInitialSize(tc.GetSizeFromTextSize(sz))

    def readlog(self):
        self.log.Clear()
        try:
            with open(self.logfile, "r") as infile:
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


app = wx.App()

root = wx.Frame(None, -1, "top")  # This is the top-level window.
root.Show(False)  # Don't show it

logger = logging.getLogger('Main_Logger')
logger.setLevel(logging.DEBUG)

mainlogfile = os.path.expanduser('~/.rs-backup/rs-backup-GUI.log')

handler = logging.handlers.TimedRotatingFileHandler(mainlogfile,
                                                    when="m",
                                                    interval=10,
                                                    backupCount=5)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
sys.stderr = LoggerWriter(logger.error)

MyWorker = BackupWorker()

MyWorker.run()

app.MainLoop()

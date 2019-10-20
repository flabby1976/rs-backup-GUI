
from ConfigParser import SafeConfigParser
import wx

class ConfigParserEditPopup(wx.Frame):

    def __init__(self, filename, title="Configuration Editor"):
        wx.Frame.__init__(self, None, title=title)

        self.filename = filename
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(4, 4)

        self.config = SafeConfigParser()
        self.config.read(self.filename)

        self.ents={}
        row = 0
        for section_name in self.config.sections():
            self.ents[section_name]={}
            l = wx.StaticText(panel, label="["+section_name+"]")
            sizer.Add(l, pos=(row, 0), flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
            row = row+1
            
            for key, value in self.config.items(section_name, 1):

                l = wx.StaticText(panel, label=str(key), style=wx.ALIGN_RIGHT)
                sizer.Add(l, pos=(row, 0), flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)

                e = wx.TextCtrl(panel, value=value)
                sizer.Add(e, pos=(row, 1), span=(1, 5),
                    flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)

                self.ents[section_name][key]=e

                row = row+1

        buttonOk = wx.Button(panel, label="Ok", size=(90, 28))
        buttonCancel = wx.Button(panel, label="Cancel", size=(90, 28))
        sizer.Add(buttonOk, pos=(row+1, 3))
        sizer.Add(buttonCancel, pos=(row+1, 4), flag=wx.RIGHT|wx.BOTTOM, border=10)

        buttonOk.Bind(wx.EVT_BUTTON,self.OK)      
        buttonCancel.Bind(wx.EVT_BUTTON,self.Cancel)
        
        panel.SetSizer(sizer)
        sizer.Fit(self)


    def OK(self, event):
        for section_name in self.config.sections():
            for key in self.config.options(section_name):
                self.config.set(section_name, key, self.ents[section_name][key].GetValue())
            if self.Verify():
                self.Save()
            else:
                print('Config Error!')

    def Cancel(self, event):
        self.Quit()

    def Verify(self):
        return True

    def Save(self):
        with open(self.filename, 'wb') as configfile:
            self.config.write(configfile)
        self.Quit()

    def Quit(self):
        self.Close()




        


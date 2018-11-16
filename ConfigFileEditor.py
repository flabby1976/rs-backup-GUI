
from configobj import ConfigObj
import wx

class MyConfigObj(ConfigObj):

    def __init__(self, *args, **kwargs):
        ConfigObj.__init__(self, *args, **kwargs)

    def _write_line(self, indent_string, entry, this_entry, comment):
        """Write an individual line, for the write method"""
        # NOTE: the calls to self._quote here handles non-StringType values.
        if not self.unrepr:
            val = self._decode_element(self._quote(this_entry))
        else:
            val = repr(this_entry)
            
        return '%s%s%s%s%s' % (indent_string,
                               self._decode_element(self._quote(entry, multiline=False)),
                               self._a_to_u('='),
                               val,
                               self._decode_element(comment))

    def _unquote(self, value):
         return value

    def _quote(self, value, multiline=True):
        return value


class ConfigFileEditPopup(wx.Frame):

    def __init__(self, filename, title="Configuration Editor"):
        wx.Frame.__init__(self, None, title=title)

        self.InitUI(filename)
        self.Centre()
        self.Show()

    def InitUI(self, filename):

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(4, 4)

        self.config = MyConfigObj(filename, interpolation = False)

        self.ents={}
        row = 0
        for key in self.config.scalars:

            l = wx.StaticText(panel, label=str(key))
            sizer.Add(l, pos=(row, 0), flag=wx.TOP|wx.LEFT|wx.BOTTOM, border=5)

            e = wx.TextCtrl(panel, value=self.config[key])
            sizer.Add(e, pos=(row, 1), span=(1, 5),
                flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)

            self.ents[key]=e

            row = row+1

        buttonOk = wx.Button(panel, label="Ok", size=(90, 28))
        buttonCancel = wx.Button(panel, label="Cancel", size=(90, 28))
        sizer.Add(buttonOk, pos=(row+1, 3))
        sizer.Add(buttonCancel, pos=(row+1, 4), flag=wx.RIGHT|wx.BOTTOM, border=10)

        buttonOk.Bind(wx.EVT_BUTTON,self.OK)      
        buttonCancel.Bind(wx.EVT_BUTTON,self.Cancel)
        
        sizer.Fit(panel)
        panel.SetSizer(sizer)
        panel.Fit()

    def OK(self, event):
        for key in self.config.scalars:
            self.config[key]=self.ents[key].GetValue()
        if self.Verify():
            self.Save()
        else:
            print('Config Error!')

    def Cancel(self, event):
        self.Quit()

    def Verify(self):
        return True

    def Save(self):
        self.config.write()
        self.Quit()

    def Quit(self):
        self.Close()




        


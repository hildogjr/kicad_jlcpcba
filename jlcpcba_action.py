import pcbnew
import wx
import sys
import os
import re

from .jlcpcba_main import *

class JlcpcbaPluginAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Export JLCPCB PCBA Files"
        self.category = "PCBA"
        self.description = "Create BOM and CPL files for JLCPCBs PCBA Service"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'jlcpcba.png')

    def Run(self):
        print("Testing")
        try:
            create()
            wx.MessageDialog(None, "All Done").ShowModal()
        except Exception as e:
            import os
            plugin_dir = os.path.dirname(os.path.realpath(__file__))
            log_file = os.path.join(plugin_dir, 'jlcpcba_run.log')
            with open(log_file, 'w') as f:
                f.write(repr(e))
            wx.MessageDialog(None, "Failed, check logs").ShowModal()





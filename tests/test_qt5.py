#!/usr/bin/python3
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QHBoxLayout
#from PyQt5.QtCore import SIGNAL

import sys
sys.path.insert(0, '..')
sys.path.insert(0, '.')

from Koo.Rpc import Rpc
from Koo.Common import Api
from Koo.Common import Localization
Localization.initializeTranslations()
from Koo.Dialogs import WindowService
from Koo.Actions import Actions
import Koo

x = Rpc.session.login('http://admin:admin@localhost:8069', 'koo')

app = QApplication([])

class TestWindow(QMainWindow):
    def addWindow(self, window, target):
        parent = QApplication.activeModalWidget()
        if not parent:
            parent = self
        dialog = QDialog(parent)
        dialog.setWindowTitle( _('Wizard') )
        dialog.setModal( True )
        layout = QHBoxLayout(dialog)
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.addWidget(window)
        window.setParent( dialog )
        #self.connect( window, SIGNAL('closed()'), dialog.accept )
        # self.connect( window, oialog.accept )
        window.show()
        dialog.exec_()

win = TestWindow()

class KooApi(Api.KooApi):
    def execute(self, actionId, data={}, type=None, context={}):
    	Koo.Actions.execute( actionId, data, type, context )

    def executeReport(self, name, data={}, context={}):
    	return Koo.Actions.executeReport( name, data, context )

    def executeAction(self, action, data={}, context={}):
    	return Koo.Actions.executeAction( action, data, context )

    def executeKeyword(self, keyword, data={}, context={}):
    	return Koo.Actions.executeKeyword( keyword, data, context )

    def createWindow(self, view_ids, model, res_id=False, domain=None,
    		view_type='form', window=None, context=None, mode=None, name=False, autoReload=False,
    		target='current'):
    	WindowService.createWindow( view_ids, model, res_id, domain,
    		view_type, window, context, mode, name, autoReload, target )

    def createWebWindow(self, url, title):
    	WindowService.createWebWindow(url, title)

    def windowCreated(self, window, target):
    	win.addWindow( window, target )

Api.instance = KooApi()

# Api.instance.createWindow([], 'res.partner', 2, target='current')
Api.instance.createWindow([], 'giscedata.at.tram', 1, target='current')
win.show()

Rpc.session.logout()

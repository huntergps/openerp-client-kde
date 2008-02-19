##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: char.py 2955 2006-04-27 19:19:50Z pinky $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from common import common

from translationdialog import *
from abstractformwidget import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class CharFormWidget(AbstractFormWidget):
	def __init__(self, parent, view, attrs={}):
		AbstractFormWidget.__init__(self, parent, view, attrs)

		self.widget = QLineEdit( self )
		self.widget.setMaxLength( int( attrs.get( 'size',16 ) ) )
		self.installPopupMenu( self.widget )
		if attrs.get( 'invisible', False ):
			self.widget.hide()

		layout = QHBoxLayout( self )
		layout.setContentsMargins( 0, 0, 0, 0 )
		layout.addWidget( self.widget )

		if attrs.get('translate', False):
			pushTranslate = QPushButton( self )
			pushTranslate.setIcon( QIcon( ':/images/images/locale.png' ) )
			layout.addWidget( pushTranslate )
			self.connect( pushTranslate, SIGNAL('clicked()'), self.translate )

		self.connect( self.widget, SIGNAL('editingFinished()'), self.modified )

	def translate(self):
		if not self.model.id:
			QMessageBox.information( self, '', _('You must save the resource before adding translations'))
			return
		dialog = TranslationDialog( self.model.id, self.model.resource, self.attrs['name'], unicode(self.widget.text()), self )
		dialog.exec_()
		self.widget.setText( dialog.result )

	def store(self):
		self.model.setValue( self.name, unicode(self.widget.text()) or False )

	def clear(self):
		self.widget.setText('')
	
	def showValue(self):
		self.widget.setText( self.model.value(self.name) or '' )

	def setReadOnly(self, value):
		self.widget.setReadOnly( value )

	def colorWidget(self):
		return self.widget


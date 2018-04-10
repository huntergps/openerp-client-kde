##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
# Copyright (c) 2007-2008 Albert Cervera i Areny <albert@nan-tic.com>
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

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

# @brief AbstractFieldWidget is the base class for all search widgets in Koo.
# In order to create a new search widget, that is: a widget that appears in a
# auto-generated search form you need to inherit from this class and implement some
# of it's functions.


class AbstractSearchWidget(QWidget):
    # @brief Creates a new AbstractSearchWidget and receives the following parameters
    #
    # Note that a class that inherits AbstractSearchWidget should set self.focusWidget
    # which by default equals 'self'.
    #
    #  name:       The name of the field
    #  parent:     The QWidget parent of this QWidget
    #  attributes: Holds some extra attributes
    #
    keyDownPressed = pyqtSignal()

    def __init__(self, name, parent, attrs={}):
        QWidget.__init__(self, parent)
        self._value = None
        self.name = name
        self.model = attrs.get('model', None)
        self.attrs = attrs
        self.focusWidget = self

    def eventFilter(self, target, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Down:
            self.keyDownPressed.emit()
            return True
        return False

    # @brief Sets the focus to the widget
    def setFocus(self):
        self.focusWidget.setFocus()

    # @brief Clears the value of the widget
    # New widgets should override this function.
    def clear(self):
        pass

    # @brief Returns a domain-like list for the current value in the widget.
    # New widgets should override this function.
    def value(self):
        return []

    # @brief Sets the given value in the search field.
    # New widgets should override this function.
    def setValue(self, value):
        pass

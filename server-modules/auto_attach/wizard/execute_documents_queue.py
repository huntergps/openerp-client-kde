##############################################################################
#
# Copyright (c) 2007-2010 NaN Projectes de Programari Lliure, S.L. All rights reserved.
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
# as published by the Free Software Foundation; either version 3
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

import netsvc
import wizard
import pooler

view_form_end = """<?xml version="1.0"?>
	<form string="Document queue processed">
		<label align="0.0" string="The document queue has been executed." colspan="4"/>
	</form>"""

view_form_start = """<?xml version="1.0"?>
	<form string="Document queue update">
		<image name="gtk-info" size="64" colspan="2"/>
		<group colspan="2" col="4">
			<label align="0.0" string="All documents in the queue will be analyzed, verified and processed." colspan="4"/>
			<label align="0.0" string="Note that this operation may take a lot of time, depending on the number of documents." colspan="4"/>
			<label align="0.0" string="The following documents will be processed:" colspan="4"/>
			<field name="documents" nolabel="1" colspan="4"/>
		</group>
	</form>"""

view_fields_start = {
	"documents": {'type':'text', 'string':'Documents', 'readonly':True}
}

class execute_document_queue_wizard(wizard.interface):
	def _before_execute(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		if 'ids' in data:
			ids = data['ids']
		else:
			ids = pool.get('nan.document').search(cr, uid, [('state','in',('pending','verified'))], context=context)
		values = pool.get('nan.document').read(cr, uid, ids, ['name'], context)
		ret = { 
			'documents': '\n'.join([x['name'] for x in values]) 
		}
		return ret

	def _execute(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		if 'ids' in data:
			ids = data['ids']
		else:
			ids = pool.get('nan.document').search(cr, uid, [('state','=',('pending','verified'))], context=context)
		workflow = netsvc.LocalService('workflow')
		for id in ids:
			workflow.trg_validate(uid, 'nan.document', id, 'analyze_document', cr)
			document = pool.get('nan.document').browse(cr, uid, id, context)
			if not document.template_id:
				continue
			workflow.trg_validate(uid, 'nan.document', id, 'verify_document', cr)
			workflow.trg_validate(uid, 'nan.document', id, 'process_document', cr)
		return {}

	states = {
		'init': {
			'actions': [_before_execute],
			'result': {'type':'form', 'arch':view_form_start, 'fields': view_fields_start, 'state':[('end','Cancel','gtk-cancel'),('start','Start Process','gtk-ok')]}
		},
		'start': {
			'actions': [_execute],
			'result': {'type':'form', 'arch':view_form_end, 'fields': {}, 'state':[('end','Close','gtk-close')]}
		}
	}
execute_document_queue_wizard('nan_document_execute')

##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from Koo.Rpc import RpcProxy
from Koo import Rpc
from Koo.Common import Options
from Record import ModelRecord
import Field 


from PyQt4.QtCore import *
from PyQt4.QtGui import *

try:
	a = set()
except NameError:
	from sets import Set as set

## @brief The ModelRecordGroup class manages a list of records (models).
# 
# Provides functions for loading, storing and creating new objects of the same type.
# The 'fields' property stores a dictionary of dictionaries, each of which contains 
# information about a field. This information includes the data type ('type'), its name
# ('name') and other attributes. The 'mfields' property stores the classes responsible
# for managing the values which are finally stored on the 'values' dictionary in the
# Model
#
# The model can also be sorted by any of it's fields. Two sorting methods are provided:
# SortVisibleItems and SortAllItems. SortVisibleItems is usually faster for a small
# number of elements as sorting is handled on the client side, but only those loaded
# are considered in the sorting. SortAllItems, sorts items in the server so all items
# are considered. Although this would cost a lot when there are thousands of items, 
# only some of them are loaded and the rest are loaded on demand.
#
# Note that by default the group will handle (and eventually load) all records that match 
# the conditions imposed by 'domain' and 'filter'. Those are empty by default so creating 
# ModelRecordGroup('res.parnter') and iterating through it's items will return all partners
# in the database. If you want to ensure that the group is kept completely empty, you can
# call makeEmpty() which is equivalent to calling setFilter() with a filter that no records
# match, but without the overhead of asking the server.
#
# ModelRecordGroup will emit several kinds of signals on certain events. 
class ModelRecordGroup(QObject):

	SortVisibleItems = 1
	SortAllItems = 2

	## @brief Creates a new ModelRecordGroup object.
	# @param resource Name of the model to load. Such as 'res.partner'.
	# @param fields Dictionary with the fields to load. This value typically comes from the server.
	# @param ids Record identifiers to load in the group.
	# @param parent Only used if this ModelRecordGroup serves as a relation to another model. Otherwise it's None.
	def __init__(self, resource, fields = None, ids=[], parent=None, context={}):
		QObject.__init__(self)
		self.parent = parent
		self._context = context
		self._context.update(Rpc.session.context)
		self.resource = resource
		self.limit = Options.options.get( 'limit', 80 )
		self.rpc = RpcProxy(resource)
		if fields == None:
			self.fields = {}
		else:
			self.fields = fields
		self.mfields = {}
		self.mfields_load(self.fields.keys())

		self.records = []
		
		self.sortedField = None
		self.sortedRelatedIds = []
		self.sortedOrder = None
		self.updated = False
		self._domain = []
		self._filter = []
		self._empty = False

		#self._sortMode = self.SortVisibleItems
		if Options.options['sort_mode'] == 'visible_items':
			self._sortMode = self.SortVisibleItems
		else:
			self._sortMode = self.SortAllItems

		self.load(ids)
		self.model_removed = []
		self.on_write = ''


	# Creates the entries in 'mfields' for each key of the 'fkeys' list.
	def mfields_load(self, fkeys):
		for fname in fkeys:
			fvalue = self.fields[fname]
			fvalue['name'] = fname
			self.mfields[fname] = Field.FieldFactory.create( fvalue['type'], self, fvalue )

	## @brief Saves all the models. 
	#
	# Note that there will be one request to the server per modified or 
	# created model.
	def save(self):
		for record in self.records:
			saved = record.save()

	## @brief This function executes the 'on_write' function in the server.
	#
	# If there is a 'on_write' function associated with the model type handled by 
	# this model group it will be executed. 'editedId' should provide the 
	# id of the just saved model.
	#
	# This functionality is provided here instead of on the model because
	# the remote function might update some other models, and they need to
	# be (re)loaded.
	def written( self, editedId ):
		if not self.on_write or not editedId:
			return
		# Execute the on_write function on the server.
		# It's expected it'll return a list of ids to be loaded or reloaded.
		new_ids = getattr(self.rpc, self.on_write)( editedId, self.context() )
		model_idx = self.records.index( self.recordById( editedId ) )
		result = False
		indexes = []
		for id in new_ids:
			cont = False
			for m in self.records:
				if m.id == id:
					cont = True
					m.reload()
			if cont:
				continue
			newmod = ModelRecord(self.resource, id, parent=self.parent, group=self)
			newmod.reload()
			if not result:
				result = newmod
			newIndex = min(model_idx, len(self.records)-1)
			self.addModel(newmod, newIndex)
			indexes.append(newIndex)

		if indexes:
			self.emit( SIGNAL('recordsInserted(int,int)'), min(indexes), max(indexes) )
		return result
	
	## @brief Creates as many records as len(ids) with the ids[x] as id.
	#
	# 'ids' needs to be a list of identifiers. The addFields() function
	# can be used later to load the necessary fields for each record.
	def preload(self, ids):
		if not ids:
			return 
		start = len(self.records)
		for id in ids:
			newmod = ModelRecord(self.resource, id, parent=self.parent, group=self)
			self.addModel(newmod)
		end = len(self.records)-1
		self.emit( SIGNAL('recordsInserted(int,int)'), start, end )

	## @brief Adds a list of models as specified by 'values'.
	#
	# 'values' has to be a list of dictionaries, each of which containing fields
	# names -> values. At least key 'id' needs to be in all dictionaries.
	def loadFromValues(self, values):
		start = len(self.records)
		for value in values:
			record = ModelRecord(self.resource, value['id'], parent=self.parent, group=self)
			record.set(value)
			self.records.append(record)
			self.connect(record,SIGNAL('recordChanged( PyQt_PyObject )'), self.recordChanged )
			self.connect(record,SIGNAL('recordModified( PyQt_PyObject )'),self.recordModified)
		end = len(self.records)-1
		self.emit( SIGNAL('recordsInserted(int,int)'), start, end )
	
	## @brief Loads the list of ids in this group.
	def load(self, ids, display=True):
		if not ids:
			return True

		if not self.fields:
			self.preload( ids )
			return True

		if self._sortMode == self.SortAllItems:
			self.preload( ids )
			queryIds = ids[0:self.limit]
		else:
			queryIds = ids

		if None in queryIds:
			queryIds.remove( None )
		c = Rpc.session.context.copy()
		c.update( self.context() )
		values = self.rpc.read(queryIds, self.fields.keys(), c)
		if not values:
			return False

		if self._sortMode == self.SortAllItems:
			# If nothing else was loaded, we sort the fields in the order given
			# by 'ids' or 'self.sortedRedlatedIds' when appropiate.
			if self.sortedRelatedIds:
				# This treats the case when the sorted field is a many2one
				nulls = []
				for y in values:
					if type(y[self.sortedField]) != list:
						nulls.append( y )
				vals = []
				for x in self.sortedRelatedIds:
					for y in values:
						value = y[self.sortedField]
						if type(value) == list and y[self.sortedField][0] == x:
							vals.append( y )
							# Don't break, there can be duplicates
				if self.sortedOrder == Qt.AscendingOrder:
					vals = nulls + vals
				else:
					vals = vals + nulls
			else:
				# This treats the case when the sorted field is a non-relation field
				#vals = sorted( values, key=lambda x: ids.index(x['id']) )
				for v in values:
					id = v['id']
					self.recordById(id).set(v, signal=False)
		else:
			self.loadFromValues(values)
		return True

	## @brief Clears the list of models. It doesn't remove them.
	def clear(self):
		self.emit( SIGNAL('recordsRemoved(int,int)'), 0, len(self.records)-1 )
		self.records = []
		self.model_removed = []
	
	## @brief Returns a copy of the current context
	def context(self):
		ctx = {}
		ctx.update(self._context)
		return ctx

	## @brief Adds a model to the list
	def addModel(self, record, position=-1):
		if not record.mgroup is self:
			fields = {}
			for mf in record.mgroup.fields:
				fields[record.mgroup.fields[mf]['name']] = record.mgroup.fields[mf]
			self.addFields(fields)
			record.mgroup.addFields(self.fields)
			record.mgroup = self

		if position==-1:
			self.records.append(record)
		else:
			self.records.insert(position, record)
		record.parent = self.parent
		self.connect(record,SIGNAL('recordChanged( PyQt_PyObject )'),self.recordChanged)
		self.connect(record,SIGNAL('recordModified( PyQt_PyObject )'),self.recordModified)
		return record

	## @brief Creates a new model of the same type of the models in the group.
	#
	# If 'default' is true, the model is filled in with default values. 
	# 'domain' and 'context' are only used if default is true.
	def create(self, default=True, position=-1, domain=[], context={}):
		record = ModelRecord(self.resource, None, group=self, parent=self.parent, new=True)
		self.connect(record,SIGNAL('recordChanged( PyQt_PyObject )'),self.recordChanged)
		self.connect(record,SIGNAL('recordModified( PyQt_PyObject )'),self.recordModified)
		if default:
			ctx=context.copy()
			ctx.update( self.context() )
			record.fillWithDefaults(domain, ctx)
		self.addModel( record, position )
		if position == -1:
			start = len(self.records) - 1
		else:
			start = position
		self.emit( SIGNAL('recordsInserted(int,int)'), start, start )
		return record
	
	def recordChanged(self, model):
		self.emit( SIGNAL('recordChanged(PyQt_PyObject)'), model )

	def recordModified(self, model):
		self.emit( SIGNAL('modified()') )

	## @brief Removes a model from the model group but not from the server.
	#
	# If the model doesn't exist it will ignore it silently.
	def remove(self, record):
		if not record in self.records:
			return
		idx = self.records.index(record)
		if self.records[idx].id:
			self.model_removed.append(self.records[idx].id)
		if record.parent:
			record.parent.modified = True
		self.emit( SIGNAL('modified()') )
		self.emit( SIGNAL('recordsRemoved(int,int)'), idx, idx )
		self.records.remove(self.records[idx])

	## @brief Adds the specified fields to the model group
	#
	# Note that it updates 'fields' and 'mfields' in the group
	# and creates the necessary entries in the 'values' property of 
	# all the models. 'fields' is a dict of dicts as typically returned by 
	# the server.
	def addCustomFields(self, fields):
		to_add = []
		for f in fields.keys():
			if not f in self.fields:
				self.fields[f] = fields[f]
				self.fields[f]['name'] = f
				to_add.append(f)
			else:
				self.fields[f].update(fields[f])
		self.mfields_load(to_add)
		for fname in to_add:
			for m in self.records:
				m.values[fname] = self.mfields[fname].create(m)
		return to_add

	## @brief Adds the specified fields and loads the necessary ones from the 
	# server.
	#
	# 'fields' is a dict of dicts as typically returned by the server.
	def addFields(self, fields):
		to_add = self.addCustomFields(fields)
		if not len(self.records):
			return True

		old = []
		new = []
		for model in self.records:
			if model.id:
				if model._loaded:
					old.append(model.id)
			else:
				new.append(model)

		
		# Update existing models
		if len(old) and len(to_add):

			# Do not read from the server binary and image types 
			# They'll be loaded on demand
			binaries = [x for x in fields if fields[x]['type'] in ('binary','image')]
			others = list( set(to_add) - set(binaries) )

			if others:
				c = Rpc.session.context.copy()
				c.update( self.context() )
				values = self.rpc.read(old, others, c)
				if values:
					for v in values:
						id = v['id']
						if 'id' not in others:
							del v['id']
						self.recordById(id).set(v, signal=False)
			if binaries:
				# We set binaries to the special value None so
				# the field will know it hasn't been loaded and thus
				# load data on demand when get() is called.
				data = {}
				for x in binaries:
					data[x] = None
				for x in self.records:
					x.set( data )

		# Set defaults
		if len(new) and len(to_add):
			values = self.rpc.default_get( to_add, self.context() )
			for t in to_add:
				if t not in values:
					values[t] = False
			for mod in new:
				mod.setDefaults(values)

	## @brief Ensures all records in the group are loaded.
	def ensureAllLoaded(self):
		ids = [x.id for x in self.records if not x._loaded]
		c = Rpc.session.context.copy()
		c.update( self.context() )
		values = self.rpc.read( ids, self.fields.keys(), c )
		if values:
			for v in values:
				self.recordById( v['id'] ).set(v, signal=False)

	## @brief Returns the number of models in this group.
	def count(self):
		return len(self.records)

	def __iter__(self):
		self.ensureAllLoaded()
		return iter(self.records)

	## @brief Returns the model with id 'id'. You can use [] instead.
	# Note that it will check if the model is loaded and load it if not.
	def modelById(self, id):
		for model in self.records:
			if model.id == id:
				self.ensureModelLoaded(model)
				return model
	__getitem__ = modelById

	## @brief Returns the model at the specified row number.
	def modelByRow(self, row):
		model = self.records[row]
		if model._loaded == False:
			self.ensureModelLoaded(model)
		return model

	## @brief Returns whether model is in the list of LOADED models
	# If we use 'model in model_group' then it will try to
	# load all models and if one of the models has id False
	# an error will be fired.
	def modelExists(self, model):
		return model in self.records

	## @brief Returns the model with id 'id'. You can use [] instead.
	# Note that it will return the record (model) but won't try to load it.
	def recordById(self, id):
		for model in self.records:
			if model.id == id:
				return model

	## @brief Checks whether the specified model is fully loaded and loads
	# it if necessary.
	def ensureModelLoaded(self, model):
		if model._loaded:
			return 

		c = Rpc.session.context.copy()
		c.update( self.context() )
		ids = [x.id for x in self.records]
		pos = ids.index(model.id) / self.limit

		queryIds = ids[pos * self.limit: pos * self.limit + self.limit]
		if None in queryIds:
			queryIds.remove( None )
		values = self.rpc.read(queryIds, self.fields.keys(), c)
		if not values:
			return False

		# This treats the case when the sorted field is a non-relation field
		for v in values:
			id = v['id']
			self.recordById(id).set(v, signal=False)

	## @brief Allows setting the domain for this group of records.
	def setDomain(self, value):
		if value == None:
			self._domain = []
		else:
			self._domain = value
		self._empty = False
	
	## @brief Returns the current domain.
	def domain(self):
		return self._domain

	## @brief Allows setting a filter for this group of records.
	#
	# The filter is conatenated to the domain to further restrict the records of
	# the group.
	def setFilter(self, value):
		if value == None:
			self._filter = []
		else:
			self._filter = value
		self._empty = False
	
	## @brief Returns the current filter.
	def filter(self):
		return self._filter

	## @brief Makes the group completely empty. It's like applying a filter that
	# ensures that no record is loaded but without the need of quering the server.
	#
	# Calling setFilter() or setDomain() after this function will clear the empty flag.
	def makeEmpty(self):
		self._empty = True
		self.clear()

	## @brief Reload the model group with current selected sort field, order, domain and filter
	def update(self):
		#f = self.sortedField
		#self.sortedField = None
		## Make it reload again
		self.updated = False
		self.sort( self.sortedField, self.sortedOrder )

	## @brief Sorts the model by the given field name.
	def sort(self, field, order):
		if self._empty:
			return
		if self._sortMode == self.SortAllItems:
			self.sortAll( field, order )
		else:
			self.sortVisible( field, order )

	# Sorts the models in the group using ALL records in the database
	def sortAll(self, field, order):
		if self.updated and field == self.sortedField and order == self.sortedOrder:
			return

		# Check there're no new or modified fields. If there are
		# we won't sort as it means reloading data from the server
		# and we'd loose current changes.
		for record in self.records:
			if record.modified:
				return
			
		if not field in self.fields.keys():
			# If the field doesn't exist use default sorting. Usually this will
			# happen when we update and haven't selected a field to sort by.
			ids = self.rpc.search( self._domain + self._filter )
			self.sortedRelatedIds = []
		else:
			type = self.fields[field]['type']
			if type == 'one2many' or type == 'many2many':
				# We're not able to sort 2many fields
				return

			# A lot of the work done here should be done on the server by core OpenERP
			# functions. This means this runs slower than it should due to network and
			# serialization latency. Even more, we lack some information to make it 
			# work well.

			if type == 'many2one':
				# In the many2one case, we sort all records in the related table 
				# There's a bug here, as we consider 'name' the field that will be shown.
				# in some cases this field doesn't exist.
				orderby = 'name '
				if order == Qt.AscendingOrder:
					orderby += 'ASC'
				else:
					orderby += 'DESC'
				try:
					# Use call to catch exceptions
					self.sortedRelatedIds = Rpc.session.call('/object', 'execute', self.fields[field]['relation'], 'search', [], 0, 0, orderby )
				except:
					# Maybe name field doesn't exist :(
					# Use default order
					self.sortedRelatedIds = Rpc.session.call('/object', 'execute', self.fields[field]['relation'], 'search', [], 0, 0 )
					
				ids = self.rpc.search( self._domain + self._filter )
			else:
				orderby = field + " "
				if order == Qt.AscendingOrder:
					orderby += "ASC"
				else:
					orderby += "DESC"
				try:
					# Use call to catch exceptions
					ids = Rpc.session.call('/object', 'execute', self.resource, 'search', self._domain + self._filter, 0, 0, orderby )
				except:
					# In functional fields not stored in the database this will
					# cause an exceptioin :(
					# Use default order
					ids = Rpc.session.call('/object', 'execute', self.resource, 'search', self._domain + self._filter, 0, 0 )
				self.sortedRelatedIds = []

		# We set this fields in the end in case some exceptions where fired 
		# in previous steps.
		self.sortedField = field
		self.sortedOrder = order
		self.updated = True

		self.clear()
		# The load function will be in charge of loading and sorting elements
		self.load( ids )

	# Sorts the records of the group taking into account only loaded fields.
	def sortVisible(self, field, order):
		if self.updated and field == self.sortedField and order == self.sortedOrder:
			return

		if not self.updated:
			ids = Rpc.session.call('/object', 'execute', self.resource, 'search', self._domain + self._filter, 0, self.limit )
			self.clear()
			self.load( ids )
		
		if not field in self.fields:
			return

		if field != self.sortedField:
			# Sort only if last sorted field was different than current

			# We need this function here as we use the 'field' variable
			def ignoreCase(model):
				v = model.value(field)
				if isinstance(v, unicode) or isinstance(v, str):
					return v.lower()
				else:
					return v

			type = self.fields[field]['type']
			if type == 'one2many' or type == 'many2many':
				self.records.sort( key=lambda x: len(x.value(field).models) )
			else:
				self.records.sort( key=ignoreCase )
			if order == Qt.DescendingOrder:
				self.records.reverse()
		else:
			# If we're only reversing the order, then reverse simply reverse
			if order != self.sortedOrder:
				self.records.reverse()

		self.sortedField = field
		self.sortedOrder = order
		self.updated = True
		
	## @brief Removes all new records and marks all modified ones as not loaded.
	def cancel(self):
		for record in self.records[:]:
			if not record.id:
				self.records.remove( record )
			elif record.isModified():
				record.cancel()

	## @brief Returns True if any of the records in the group have been modified.
	def isModified(self):
		for record in self.records:
			if record.isModified():
				return True
		return False
# vim:noexpandtab:

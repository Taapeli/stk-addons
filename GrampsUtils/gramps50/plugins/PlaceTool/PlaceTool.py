#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#
# PlaceTool
# ---------
# Author: kari.kujansuu@gmail.com
# 9 Jun 2019
#
# Gramplet to change properties of multiple places at the same time.
# The properties that can be changed are:
#
# - place type
# - tag
# - enclosing place
#
# The gramplet can also generate a place hierarchy from place names or titles.
#
# For the enclosing place first select the place that should enclose the other places 
# and click the "Set enclosing place" button. The selected place will be displayed.
# Then select any number of places that should  be enclosed by the first one
# and click the "Apply to selected places" button. 
#
# A place might already have an enclosing place. In that case the new place will be added
# and the place will end up being enclosed by multiple places. This is quite OK but
# you can also remove the previous enclosing places by checking the box "Clear original enclosing places".
# This can e.g. be used to "move" the places under another place.
#
# Attempts to set a duplicate enclosing place or a loop (so that a place contains itself) 
# are quietly bypassed.
#
# You can also set the type of the selected place or assign any tag if needed.
# The operations can be combined so that e.g. the place type and enclosing place can be set 
# at the same time. Type and tag can be selected from pre-existing ones or you can type
# a new name if needed.
#
# Any existing tags can also be first removed if the "Clear tags" checkbox is marked. Otherwise
# the new tag is added the set of the tags for the places. 
#
# If the enclosing place, type or tag is not specified, then the corresponding
# setting is not changed.
#
# If a place name contains comma separated names then the gramplet can change this
# to a place hierarchy. For example if the name is of the form "place1, place2, place3"
# then two new places, place2 and place3 are created, the name of the original place
# is changed to place1 and the places are put in the hierarchy "place1 < place2 < place3".
# Duplicate place names at the same level are automatically merged. The original names
# can also be separate by spaces instead of commas - but then you must be careful that
# the names do not contain spaces.
#
# The hierarchy can also be generated in reverse, e.g. the result can also be 
# "place3 < place2 < place1" if the corresponding checkbox is marked.
#
# The place type and tag setting affects only the original place.
#
# If a new enclosing place is also specified then the new hierarchy is placed under the
# enclosing place.
#
# The "Clear selections" button will clear the form.
#
# The changes are done under a transaction and they can be undone 
# from the Gramps menu "Edit > Undo Setting place properties". 
#
# The "Filter" gramplet can be used to search for the places that need changes. This gramplet
# does not have direct support for filters.
#
# This gramplet can only be added on the Places view.
 
import json
import pprint

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Note, Tag

from gramps.gui.dialog import OkDialog

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class PlaceTool(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Set properties for multiple places"))

    def db_changed(self):
        self.__clear(None)
        
    def __typenames(self):
        for pt in self.dbstate.db.get_place_types():
            yield pt
        place_type_instance = PlaceType()
        for pt in place_type_instance.get_standard_names():
            yield pt

    def __tagnames(self):
        for handle in self.dbstate.db.get_tag_handles(sort_handles=True):
            tag = self.dbstate.db.get_tag_from_handle(handle)
            yield tag.get_name()
                    

    def __clear(self, obj):
        self.selected_handle = None        
        selected_parent = None
        self.selected_name = ""
        self.enclosing_place.set_text(_("None"))
        self.tagcombo.get_child().set_text("")
        self.typecombo.get_child().set_text("")
        self.clear_enclosing.set_active(False)
        self.clear_tags.set_active(False)
        self.generate_hierarchy.set_active(False)
        self.spaces.set_active(False)
        self.reverse.set_active(False)
    

    
    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet allows setting properties for multiple places at the same time"))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        pt_label = Gtk.Label()
        pt_label.set_markup("<b>{}</b>".format(_('Place type:')))
        pt_label.set_halign(Gtk.Align.START)
        self.typecombo = Gtk.ComboBoxText.new_with_entry()
        self.__fill_combo(self.typecombo, list(self.__typenames()),wrap_width=4)

        tag_label = Gtk.Label()
        tag_label.set_markup("<b>{}</b>".format(_('Tag:')))
        tag_label.set_halign(Gtk.Align.START)
        self.tagcombo = Gtk.ComboBoxText.new_with_entry()
        self.__fill_combo(self.tagcombo, list(self.__tagnames()))

        label1 = Gtk.Label()
        label1.set_markup("<b>{}</b>".format(_("New enclosing place")))
        label1.set_halign(Gtk.Align.START)
        label1.set_line_wrap(True)
        self.label1 = label1

        self.enclosing_place = Gtk.Label(_("None"))
        self.enclosing_place.set_halign(Gtk.Align.START)

        pt_grid = Gtk.Grid(column_spacing=10)
        pt_grid.attach(pt_label,0,0,1,1)
        pt_grid.attach(self.typecombo,1,0,1,1)
        
        pt_grid.attach(tag_label,0,1,1,1)
        pt_grid.attach(self.tagcombo,1,1,1,1)
        pt_grid.attach(label1,0,2,1,1)
        pt_grid.attach(self.enclosing_place,1,2,1,1)

        vbox.pack_start(pt_grid, False, True, 0)

        but_set_enclosing = Gtk.Button(label=_('Set enclosing place'))
        but_set_enclosing.connect("clicked", self.__select)
        vbox.pack_start(but_set_enclosing, False, True, 20)

        self.clear_enclosing = Gtk.CheckButton(_("Clear original enclosing places"))
        vbox.pack_start(self.clear_enclosing, False, True, 0)

        self.clear_tags = Gtk.CheckButton(_("Clear tags"))
        vbox.pack_start(self.clear_tags, False, True, 0)

        self.generate_hierarchy = Gtk.CheckButton(_("Generate hierarchy"))
        self.generate_hierarchy.connect("clicked", self.__select_generate_hierarchy)
        vbox.pack_start(self.generate_hierarchy, False, True, 0)

        butbox1 = Gtk.VButtonBox()
        self.spaces = Gtk.CheckButton(_("use spaces as separator"))
        self.spaces.set_sensitive(False)
        butbox1.pack_start(self.spaces, False, True, 0)

        self.reverse = Gtk.CheckButton(_("reverse hierarchy"))
        self.reverse.set_sensitive(False)
        butbox1.pack_start(self.reverse, False, True, 0)

        vbox.pack_start(butbox1, False, True, 0)

        but_clear = Gtk.Button(label=_('Clear selections'))
        but_clear.connect("clicked", self.__clear)
        vbox.pack_start(but_clear, False, True, 0)

        but_apply = Gtk.Button(label=_('Apply to selected places'))
        but_apply.connect("clicked", self.__apply)
        vbox.pack_start(but_apply, False, True, 0)

        vbox.show_all()
        return vbox

    def __fill_combo(self, combo, data_list, wrap_width=1):
        for data in sorted(data_list):
            if data:
                combo.append_text(data)

        combo.set_popup_fixed_width(False)
        combo.set_wrap_width(wrap_width)
        combo.set_entry_text_column(0)

    def __select(self,obj):
        self.selected_handle = self.uistate.get_active('Place')
        if not self.selected_handle: 
            OkDialog(_("Please select a place that will be set as an enclosing place"),
                     "",
                     parent=self.uistate.window)
            return
        selected_parent = self.dbstate.db.get_place_from_handle(self.selected_handle)
        self.selected_name = selected_parent.get_name().value + ":" + selected_parent.get_title()
        self.enclosing_place.set_text(self.selected_name)

    def __select_generate_hierarchy(self,obj):
        checked = self.generate_hierarchy.get_active()
        self.spaces.set_sensitive(checked)
        self.reverse.set_sensitive(checked)
    
    def __apply(self,obj):
        with DbTxn(_("Setting place properties"), self.dbstate.db) as self.trans:
            tagname = self.tagcombo.get_child().get_text().strip()
            if tagname:
                tag = self.__find_tag(tagname)           
            else:
                tag = None
            typename = self.typecombo.get_child().get_text().strip()
            if typename:
                ptype = PlaceType(typename)
            else:
                ptype = None
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_places = len(selected_handles)
            x = self.clear_enclosing.get_active()
            for handle in selected_handles:
                place = self.dbstate.db.get_place_from_handle(handle)
                pname = place.get_name().value
                if self.clear_enclosing.get_active():
                    self.__clear_enclosing_place(place,handle)
                if self.clear_tags.get_active():
                    self.__clear_tags(place,handle)
                if typename: self.__set_type(place,handle,typename)
                if tag: self.__set_tag(place,handle,tag)
                top = place
                if self.generate_hierarchy.get_active():
                    top = self.__generate_hierarchy(place,handle) or place
                self.__set_enclosing_place(top)

                self.dbstate.db.commit_place(place,self.trans)
                if place != top: self.dbstate.db.commit_place(top,self.trans)
    
    def __set_tag(self, place, handle, tag):
        place.add_tag(tag.handle)
    
    def __set_type(self, place, handle,ptype):
        place.set_type(ptype)
        
    def __clear_enclosing_place(self, place, handle):
        place.set_placeref_list([])

    def __clear_tags(self, place, handle):
        place.set_tag_list([])


    def __encloses(self, handle1, handle2):
        # True if handle1 encloses handle2 (possibly indirectly)
        if handle1 == handle2: return True
        place = self.dbstate.db.get_place_from_handle(handle2)
        for placeref in place.placeref_list:
            if self.__encloses(handle1, placeref.ref): return True
        return False
    
    def __set_enclosing_place(self,place):
        if not self.selected_handle: return
        if self.__encloses(place.get_handle(), self.selected_handle):  # place should not include itself
            print("Can't set",place.get_name().value,"inside",self.selected_name) 
            return
        #place = self.dbstate.db.get_place_from_handle(handle)
        pname = place.get_name().value
        if self.selected_handle in [r.ref for r in place.placeref_list]: 
            print(pname,"already enclosed by",self.selected_name)
            return # prevent duplicates
        print(pname,"<",self.selected_name)
        placeref = PlaceRef()
        placeref.ref = self.selected_handle
        place.add_placeref(placeref)


    def __find_tag(self, name):
        tag = self.dbstate.db.get_tag_from_name(name)
        if tag is None: 
            tag = Tag()                  
            tag.set_name(name)
            thandle = self.dbstate.db.add_tag(tag, self.trans)
            tag = self.dbstate.db.get_tag_from_name(name)
            self.dbstate.db.commit_tag(tag, self.trans)
        return tag  
    
    def __generate_hierarchy(self,place, handle):

        original_name = place.get_title()
        if original_name == "": 
            original_name = place.get_name().get_value()
        separator = ','
        if self.spaces.get_active():
            separator = None
            if ' ' not in original_name: return
        else:
            if ',' not in original_name: return

        names = [name.strip()
                 for name in original_name.split(separator)
                 if name.strip()]
        if self.reverse.get_active(): names.reverse()  
        place_name = PlaceName()
        place_name.set_value(names[0])
        place.set_name(place_name)
        place.set_title('')

        parent_handle = None
        top_place = place
        for name, handle in self.find_hierarchy(names)[:-1]:
            if handle is None:
                new_place = Place()
                place_name = PlaceName()
                place_name.set_value(name)
                new_place.set_name(place_name)
                if parent_handle is None:
                    #new_place.set_type(PlaceType.COUNTRY)
                    top_place = new_place
                if parent_handle is not None:
                    placeref = PlaceRef()
                    placeref.ref = parent_handle
                    new_place.add_placeref(placeref)
                parent_handle = self.dbstate.db.add_place(new_place, self.trans)
            else:
                parent_handle = handle

        if parent_handle is not None:
            placeref = PlaceRef()
            placeref.ref = parent_handle
            place.add_placeref(placeref)
        return top_place
    
    def find_hierarchy(self, names):
        out = []
        handle = None
        level = self.get_countries()
        names.reverse()  # !
        for name in names:
            if name not in level:
                out.append((name, None))
                level = {}
            else:
                handle = level[name]
                level = self.get_level(handle)
                out.append((name, handle))
        return out

    def get_level(self, handle):
        level = {}
        for obj, handle in self.dbstate.db.find_backlink_handles(handle, ['Place']):
            place = self.dbstate.db.get_place_from_handle(handle)
            level[place.get_name().get_value()] = handle
        return level

    def get_countries(self):
        countries = {}
        for handle in self.dbstate.db.find_place_child_handles(''):
            place = self.dbstate.db.get_place_from_handle(handle)
            if int(place.get_type()) != PlaceType.UNKNOWN:
                countries[place.get_name().get_value()] = handle
        return countries


    

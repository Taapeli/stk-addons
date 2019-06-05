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
# Author: kari.kujansuu@gmail.com

import json
import pprint

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Note
from gramps.gen.const import GRAMPS_LOCALE as glocale

from gramps.plugins.view.placetreeview import PlaceTreeView 

_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# SetEnclosingPlace
#
#-------------------------------------------------------------------------

class SetEnclosingPlace(Gramplet):
 
    refTag = None
    
    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        print(dir(self))

    def __create_gui(self):
        """
        Build the GUI but hide the components that are not shown initially
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("Select a place and press button to set it as an enclosing place"
                ))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        
        button_box = Gtk.ButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.START)

        but1 = Gtk.Button(label=_('Select enclosing place'))
        but1.connect("clicked", self.__select)
        button_box.add(but1)
        
        self.selected = Gtk.Label()
        self.selected.set_halign(Gtk.Align.START)

        but2 = Gtk.Button(label=_('Set enclosing place'))
        but2.connect("clicked", self.__set_enclosing_place)

        vbox.pack_start(label, False, True, 0)
        vbox.pack_start(but1, False, True, 0)
        vbox.pack_start(button_box, False, True, 10)
        vbox.pack_start(self.selected, False, True, 10)
        vbox.pack_start(but2, False, True, 0)
        vbox.show_all()
        return vbox

    def __select(self,obj):
        self.selected_handle = self.uistate.get_active('Place')
        if not self.selected_handle: return
        selected_parent = self.dbstate.db.get_place_from_handle(self.selected_handle)
        self.selected_name = selected_parent.get_name().value
        #print(dir(self.selected))
        self.selected.set_label("Selected place: " +self.selected_name)

    def __set_enclosing_place(self,obj):
        if not self.selected_handle: return
        print(type(self.uistate.viewmanager.active_page))
        if type(self.uistate.viewmanager.active_page) == PlaceTreeView: return 
        selected_handles = self.uistate.viewmanager.active_page.selected_handles()
        num_places = len(selected_handles)
        with DbTxn(_("Setting ..."), self.dbstate.db) as trans:
            for handle in selected_handles:
                if handle == self.selected_handle: continue # place should not include itself
                place = self.dbstate.db.get_place_from_handle(handle)
                pname = place.get_name().value
                print(pname,"<",self.selected_name)
                placeref = PlaceRef()
                placeref.ref = self.selected_handle
                place.add_placeref(placeref)
                self.dbstate.db.commit_place(place, trans)




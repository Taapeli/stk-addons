'''
Created on 22.3.2019

@author: TimNal
'''

import sys
import argparse
from urllib import request
import json
import pprint
import threading
import traceback
import urllib

#baseurl = "http://localhost:5000/api/v1/"
baseurl = "https://isotest.isotammi.net/api/v1/"
        
#------------------------------------------------------------------------
#
# GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk, Gdk, GObject

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.plug import Gramplet
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceName, PlaceType, PlaceRef, Url, UrlType, Note, NoteType, Source, Tag
from gramps.gen.datehandler import parser
from gramps.gen.config import config
from gramps.gen.display.place import displayer as _pd

from gramps.gui.dialog import OkDialog

"""
class PlaceType(GrampsType):

    UNKNOWN = -1
    CUSTOM = 0
    COUNTRY = 1
    STATE = 2
    COUNTY = 3
    CITY = 4
    PARISH = 5
    LOCALITY = 6
    STREET = 7
    PROVINCE = 8
    REGION = 9
    DEPARTMENT = 10
    NEIGHBORHOOD = 11
    DISTRICT = 12
    BOROUGH = 13
    MUNICIPALITY = 14
    TOWN = 15
    VILLAGE = 16
    HAMLET = 17
    FARM = 18
    BUILDING = 19
    NUMBER = 20

    _CUSTOM = CUSTOM
    _DEFAULT = UNKNOWN

    _DATAMAP = [
        (UNKNOWN, _("Unknown"), "Unknown"),
        (CUSTOM, _("Custom"), "Custom"),
        (COUNTRY, _("Country"), "Country"),
        (STATE, _("State"), "State"),
        (COUNTY, _("County"), "County"),
        (CITY, _("City"), "City"),
        (PARISH, _("Parish"), "Parish"),
        (LOCALITY, _("Locality"), "Locality"),
        (STREET, _("Street"), "Street"),
        (PROVINCE, _("Province"), "Province"),
        (REGION, _("Region"), "Region"),
        (DEPARTMENT, _("Department"), "Department"),
        (NEIGHBORHOOD, _("Neighborhood"), "Neighborhood"),
        (DISTRICT, _("District"), "District"),
        (BOROUGH, _("Borough"), "Borough"),
        (MUNICIPALITY, _("Municipality"), "Municipality"),
        (TOWN, _("Town"), "Town"),
        (VILLAGE, _("Village"), "Village"),
        (HAMLET, _("Hamlet"), "Hamlet"),
        (FARM, _("Farm"), "Farm"),
        (BUILDING, _("Building"), "Building"),
        (NUMBER, _("Number"), "Number"),
        ]

    def __init__(self, value=None):
        GrampsType.__init__(self, value)
"""


def typename_to_placetype(typename):
    for ptype,localname,name in PlaceType._DATAMAP:
        if typename == name: return ptype
        if typename == localname: return ptype
    return PlaceType.UNKNOWN
    
#------------------------------------------------------------------------
#
# Internationalisation
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class FetchRefPlaces(Gramplet):
 
    refTag = None
    
    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.type_dic = dict()
        self.refTag = self.__checkTagExistence('Referenssi', "#EF2929")           

    def __create_gui(self):
        """
        Build the GUI but hide the components that are not shown initially
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("Select a place and press button to find all matching places in the reference database. "
                "The selected place must be a 'City', 'Town', 'Municipality' or 'Parish'."
                ))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        
        button_box = Gtk.ButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.START)

        get = Gtk.Button(label=_('Search for reference places'))
        get.connect("clicked", self.__search_ref_places)
        button_box.add(get)
        
        self.place_list = Gtk.TreeView()
        self.place_list.hide()

        self.tree = Gtk.TreeView()
        self.tree.hide()

        renderer = Gtk.CellRendererText()
        self.place_list.append_column(Gtk.TreeViewColumn("Name", renderer, text=0))       
        self.place_list.append_column(Gtk.TreeViewColumn("Type", renderer, text=1))        
        self.place_list.append_column(Gtk.TreeViewColumn("Id", renderer, text=2))        

        select = self.place_list.get_selection()
        select.connect("changed", self.__on_tree_selection_changed)

        renderer = Gtk.CellRendererText()
        self.tree.append_column(Gtk.TreeViewColumn("Name", renderer, text=0))       
        self.tree.append_column(Gtk.TreeViewColumn("Type", renderer, text=1))        

        self.store_button = Gtk.Button(label=_('Store these places in the database'))
        self.store_button.connect("clicked", self.__store_ref_places)
        self.store_button.hide()

        vbox.pack_start(label, False, True, 0)
        vbox.pack_start(get, False, True, 0)
        vbox.pack_start(button_box, False, True, 10)
        vbox.pack_start(self.place_list, False, True, 10)
        vbox.pack_start(self.store_button, False, True, 10)
        vbox.pack_start(self.tree, False, True, 10)
        vbox.show_all()
        self.place_list.hide()
        self.tree.hide()
        self.store_button.hide()

        return vbox

    def __search_ref_places(self, obj):
        self.store_button.hide()
        placehandle = self.uistate.get_active("Place")
        if not placehandle: 
            OkDialog(_("No place selected"),
                 "",
                 parent=self.uistate.window)
            return 
        place = self.dbstate.db.get_place_from_handle(placehandle)
        pname = place.get_name().get_value()
        ptype = place.get_type().value
        self.place = place
        if ptype not in {PlaceType.CITY,PlaceType.TOWN,PlaceType.MUNICIPALITY,PlaceType.PARISH}: 
            OkDialog(_("Place type not supported"),
                 _("The type must be a 'City', 'Town', 'Municipality' or 'Parish'."),
                 parent=self.uistate.window)
            return 

        places = self.__fetch_ref_places(pname)
        if places is None: return
        if places == []:
            OkDialog(_("Error retrieving reference data"),
                 _("Place not found in reference data"),
                 parent=self.uistate.window)
            return

        store = Gtk.TreeStore(str,str,int)
        for place in places:
            store.append(None,[place['name'],place["type"],place["id"]])

        self.place_list.set_model(store)

        self.place_list.show()
        if self.tree: self.tree.hide()

    def __fetch_ref_places(self, name):
        url = baseurl + "search?" + urllib.parse.urlencode({"lookfor":name})
        print(url)
        try:
            json_data = urllib.request.urlopen(url).read()
        except:
            OkDialog(_("Error retrieving reference data"),
                 traceback.format_exc(),
                 parent=self.uistate.window)
            return None
            
        print(json_data)
        if not json_data: 
            OkDialog(_("Error retrieving reference data"),
                 "",
                 parent=self.uistate.window)
            return None
        data = json.loads(json_data.decode("utf-8"))
        if data['status'] != "OK": 
            OkDialog(_("Error retrieving reference data"),
                 data['statusText'],
                 parent=self.uistate.window)
            return None
        return data['records']

    
    def __on_tree_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            selected  = list(model[treeiter])
            print("You selected", selected)
            id = selected[2]
            self.__read_ref_places(id)

    def __read_ref_places(self, id):
        watch_cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.root.get_window().set_cursor(watch_cursor)
        self.store_button.hide()
        
        data = self.__fetch_sub_places(id)

        if data is None: return
        if len(data) == 0: return

        subordinates = data['surrounds']
        store = Gtk.TreeStore(str,str)

        self.__build_treestore(store,subordinates,None)

        self.tree.set_model(store)
        self.tree.show()

        self.subordinates = subordinates

        self.root.get_window().set_cursor(None)
        if len(subordinates) == 0:
            OkDialog(_("No subordinates"),
                 "",
                 parent=self.uistate.window)
            return

        self.store_button.show()
        #thread = threading.Thread(target=fetch)
        #thread.start()

    def __fetch_sub_places(self, id):
        import urllib

        url = baseurl + "record_with_subs?"  + urllib.parse.urlencode({"id":id}) 
        json_data = urllib.request.urlopen(url).read()
        if not json_data: 
            OkDialog(_("Error retrieving reference data"),
                 "",
                 parent=self.uistate.window)
            return None
        data = json.loads(json_data.decode("utf-8"))
        if data['status'] != "OK": 
            OkDialog(_("Error retrieving reference data"),
                 data['statusText'],
                 parent=self.uistate.window)
            return None
        return data["record"]

    def __build_treestore(self,store,subordinates,iter):
        for sub in subordinates:
            subname = sub['name']
            subtype = sub['type']
            iter2 = store.append(iter,[subname,subtype])
            self.__build_treestore(store,sub["surrounds"],iter2)

    def __store_ref_places(self,obj):
        self.placecount = 0
        self.newplacecount = 0
        self.duplicates = 0
        self.__store_ref_places2(self.place,self.subordinates)
        OkDialog(_("Reference places added"),
             _("Added {} new places, {} places already existed").format(self.newplacecount, self.duplicates),
             parent=self.uistate.window)

    def __store_ref_places2(self,place,subordinates):
        ptype = place.get_type().value
        pname = place.get_name().get_value()

        subplaces = []
        for cname, handle in self.dbstate.db.find_backlink_handles(place.get_handle(), ['Place']):
            subplaces.append(self.dbstate.db.get_place_from_handle(handle))
        for rsub in subordinates:
            self.placecount += 1
            subname = rsub['name']
            result = self.__checkPlaceDuplicate(subname, subplaces)
            if result:
                print(subname + ' already exists in ' + pname )
                current_sub = result
                self.duplicates += 1
            else:
                subtype = rsub['type']
                ptype = typename_to_placetype(subtype)
                current_sub = self.__addPlace(subname, ptype, refPlace=place, tag=self.refTag.handle)
                subplaces.append(current_sub)
                self.newplacecount += 1
            subs2 = rsub["surrounds"]
            self.__store_ref_places2(current_sub,subs2)
           
    def __checkPlaceDuplicate(self, pname, old_places):
        for old_place in old_places:
            if old_place.get_name().get_value() == pname:
                return old_place
        return None
 
    def __addPlace(self, pname, ptype, altNames=None, refPlace=None, tag=None):
        place = Place()
        placeName = PlaceName() 
        placeName.set_value(pname)
        place.set_name(placeName)
        if altNames:
            place.set_alternative_names(altNames)                
        place.set_type(ptype)
        if tag:
            place.add_tag(tag)
        if refPlace:
            placeRef = PlaceRef()
            placeRef.set_reference_handle(refPlace.get_handle())
            place.add_placeref(placeRef)
        with DbTxn(_("Add Place"), self.dbstate.db) as trans:
            handle = self.dbstate.db.add_place(place, trans)
            place = self.dbstate.db.get_place_from_handle(handle)
            self.dbstate.db.commit_place(place, trans)
        return place 
        
    def __checkTagExistence(self, otext, color):
        tag = self.dbstate.db.get_tag_from_name(otext)
        if tag != None: 
            #print('Tag found by name, no duplicates: ' + otext + ' ' + tag.get_name())
            pass       
        else:       
            tag = Tag()                  
            tag.set_name(otext)
            tag.set_color(color)
            with DbTxn(_("Add Tag"), self.dbstate.db) as trans:
                thandle = self.dbstate.db.add_tag(tag, trans)
                tag = self.dbstate.db.get_tag_from_name(otext)
                self.dbstate.db.commit_tag(tag, trans)
                print('Tag added: ' + tag.get_name() + ' ' + thandle)
        return tag  
        

            


           

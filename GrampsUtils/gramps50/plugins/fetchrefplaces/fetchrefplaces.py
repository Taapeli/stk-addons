'''
Created on 22.3.2019

@author: TimNal
'''

import sys
import argparse
from urllib import request
import json

#------------------------------------------------------------------------
#
# GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk

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


# LOG = logging.getLogger(".importPlaces")
from gramps.gen.utils.libformatting import ImportInfo

class FetchRefPlaces(Gramplet):
 
    all_countries = []                       # Countries in the database 
    current_country = None                   # Current country processed
    municipalities_of_current_country = []   # Municipalities in the current country
    current_municipality = None              # Current municipality processed
    villages_of_current_municipality = []    # Villages in the current municipality
    current_village = None                   # Current village processed
    farms_of_current_village = []
    current_farm = None
    buildings_of_current_farm = []

    refTag = None

    h_count = 0    # Header line count
    country_count = 0    # Country count (valtio)
    municipality_count = 0    # Municipality count (kunta)
    village_count = 0    # Village count (kylä)
    farm_count = 0    # farm count (tila)
    building_count = 0
    unknown_count = 0    # Unknown row count
    
    print("---------------------------")    

    def __get_level0(self):
        countries = []
        with self.dbstate.db.get_place_cursor() as cursor:
            pair = cursor.first()
            while pair:
                (handle, data) = pair
                print(pair)
                place = Place()
                place.unserialize(data)
                placetype = place.get_type().value
                print(placetype)
#                if getattr(PlaceType, place['type']).upper() == PlaceType.COUNTRY:
                if placetype == PlaceType.COUNTRY: 
                    print("Country found")
                    countries.append(place)
                pair = cursor.next()    
#            print(countries)
        return countries
     
    def init(self):
#        self.gdb = self.dbstate.db
        root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(root)
        root.show_all()
        self.type_dic = dict()
        self.refTag = self.__checkTagExistence('Referenssi', "#EF2929")           


    def __create_gui(self):
        """
        Create and display the GUI components of the gramplet.
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_('Enter place name:'))
        label.set_halign(Gtk.Align.START)

        self.entry = Gtk.Entry()

        button_box = Gtk.ButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.START)

        get = Gtk.Button(label=_('Get Place'))
        get.connect("clicked", self.__read_ref_places)
        button_box.add(get)

        vbox.pack_start(label, False, True, 0)
        vbox.pack_start(self.entry, False, True, 0)
        vbox.pack_start(button_box, False, True, 0)

        return vbox
    
    def main(self):
        """
        Called to update the display.
        """
        pass


    def __checkPlaceDuplicate(self, pname, old_places):
        if len(old_places) > 0:
            for old_place in old_places:
#                print('Comparing ' + pname + ' with ' + old_place.get_name().get_value())
                if old_place.get_name().get_value() == pname:
                    print('Found match ' + pname + ' with ' + old_place.get_name().get_value() + ' of type ' + old_place.__class__.__name__ ) 
                    return old_place
            return None
 
    def __addPlace(self, pname, ptype, altNames=None, refPlace=None, tag=None):
        place = Place()
        placeName = PlaceName() 
        placeName.set_value(pname)
#        placeName.set_language(priName[1])
        place.set_name(placeName)
        print(pname)
        if altNames:
            place.set_alternative_names(altNames)                
#        place.set_change_time(chgtime)
        place.set_type(ptype)
        print(ptype)
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
#            print('Place added: ' + place.get_name().get_value() + ' ' + phandle)
        return place 
        
#     def __check_Place(self, rplace, places):
#         with DbTxn(_("Read Place"), self.dbstate.db):
#             place = self.dbstate.db.get_place_from_name(rplace['pname'])
#         if place != None: 
#             print('Place found by name, no duplicates: ' +rplace['pname'] + ' ' + place.get_name())       
#         else:       
#             place = Place()                  
#             place.set_name(rplace['pname'])
# #            tag.set_color("#EF2929")
#             with DbTxn(_("Add Place"), self.dbstate.db) as trans:
#                 thandle = self.dbstate.db.add_place(place, trans)
#                 print('Place added: ' + place.get_name() + ' ' + thandle)
#         return(place)  

    def __checkTagExistence(self, otext, color):
#        with DbTxn(_("Read Tag"), self.dbstate.db):
        tag = self.dbstate.db.get_tag_from_name(otext)
        if tag != None: 
                print('Tag found by name, no duplicates: ' + otext + ' ' + tag.get_name())       
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
      
     
    def __read_ref_places(self, obj):
        from urllib import request
        from string import Template

        self.all_countries = self.__get_level0()
        for country in self.all_countries:
            print(country.get_name().get_value())
        
        name_par = self.entry.get_text() 
        
        phierarchy = name_par.split(",")       
        argv = ['http://localhost:7474/db/data/transaction/commit']  
        parser = argparse.ArgumentParser(description='Fetch a place and its subordinates from reference places database')
        parser.add_argument('in_url', help = 'Input url - reference places database.')
#        parser.print_help() 
        
        args = parser.parse_args(argv)
        
        statement =  '{  "statements" : [ {"statement" : "MATCH (c:Place)<--(n:Place)<--(m:Place) WHERE n.pname = \'$pname\' RETURN c, n, collect(m)" } ] }'
        subst = Template(statement).substitute(pname=name_par)
        url = args.in_url
    
        req = request.Request(url, bytes(subst, 'utf-8'), 
                headers={'Accept': 'application/json; charset=UTF-8',\
                          'Content-type': 'application/json',\
                          'Authorization': 'Basic bmVvNGo6ZW5vNGo='})
        with request.urlopen(req) as response:
            print("JSON data from neo4j read")
            json_data = json.loads(response.read().decode())
            print(json_data)
            if len(json_data['errors']) > 0:
                for error in data['errors']:
                    print(error)
                    return
            results = json_data['results']
#                print(results)

        columns = results[0]['columns'] if len(results) > 0 else None
        print(columns)
        data = results[0]['data'] if len(results) > 0 else None
        print(data)
        row = data[0]['row'] if len(data) > 0 else None
        rcountry = row[0] if len(row) > 0 else None
        if rcountry:
            print(rcountry)
#                self.__check_Place(country)
            result = self.__checkPlaceDuplicate(rcountry['pname'], self.all_countries)     
            if result:
                print('Country row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
#                     country = result
#                     country.set_alternative_names(altNames)
#                     with DbTxn(_("Update Country"), db) as trans:
#                         db.commit_place(country, trans)  
                self.current_country = result                              
            else:
                self.current_country = self.__addPlace(rcountry['pname'], PlaceType.COUNTRY, refPlace=None, tag=self.refTag.handle)
                self.all_countries.append(self.current_country)
            self.municipalities_of_current_country = []
            for cname, handle in self.dbstate.db.find_backlink_handles(self.current_country.get_handle(), ['Place']):
                self.municipalities_of_current_country.append(self.dbstate.db.get_place_from_handle(handle))
            print("Old municipalities " + str(len(self.municipalities_of_current_country)))    

            if len(row) > 1:                     
                rmunicipality = row[1] 
                result = self.__checkPlaceDuplicate(rmunicipality['pname'], self.municipalities_of_current_country) 
                if result:
                    print('Municipality row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                    self.current_municipality = result
                else:
                    self.current_municipality = self.__addPlace(rmunicipality['pname'], PlaceType.MUNICIPALITY, refPlace=self.current_country, tag=self.refTag.handle)
                    self.municipalities_of_current_country.append(self.current_municipality)
                    
                if len(row) > 2:
                    subordinates = row[2]
                    self.villages_of_current_municipality = []
                    for cname, handle in self.dbstate.db.find_backlink_handles(self.current_municipality.get_handle(), ['Place']):
                        self.villages_of_current_municipality.append(self.dbstate.db.get_place_from_handle(handle))
                    for rsub in subordinates:
                        result = self.__checkPlaceDuplicate(rsub['pname'], self.villages_of_current_municipality)
                        if result:
                            print('Village row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                            self.current_village = result
                        else:
                                self.current_village = self.__addPlace(rsub['pname'], PlaceType.VILLAGE, refPlace=self.current_municipality, tag=self.refTag.handle)
                                self.villages_of_current_municipality.append(self.current_village)
                else: 
                    subordinates = []   
            else:
                 print("Errors " )
                 print(json_data['errors'])    
           

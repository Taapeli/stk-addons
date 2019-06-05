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

"""
    Tools/Database Processing/Generate hierarchy from place titles
    and restore the place types from a NOTE like ""Types: <type>, <type>,..."
"""
import json

from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Tag
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.merge import MergePlaceQuery

_ = glocale.translation.gettext


def log(n,info,s):
    open("log.log","a").write("{} {} {}\n".format(n,s,info))
    
#-------------------------------------------------------------------------
#
# RestorePlaceHierarchy
#
#-------------------------------------------------------------------------
class RestorePlaceHierarchy(tool.BatchTool):
    tag = "PlaceData: " 
    
    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.user = user
        tool.BatchTool.__init__(self, dbstate, user, options_class, name)
        self.n = 0
        self.places = {}                # key=original gramps id (e.g "P0123"), value=(handle,info)
        self.notehandles = set()        # collect the notehandles to delete in this set
        self.merges = []                # collect the places needed to merge together
        self.tags = {}                  # key=tag name, value=tag handle
        if not self.fail:
            self.run()

    def run(self):
        with DbTxn(_("Restoring hierarchy"), self.db) as trans:
            self.process_in_transaction(trans)
        # merges are done in separate transactions because MergePlaceQuery does not support pre-existing transactions
        for orighandle,handle in self.merges:
            place = self.db.get_place_from_handle(handle)
            origplace = self.db.get_place_from_handle(orighandle)
            name = place.get_name().get_value()
            origname = origplace.get_name().get_value()
            print("Merge: {} ({}) to {} ({})".format(place.gramps_id,name,origplace.gramps_id,origname))
            self.merge(origplace,place)

    def merge(self,phoenix,titanic):
        query = MergePlaceQuery(self, phoenix, titanic)  # titanix will sink, phoenix will rise
        query.execute()

    def process_in_transaction(self,trans):
        self.trans = trans
        with self.user.progress(_("Restoring hierarchy"), '', 2*self.db.get_number_of_places()) as step:
            # scan all places, process the notes attached to them, store info in self.places
            for handle in self.db.get_place_handles():
                step()
                self.store_place(handle)
            # scan all notes to find notes not attached to places, create new places, store info in self.places
            for handle in self.db.get_note_handles():
                step()
                self.process_note(handle)
            # now all places should be found in self.places, set correct parents etc for all nodes
            for handle,info in self.places.values():
                step()
                self.set_parents(handle,info)
        # delete all processed notes, cannot be done earlier since there may be references from multiple places                
        print("Deleting {} notes".format(len(self.notehandles)))                
        for notehandle in self.notehandles:
            self.db.remove_note(notehandle, trans)
        self.trans = None
            
    def store_place(self,handle):
        place = self.db.get_place_from_handle(handle)
        if self.n < 10 or place.get_title().find("Harjunp") >= 0:
            print(self.n,"title:",place.get_title())
        self.n += 1
        note,notehandle = self.find_typenote(place)
        if note is None: return 
        notetext = note.get()
        info = json.loads(notetext.split(maxsplit=1)[1])
        self.set_info(place,info)
        place.remove_note(notehandle)
        self.db.commit_place(place, self.trans)
        id = info["id"]
        if id in self.places: # dup
            orighandle,originfo = self.places[id]
            self.merges.append((orighandle,handle))  # merge these later
            return
            
        self.places[id] = (handle,info)
        self.notehandles.add(notehandle)
        log(1,info,notehandle)
        #print("place: {info}".format(**locals()))

    def process_note(self,notehandle):
        if notehandle in self.notehandles: return  # already found thru a place
        note = self.db.get_note_from_handle(notehandle)
        notetext = note.get()
        if notetext.startswith(self.tag): 
            info = json.loads(notetext.split(maxsplit=1)[1])
            id = info["id"]
            if id in self.places: 
                #print("note {id} already found: {info}".format(**locals()))
                return  # already found thru a place, should not get here!
            place = Place()
            self.set_info(place,info)
            placehandle = self.db.add_place(place,self.trans)
            self.db.commit_place(place, self.trans)
            self.places[id] = (placehandle,info)
            self.notehandles.add(notehandle)
            log(2,info,notehandle)
            #print("note {id} : new place: {info}".format(**locals()))
            
    def set_info(self,place,info):
        placename = PlaceName()
        names = info["names"]
        ptype = info["type"]
        tags = info["tags"]
        primary_name = names[0]["name"]
        primary_name_lang = names[0]["lang"]
        placename.set_value(primary_name)
        placename.set_language(primary_name_lang)
        place.set_name(placename)
        place.set_title('') # ??
        self.set_type(place,ptype)
        self.set_altnames(place,names[1:])
        if tags: print("tag:",primary_name,tags)
        for tagdata in tags:
            taghandle = self.find_tag(tagdata)
            place.add_tag(taghandle)
        
    def find_tag(self,tagdata):
        tagname = tagdata["name"]
        if tagname in self.tags: return self.tags[tagname]
        tag = Tag()
        tag.set_name(tagname)
        tag.set_color(tagdata["color"])
        tag.set_priority(tagdata["priority"])
        taghandle = self.db.add_tag(tag,self.trans)
        self.tags[tagname] = taghandle
        return taghandle
        
    def set_parents(self,handle,info):
        place = self.db.get_place_from_handle(handle)
        parent_ids = info["parents"]
        for parent_id in parent_ids:
            parent_handle,parent_info = self.places[parent_id]
            placeref = PlaceRef()
            placeref.ref = parent_handle
            place.add_placeref(placeref)
        #self.set_info(place,info) can be deleted here?
        self.db.commit_place(place, self.trans)

    def set_type(self, place,ptype):
        if ptype:
            placetype = PlaceType()
            #placetype.set_from_xml_str(ptype)
            placetype.unserialize(ptype)
            place.set_type(placetype)

    def set_altnames(self, place, names):
        for pn in names:
            place_name = PlaceName()
            place_name.set_value(pn["name"])
            place_name.set_language(pn["lang"])
            place.add_alternative_name(place_name)
    
    def find_typenote(self, place):
        for notehandle in place.get_note_list():
            note = self.db.get_note_from_handle(notehandle)
            notetext = note.get()
            if notetext.startswith(self.tag): return note,notehandle
        return None,None

#------------------------------------------------------------------------
#
# RestorePlaceHierarchyOptions
#
#------------------------------------------------------------------------
class RestorePlaceHierarchyOptions(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

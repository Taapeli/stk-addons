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

"""Tools/Database Processing/Save place hierarchy types in a NOTE"""
import json
import pprint

from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Note
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

"""
A1) Talleta tyypit
   Grampsissa hierarkia: 
         Nekala   - Kaupunginosa
         Tampere  - Kaupunki
         Suomi    - Valtio tai Liittovaltio
   Gedcomiin menee:
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio


A2) Palauta hierarkia ja tyypit
   Gedcomissa on:
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio
   Grampsiin luodaan hierarkia: 
         Nekala   - Kaupunginosa
         Tampere  - Kaupunki
         Suomi    - Valtio tai Liittovaltio
   ja poistetaan ym. NOTE
   
Entä jos vaiheessa A2 PLAC- ja NOTE-kohdissa on eri määrä osia, esim.
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa
tai
         2 PLAC Nekala, Tampere
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio
         
Tai entä jos on ristiriitaisia määrityksiä         
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio
ja
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kulmakunta, Kunta, Valtio tai Liittovaltio

tai Grampsissa on jo jokin paikoista, esim,
         Tampere - Kunta
ja Gedcomissa onkin
         2 PLAC Tampere, Suomi
         3 NOTE Types: Kaupunki, Valtio tai Liittovaltio


Entä jos vaiheessa A1 on
   Grampsissa hierarkia: 
         Nekala   - Kaupunginosa
         Tampere  - Kaupunki
         Suomi    - Valtio tai Liittovaltio
   ja myös
         "Tampere, Suomi" - Kunta
   Gedcomiin menee:
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio
         2 PLAC Tampere, Suomi
         3 NOTE Types: Kunta
Mahdollinen ratkaisu: ei panna Types:-määritystä Gedcomiin, jos paikkakunnan nimessä on pilkkuja. Silloin tyyppi häviää jälkimmäiseltä paikalta....  
Toinen ratkaisu: käytetään Gedcomissa erotinmerkkinä esim. puolipistettä                
         2 PLAC Nekala; Tampere; Suomi
         3 NOTE Types: Kaupunginosa, Kaupunki, Valtio tai Liittovaltio
         2 PLAC Tampere, Suomi
         3 NOTE Types: Kunta
Kolmas ratkaisu: koodataan myös paikannimet NOTEen---
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Nekala[Kaupunginosa], Tampere[Kaupunki], Suomi[Valtio tai Liittovaltio]
         2 PLAC Tampere, Suomi
         3 NOTE Types: Tampere, Suomi[Kunta]
tai         
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: Kaupunginosa[Nekala], Kaupunki[Tampere], Valtio tai Liittovaltio[Suomi]
         2 PLAC Tampere, Suomi
         3 NOTE Types: Tampere, Suomi[Kunta]
tai vaikka JSONina_         
         2 PLAC Nekala, Tampere, Suomi
         3 NOTE Types: [{"type":"Kaupunginosa","name:"Nekala"},{...}]
         2 PLAC Tampere, Suomi
         3 NOTE Types: [{"name":"Tampere, Suomi","type":"Kunta"}]
Isotammen paikat-muunnos voisi sitten olla koskematta sellaisiin, joissa on Types-tiedossa enemmän kuin yksi tyyppi - voi olettaa että ne on jo oikein...


Osoite muuttuu Asuinpaikka-tapahtumaksi, paikka siinä ADDR-kohdassa.
Paikkoihin tulee "Vaihtoehtoinen sijainti"

"""   

#-------------------------------------------------------------------------
#
# SavePlaceHierarchy
#
#-------------------------------------------------------------------------
class SavePlaceHierarchy(tool.BatchTool):
    tag = "PlaceData: "  # Meta, Extra, Info ?

    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.user = user
        self.uistate = user.uistate
        tool.BatchTool.__init__(self, dbstate, user, options_class, name)

        if not self.fail:
            self.run()

    def run(self):
        """
        Generate the hierarchy.
        """
        print(self.uistate)
        print(self.uistate.viewmanager)
        print(self.uistate.uimanager)
        pprint.pprint(self.uistate.viewmanager.__dict__)
        pprint.pprint(self.uistate.viewmanager.active_page)
        pprint.pprint(self.uistate.viewmanager.active_page.selected_handles())
#             self.selection.selected_foreach(self.blist, mlist)
#              selected_handles(self):
        with self.user.progress(
                _("Saving hierarchy"), '',
                self.db.get_number_of_places()) as step:

            with DbTxn(_("Saving hierarchy"), self.db) as trans:

                print(_("Saving hierarchy"))
                for handle in self.db.get_place_handles():
                    step()
                    trace = False
                    place = self.db.get_place_from_handle(handle)
                    pname = place.get_name().value
                    notetext = self.tag + json.dumps(self.serialize(place))
                    note = self.addnote(place,notetext,trans,trace)
                    if trace: print("added note:",note,note.get())
                    self.db.commit_place(place, trans)

    def serialize(self,place):
        pname = place.get_name().value
        ptype = place.get_type()
        pnames = place.get_all_names()
        #print("  place:",pname,"ptype:",str(ptype))
        parents = []
        for placeref in place.get_placeref_list():
            refhandle = placeref.ref
            parentplace = self.db.get_place_from_handle(refhandle)
            parents.append(parentplace.gramps_id)
        tagdata = []
        for taghandle in place.get_tag_list():
            tag = self.db.get_tag_from_handle(taghandle)
            tagdata.append(dict(name=tag.get_name(),color=tag.get_color(),priority=tag.get_priority()))
        return dict(
            id=place.gramps_id,
            names=[dict(name=pname.value,lang=pname.lang) for pname in pnames],
            type=ptype.serialize(),
            tags=tagdata,
            parents=parents,
        )

    def addnote(self,place,notetext,trans,trace):
        "Find a note starting with self.tag (Types:) or create a new and add it to the place"
        for notehandle in place.get_note_list():
            note = self.db.get_note_from_handle(notehandle)
            old_notetext = note.get()
            if old_notetext.startswith(self.tag): 
                if trace: print("found old note")
                note.set(notetext)
                self.db.commit_note(note, trans)
                return note
        if trace: print("create a new note")
        note = Note()
        note.set(notetext)
        note_handle = self.db.add_note(note, trans)
        place.add_note(note_handle)
        self.db.commit_note(note, trans)
        return note
                    

#------------------------------------------------------------------------
#
# SavePlaceHierarchyOptions
#
#------------------------------------------------------------------------
class SavePlaceHierarchyOptions(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

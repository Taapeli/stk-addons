import json
import pprint
import re

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Event, EventRef, EventType, Tag
from gramps.gen.const import GRAMPS_LOCALE as glocale

from gramps.gui.dialog import OkDialog

_ = glocale.translation.gettext


# regex helpers
class P:
    def __init__(self,name,pat):
        self.name = name
        self.pat = pat
        self.pats = "(?P<{name}>{pat})".format(name=name,pat=pat)
       
def p(**kwargs):
    assert len(kwargs) == 1
    for name,pat in kwargs.items():
        return "(?P<{name}>{pat})".format(name=name,pat=pat)
    raise Error

def optional(pat):
    return "({pat})?".format(pat=pat)    

def match(s,*args):    
    pat = "".join(args)
    print(s)
    print(pat)
    flags = re.VERBOSE
    r = re.fullmatch(pat,s,flags)
    if r is None: return None
    class Ret: pass
    ret = Ret()
    ret.__dict__ = r.groupdict()
    return ret

class Aviopaikat(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Set properties for multiple places"))

    def db_changed(self):
        self.__clear(None)
        
    def __clear(self, obj):
        pass

    
    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet processes marriage places..."))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        btn_execute = Gtk.Button(label=_('Execute'))
        btn_execute.connect("clicked", self.__execute)
        vbox.pack_start(btn_execute, False, True, 20)


        vbox.show_all()
        return vbox

    
    def __add_resi_event(self, person, placename, date_object):
        pn = PlaceName()
        pn.set_value(placename)
        place = Place()
        place.set_name(pn)
        placehandle = self.dbstate.db.add_place(place, self.trans)

        e = Event()
        e.set_type(EventType.RESIDENCE)
        e.set_date_object(date_object)
        e.set_place_handle(placehandle)
        e.set_description("marriage")
        eventhandle = self.dbstate.db.add_event(e, self.trans)

        eref = EventRef()
        eref.ref = eventhandle
        person.add_event_ref(eref)
        self.dbstate.db.commit_person(person,self.trans)
    
    def __execute(self,obj):
        with DbTxn(_("Processing marriages"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_places = len(selected_handles)
            for eventhandle in selected_handles:
                event = self.dbstate.db.get_event_from_handle(eventhandle)
                print(event)
                if not event.get_type().is_marriage(): continue
                placehandle = event.get_place_handle()
                place = self.dbstate.db.get_place_from_handle(placehandle)
                pname = place.get_name().value
                places = self.__match2(pname)
                if not places: continue
                print(places)
                place1, husb_place, wife_place = places
                family_handles = list(self.dbstate.db.find_backlink_handles(eventhandle,['Family']))
                print(family_handles)
                for objtype,family_handle in family_handles:
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    father_handle = family.get_father_handle()
                    mother_handle = family.get_mother_handle()
                    if not father_handle or not mother_handle: continue
                    father = self.dbstate.db.get_person_from_handle(father_handle)
                    father_name = father.get_primary_name().get_name()
                    mother = self.dbstate.db.get_person_from_handle(mother_handle)
                    mother_name = mother.get_primary_name().get_name()
                    print(father_name,mother_name)
                    self.__add_resi_event(father,husb_place,event.get_date_object())
                    self.__add_resi_event(mother,wife_place,event.get_date_object())
                    pn = PlaceName()
                    pn.set_value(place1)
                    newplace = Place()
                    newplace.set_name(pn)
                    newplacehandle = self.dbstate.db.add_place(newplace, self.trans)
                    event.set_place_handle(newplacehandle)

                event.set_description("marriage")
                self.dbstate.db.commit_event(event,self.trans)
                self.dbstate.db.commit_place(place,self.trans)

    def __match(self,place):
        m = re.match(r"([^,]+),? ?\(([^/]+)/([^/]+)\)", place)
        if not m: return False
        place1 = m.group(1).strip()
        place2 = m.group(2).strip()
        place3 = m.group(3).strip()
        if place2 == "-":
            husb_place = place1
        else:
            husb_place = place2 + ", " + place1
        if place3 == "-":
            wife_place = place1
        else:
            wife_place = place3 + ", " + place1
        return place1, husb_place, wife_place
    
    def __match2(self,place): # does not work in Python 3.5 or earlier 
        non_comma = r'[^,]+'
        optional_comma = r',?'
        optional_space = r'\s?'
        leftparen = r'\('
        rightparen = r'\)'
        non_slash = r'[^/]+'
        m = match(place,
                  p(place1=non_comma),
                  p(comma1=optional_comma),
                  p(space=optional_space),
                  p(par1=leftparen),
                  p(husb_place=non_slash),
                  p(slash="/"),
                  p(wife_place=non_slash),
                  p(par2=rightparen))
        # does not work in Python 3.5 or earlier since the order of keyword args is not preserved
#        r"([^,]+),? ?\(([^/]+)/([^/]+)\)"
        if not m: return False
        place2 = m.husb_place
        place3 = m.wife_place
        if place2 == "-":
            husb_place = m.place1
        else:
            husb_place = place2 + ", " + m.place1
        if place3 == "-":
            wife_place = m.place1
        else:
            wife_place = place3 + ", " + m.place1
        return m.place1, husb_place, wife_place

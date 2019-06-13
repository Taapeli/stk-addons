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
zerototwozeros = r"0{0,2}"
oneortwodigits = r"\d{1,2}"
twodigits = r"\d{2}"
fourdigits = r"\d{4}"
dot = r"\."
dash = r"-"
sep = "[\.,-/]"
gt = "\>"
lt = "\<"

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

def fmtdate(y,m,d):
    try:
        dt = datetime.date(int(y),int(m),int(d))
        return dt.strftime("%d %b %Y").upper()
    except:
        return None

class Dates(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Correct invalid dates"))

    def db_changed(self):
        self.__clear(None)
        
    def __clear(self, obj):
        pass

    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet corrects invalid dates..."))
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        vbox.pack_start(label, False, True, 0)

        btn_execute = Gtk.Button(label=_('Execute'))
        btn_execute.connect("clicked", self.__execute)
        vbox.pack_start(btn_execute, False, True, 20)


        vbox.show_all()
        return vbox
    

    
    def __execute(self,obj):
        with DbTxn(_("Correcting invalid dates"), self.dbstate.db) as self.trans:
            selected_handles = self.uistate.viewmanager.active_page.selected_handles()
            num_places = len(selected_handles)
            for eventhandle in selected_handles:
                event = self.dbstate.db.get_event_from_handle(eventhandle)
                print(event)
                dateobj = event.get_date_object()
                datestr = dateobj.get_text()
                if dateobj.is_valid():
                    print(dateobj,"is valid")
                    continue
                if datestr == "":
                    print(dateobj,"is blank")
                    continue
                print(datestr,"is INvalid")
                newdate = self.fix_date(datestr)
                print("newdate:",newdate)
                dateobj.set_text_value(newdate)
                self.dbstate.db.commit_event(event,self.trans)

    def fix_date(self, datestr):
        class Item: pass
        item = Item()
        item.path = "RESI.DATE"
        item.tag = "DATE"
        item.value = datestr
        
        class Options: 
            def __getattr__(self,name):
                return True
        options = Options()
        newitem = self.transform(item, options, phase=1)
        if newitem == True: return datestr
        if newitem == None: raise Error
        return newitem.value
        

    def transform(self,item,options,phase):
        """
        Fix dates of the forms:
        
        31.12.1888    -> 31 DEC 1888
        31,12,1888    -> 31 DEC 1888
        31-12-1888    -> 31 DEC 1888
        31/12/1888    -> 31 DEC 1888
        1888-12-31    -> 31 DEC 1888
        .12.1888      ->    DEC 1888
        12.1888       ->    DEC 1888
        12/1888       ->    DEC 1888
        12-1888       ->    DEC 1888
        0.12.1888     ->    DEC 1888
        00.12.1888    ->    DEC 1888
        00.00.1888    ->    1888
        00 JAN 1888   ->    JAN 1888
        1950-[19]59   -> FROM 1950 TO 1959
        1950-         -> FROM 1950 
        >1950         -> FROM 1950 
        -1950         -> TO 1950 
        <1950         -> TO 1950 
        """
        self.options = options

        if item.tag == "DATE":
            value = item.value.strip()

            if options.handle_dd_mm_yyyy:
                    # 31.12.1888 -> 31 DEC 1888
                    # 31,12,1888 -> 31 DEC 1888
                    # 31-12-1888 -> 31 DEC 1888
                    # 31/12/1888 -> 31 DEC 1888
                    r = match(value,
                              p(d=oneortwodigits),sep,
                              p(m=oneortwodigits),sep,
                              p(y=fourdigits))
                    if r:
                        val = fmtdate(r.y,r.m,r.d)
                        if val:
                            item.value = val
                            return item
    
            if options.handle_zeros:
                # 0.0.1888 -> 1888
                # 00.00.1888 -> 1888
                r = match(value,zerototwozeros,dot,zerototwozeros,p(y=fourdigits))
                if r:
                    item.value = r.y
                    return item
            
                # 00.12.1888 -> DEC 1888
                # .12.1888 -> DEC 1888
                #  12.1888 -> DEC 1888
                r = match(value,zerototwozeros,dot,p(m=oneortwodigits),dot,p(y=fourdigits))
                if not r:
                    r = match(value,p(m=oneortwodigits),dot,p(y=fourdigits))
                if r:
                    val = fmtdate(r.y,r.m,1)
                    if val:
                        item.value = val[3:]
                        return item

            if options.handle_zeros2:
                # 0 JAN 1888   ->    JAN 1888
                if value.startswith("0 "):
                    item.value = item.value[2:]
                    return item
                
                # 00 JAN 1888   ->    JAN 1888
                if value.startswith("00 "):
                    item.value = item.value[3:]
                    return item
    
    
            if options.handle_intervals:
                # 1888-1899 
                r = match(value,p(y1=fourdigits),dash,p(y2=fourdigits))
                if r:
                    century = r.y1[0:2]
                    item.value = "FROM {r.y1} TO {r.y2}".format(**locals())
                    return item
    
                # 1888-99
                r = match(value,p(y1=fourdigits),dash,p(y2=twodigits))
                if r:
                    if int(r.y2) > int(r.y1[2:]): 
                        century = r.y1[0:2]
                        item.value = "FROM {r.y1} TO {century}{r.y2}".format(**locals())
                        return item
                    
            if options.handle_intervals2:
                # 1888-, >1888
                tag = item.path.split(".")[-2]
                kw = "AFT"
                if tag in ('RESI','OCCU'): kw = "FROM"
                r = match(value,p(y=fourdigits),dash)
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
                r = match(value,gt,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
    
            if options.handle_intervals3:
                # -1888, <1888
                tag = item.path.split(".")[-2]
                kw = "BE"
                if tag in ('RESI','OCCU'): kw = "ennen"
                r = match(value,dash,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals()) 
                    return item
                r = match(value,lt,p(y=fourdigits))
                if r:
                    item.value = "{kw} {r.y}".format(**locals())  
                    return item
    
            if options.handle_yyyy_mm_dd:
                # 1888-12-31
                r = match(value,p(y=fourdigits),dash,p(m=twodigits),dash,p(d=twodigits))
                if r:
                    val = fmtdate(r.y,r.m,r.d)
                    if val:
                        item.value = val
                        return item
    
            if options.handle_yyyy_mm:
                # 1888-12
                r = match(value,p(y=fourdigits),dash,p(m=twodigits))
                if r:
                    val = fmtdate(r.y,r.m,1)
                    if val:
                        item.value = val[3:]
                        return item

        return True


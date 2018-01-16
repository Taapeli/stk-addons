'''
Created on 30.11.2017

@author: TimNal
'''
 
"""
Tools/Database Processing/Process custom Note prefixes
Custom note prefixes: _CALL  -  note contains a call name

"""

from gramps.gui.plug import tool
#from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import note, person
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# Process Custom Notes
#
#-------------------------------------------------------------------------
class ProcessCustomNotes(tool.BatchTool):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.user = user
        tool.BatchTool.__init__(self, dbstate, user, options_class, name)

        if not self.fail:
            self.run()

    def run(self):
        """
        Traverse the notes to find the notes to process and the objects referring to them.
        """
        print("Running...")
        with self.user.progress(
                _("Processing notes"), '',
                self.db.get_number_of_notes()) as step:
            call_notes = {}
            targets = {}
            for handle in self.db.get_note_handles():
                step()
                note = self.db.get_note_from_handle(handle)
#                print(note.to_struct())
                print(note.type.string, ': ', note.text.get_string())
                if note.text.get_string().startswith('_CALL'):
                    call_name = (note.text.get_string())[5:]
                    call_notes[note.handle] = call_name
                    referrers = self.db.find_backlink_handles(note.handle, include_classes=None)
                    for referrer in referrers:
                        phandle = referrer[1]
                        if not phandle in targets.keys():
                            print(referrer)
                            targets[phandle] = [referrer, {note.handle: note}]
                        else:    
                            targets[phandle][1][note.handle] = note
            print(targets)                            
            """
            Find distinct set of objects referring to the notes to process.
            """                    
            for target in targets.values():        
                referrer = target[0]
                notes = target[1]
                print(target)
                if referrer[0] == 'Person':
                    person = self.db.get_person_from_handle(referrer[1])
#                    print(person.to_struct())
                    print('Primary name notes: ', person.primary_name.note_list)
                    for nhandle in person.primary_name.note_list:
                        if nhandle in notes:
                            print('PMatch')
                            person.primary_name.set_call_name(call_notes[nhandle])
                    for alt_name in person.alternate_names:
                        print('Alternate name notes: ', alt_name.note_list)
                        for nhandle in alt_name.note_list:
                            if nhandle in call_notes:
                                print('AMatch')
                                alt_name.set_call_name(call_notes[nhandle])  
                    with DbTxn(_("Edit Name"), self.db) as trans:
                        self.db.commit_person(person, trans)
                         
                else:
                    print('------------> Process referrer :', referrer) 


#------------------------------------------------------------------------
#
# GenerateNoteOptions
#
#------------------------------------------------------------------------
class GenerateNoteOptions(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

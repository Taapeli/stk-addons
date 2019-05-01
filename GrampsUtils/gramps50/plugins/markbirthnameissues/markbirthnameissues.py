'''
Created on 5.4.2017

@author: TimNal
'''
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
#

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
# 
import logging
LOG = logging.getLogger()
LOG.setLevel(logging.WARN)

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------

from gramps.gui.plug import tool
from gramps.gen.db import DbTxn
#from gramps.gui.utils import ProgressMeter
from gramps.gen.lib import Person, Name, NameType, Note, NoteType 
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
##
# MarkBirthnameIssues
#
#-------------------------------------------------------------------------

class MarkBirthnameIssues(tool.BatchTool):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        LOG.debug("Initing with Issues")
        self.user = user
        tool.BatchTool.__init__(self, dbstate, user, options_class, name)
        LOG.debug(self)
        if not self.fail:
            self.run()

    """Mark names of persons with no birth surname or other than parent's surname"""
 
#     name        = _('Persons with missing birthname or odd birth surname')
#     description = _("Matches persons with no  birth surname or other than parent surname")
#     category    = _('General tools')

    def addNewNote(self, notecontent):
        with DbTxn(_("Add New Note"), self.db) as ntrans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, ntrans)
#            self.db.commit_note(new_note, ntrans)
            return note_handle

    def addNoteToName(self, notecontent, bname):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, trans)
            bname.add_note(note_handle)
#            self.db.commit_note(bname, trans)
#             if isinstance(tobj, Person):
#                 self.db.commit_person(tobj, trans)
#             elif isinstance(tobj, Name): 
#                 self.db.commit(tobj, trans)    
 
    def addNoteToPerson(self, notecontent, aPerson):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, trans)
            aPerson.add_note(note_handle)
            self.db.commit_person(aPerson, trans)
#             if isinstance(tobj, Person):
#                 self.db.commit_person(tobj, trans)  
            return   

    def getNames(self, phandle):
        person = self.db.get_person_from_handle(phandle)
        names = [person.get_primary_name()] + person.get_alternate_names()
        return(names)        
        
                      
    def compareNymes(self, parent, nyme):
        i = 0
        for c in str(parent.name.first_name):
            if nyme[i:i+1] == c:
                i+=1
            break
        if i > 3:
            return True   
        return False
     
    def compareSurnames(self, pnames, surname):
        for name in pnames:
            if surname == str(name.get_surname()):
                return True
        return False
    
    def checkForIssues(self, person):
        bsurname = ''
        names = [person.get_primary_name()] + person.get_alternate_names()
        for pname in names:
            if pname.type == NameType.BIRTH:
                if pname.first_name == '':
                    LOG.debug("T    Birth first name empty")
                    self.addNoteToPerson('--BIRTHNAME: Christian name empty, add one.', person)
                bsurname = str(pname.get_surname())
#                bchristname = str(pname.first_name)
                bpatronyme = str(pname.suffix)
                LOG.debug("Birth surname " + bsurname)
                if bsurname == '':
                    if pname.suffix == "": 
                        LOG.debug("T    Both birth surname and patronyme/matronyme empty")
                        self.addNoteToPerson('--BIRTHNAME: Both birth surname and patronyme/matronyme empty.', person)
                    else:
                        LOG.debug("F    Birth surname empty, patronyme/matronyme given")
                    return     # Birth surname empty, patronyme/matronyme given
                else:   
                    pFamilies = person.get_parent_family_handle_list()  # Possibly several parent families
                    if len(pFamilies) == 0:
                        LOG.debug("F    Birthname %s found but no parent family exists, inconclusive " % bsurname) 
                        return             # Birthname found but no parent family exists, inconclusive     
                    for phandle in pFamilies:  
                        pFamily = self.db.get_family_from_handle(phandle)
                        fhandle = pFamily.get_father_handle()
                        mhandle = pFamily.get_mother_handle()
                        if fhandle:
#                            father = self.db.get_person_from_handle(fhandle)
                            fnames = self.getNames(fhandle)
                            if bpatronyme and not self.compareNymes(fnames, bpatronyme):
                                self.addNoteToPerson("--BIRTHNAME: Patronyme %s does not agree with fathers christian name " %  bsurname, person)
                                return
                            if bsurname and not self.compareSurnames(fnames, bsurname):    
                                self.addNoteToPerson("--BIRTHNAME: Surname %s not same as fathers surname " %  bsurname, person)
                                return  
                        if mhandle:
#                            mother = self.db.get_person_from_handle(mhandle)
                            mnames = self.getNames(mhandle)
                            if bsurname and not self.compareSurnames(mnames, bsurname):
                                self.addNoteToPerson("--BIRTHNAME: Surname %s not same as mohers surname " %  bsurname, person)
                                return
                            if bpatronyme and not self.compareNymes(mnames, bpatronyme):
                                self.addNoteToPerson("--BIRTHNAME: Matronyme %s does not agree with mothers christian name " %  bsurname, person)
                            return  
        LOG.debug("T    No birthname found, add one ")
        self.addNoteToPerson("--BIRTHNAME: No birthname found, define one.", person)                 
        return     # Problem: no birthname found

            
    def run(self):
        LOG.debug("Running Issues")
        with self.user.progress(
                _("Checking for issues"), '', self.db.get_number_of_people()) as step:
            for phandle in self.db.get_person_handles():
                step()
                self.checkForIssues(self.db.get_person_from_handle(phandle))  
  
        self.db.enable_signals()
        self.db.request_rebuild() 
               
    
#------------------------------------------------------------------------
#
# MarkBirthnameIssuesOptions
#
#------------------------------------------------------------------------
class MarkBirthnameIssuesOptions(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        LOG.debug("Initing Options")
        tool.ToolOptions.__init__(self, name, person_id)


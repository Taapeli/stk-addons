'''
Created on 5.4.2017

@author: TimNal
'''
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
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

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------

import logging
LOG = logging.getLogger("gramplets")
LOG.setLevel(logging.DEBUG)


#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

from gramps.gui.plug import tool
from gramps.gen.db import DbTxn
from gramps.gui.utils import ProgressMeter
from gramps.gen.lib import Person, Name, NameType, Note, NoteType 

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
            self.db.commit_note(new_note, ntrans)
            return note_handle

    def addNoteToName(self, notecontent, bname):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, trans)
#            note_handle = self.addNewNote(notecontent)
            bname.add_note(note_handle)
            self.db.commit(bname, trans)
#             if isinstance(tobj, Person):
#                 self.db.commit_person(tobj, trans)
#             elif isinstance(tobj, Name): 
#                 self.db.commit(tobj, trans)    
        return     
 
    def addNoteToPerson(self, notecontent, aPerson):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, trans)
#            note_handle = self.addNewNote(notecontent)
            aPerson.add_note(note_handle)
            self.db.commit_person(aPerson, trans)
#             if isinstance(tobj, Person):
#                 self.db.commit_person(tobj, trans)  
            return                 
    def compareSurnames(self, parentHandle, surname):
        parent = self.db.get_person_from_handle(parentHandle)
        pnames = [parent.get_primary_name()] + parent.get_alternate_names()
        for name in pnames:
            if surname == str(name.get_surname()):
                return True
        return False

    def checkForIssues(self, person):
        birthsurname = ''
#            person = self.db.get_person_from_handle(phandle)
        names = [person.get_primary_name()] + person.get_alternate_names()
        for pname in names:
            if pname.type == NameType.BIRTH:
                if pname.first_name == '':
                    LOG.debug("T    Birth first name empty")
                    self.addNoteToName('--CHECK: Birth first name empty, add one.', pname)
                bsurname = str(pname.get_surname())
#                LOG.debug("Birth surname " + bsurname) 
                if bsurname == '':
                    if pname.suffix == "": 
                        LOG.debug("T    Both birth surname and patronyme/matronyme empty")
                        self.addNoteToPerson('--CHECK: Both birth surname and patronyme/matronyme empty.', person)
                    else:
                        LOG.debug("F    Birth surname empty, patronyme/matronyme given")
                    return     # Birth surname empty, patronyme/matronyme given
                else:   
                    pFamilies = person.get_parent_family_handle_list()
                    if len(pFamilies) == 0:
                        LOG.debug("F    Birthname %s found but no parent family exists, inconclusive " % bsurname) 
                        return             # Birthname found but no parent family exists, inconclusive     
                    for phandle in pFamilies:
                        pFamily = self.db.get_family_from_handle(phandle)
                        fhandle = pFamily.get_father_handle()
                        if fhandle:
                            if self.compareSurnames(fhandle, bsurname):
                                LOG.debug("F    Surname %s same as fathers surname, no problem " % bsurname) 
                                return    # Surname sane as fathers surname, no problem
                        mhandle = pFamily.get_mother_handle()                            
                        if mhandle:
                            if self.compareSurnames(mhandle, bsurname):
                                LOG.debug("F    Surname %s same as mothers surname, no problem " % bsurname) 
                                return    # Surname same as mothers surname, no problem
                        LOG.debug(pname.first_name + ' ' + pname.get_surname())    
                        self.addNoteToPerson("--CHECK: No matching parent surname %s found" %  birthsurname, person)         
                        return     # Problem: No matching parent surname found
        LOG.debug("T    No birthname found, add one ")
        self.addNoteToPerson("-CHECK: No birthname found, define one.", person)                 
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
# GeneratePlaceOptions
#
#------------------------------------------------------------------------
class MarkBirthnameIssuesOptions(tool.ToolOptions):
    """
    Define options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        LOG.debug("Initing Options")
        tool.ToolOptions.__init__(self, name, person_id)


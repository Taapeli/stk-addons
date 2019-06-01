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
import unicodedata 
import re

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
          
    def genetivize(self, name, lang):
        genetive = '???'
        if lang == 'fi': 
    #                matchobj = re.search("^(\w+)([k{2}|p{2}|t{2}])([aeiouyäöå])$", name)
            matchobj = re.search("^(\w+)([k|p|t}]{2})([aeiouyäöå])$", name)                
            if matchobj:
    #                     print(matchobj.group(1))
    #                     print(matchobj.group(2))
    #                     print(matchobj.group(3))
                genetive = matchobj.group(1)+matchobj.group(2)[1:2]+matchobj.group(3)+"n"
                    
            else:
                # matchobj = re.search("^(\w+)(us)$", name)
                if name.endswith("as"):
                    genetive = name[0:-2]+"aksen" 
                elif name.endswith("ieli"):
                    genetive = name[0:-4]+"ielen"                                           
                elif name.endswith("is"):
                    genetive = name[0:-2]+"iksen"
                elif name.endswith("us"):
                    genetive = name[0:-2]+"uksen"
                elif name.endswith(('a', 'e', 'i', 'o', 'u', 'y', 'ä', 'ö', 'å')):
                    genetive = name+"n"
                else:
                    genetive = name+"in" 
        elif lang == 'se':
            if name.endswith('s'):
                genetive = name
            else:    
                genetive = name+"s"  
        return(genetive)                         
                    
    def compareNymes(self, pnames, nyme):
        lang = '??'
        fname = ''
        if   nyme.endswith(('poika', 'tytär')): lang = 'fi'
        elif nyme.endswith(('son', 'dotter', 'dr.')):  lang = 'se'
        # print(f"{lang}  {nyme} -- {pnames}")
    # Normalize stings before compare because of accented characters
        nnyme = unicodedata.normalize('NFKD', nyme).encode('ASCII','ignore')
        # nnyme = unicodedata.normalize('NFC', nyme.decode('utf8'))
        for name in pnames:
            fname = name.first_name.split(' ')
            nfname = unicodedata.normalize('NFKD', self.genetivize(fname[0], lang)).encode('ASCII','ignore')
            # nfname = str(unicodedata.normalize('NFC', name.first_name.decode('utf8')))
            # print("    Nymes:" + str(nnyme) +  " - " + str(nfname))
            # Following algorithm is a crude preliminary one,  reference names should be used instead
            
            if nnyme.startswith(nfname):
                print(f"{lang}  {nyme} = { nfname}")     
                return True 
        print(f"{lang}  {nyme} <> { nfname}")      
        return False
     
    def compareSurnames(self, pnames, surname):
        # Normalize stings before compare because of accented characters
        nsurname = unicodedata.normalize('NFKD', surname).encode('ASCII','ignore')
        # nsurname = str(unicodedata.normalize('NFC', surname.decode('utf8')))
        for name in pnames:
            npsurname = unicodedata.normalize('NFKD', str(name.get_surname())).encode('ASCII','ignore')
            # print("    " + str(nsurname) +  " - " + str(npsurname))
            if nsurname == npsurname:
            # if nsurname == str(unicodedata.normalize('NFC', name.get_surname.decode('utf8'))):
                print(f"{nsurname} =  {npsurname}")
                return True
        print(f"{nsurname} <>  {npsurname}")    
        return False
    
    def checkForIssues(self, person):
        bsurname = ''
        bnamecount = 0
        names = [person.get_primary_name()] + person.get_alternate_names()
        for pname in names:
            if pname.type == NameType.BIRTH:
                bnamecount += 1
                if pname.first_name == '':
                    # print("T    Birth first name empty")
                    self.addNoteToPerson('--BIRTHNAME: First name empty, add one.', person)
                bsurname = str(pname.get_surname())
                # print("Birth surname " + bsurname)
                bpatronyme = str(pname.suffix)
                # print("Birth patronyme " + bpatronyme)
                if bsurname == '':
                    if pname.suffix == "": 
                        # print("T    Both birth surname and patronyme/matronyme empty")
                        self.addNoteToPerson('--BIRTHNAME: Both birth surname and patronyme/matronyme empty.', person)
                        # return

                pFamilies = person.get_parent_family_handle_list()  # Possibly several parent families
                if len(pFamilies) > 0:
                    for phandle in pFamilies:  
                        pFamily = self.db.get_family_from_handle(phandle)
                        fhandle = pFamily.get_father_handle()
                        # print("  Father handle " + fhandle)
                        fnames = self.getNames(fhandle) if fhandle else None
                        mhandle = pFamily.get_mother_handle()
                        # print("  Mother handle " + mhandle)
                        mnames = self.getNames(mhandle) if mhandle else None
                        
                        if bpatronyme:
                            if fnames and self.compareNymes(fnames, bpatronyme):
                                continue
                            elif mnames and self.compareNymes(mnames, bpatronyme):
                                continue
                            else:
                                self.addNoteToPerson("--BIRTHNAME: Patronyme/matronyme %s does not agree with parents first name " %  bpatronyme, person)
                         
                        if bsurname:
                            if fnames and self.compareSurnames(fnames, bsurname):
                                continue 
                            elif mnames and self.compareSurnames(mnames, bsurname):
                                continue
                            else:   
                                self.addNoteToPerson("--BIRTHNAME: Surname %s not same as parents surname " %  bsurname, person)
                    # print("F    Birthname %s found but no parent family exists, inconclusive " % bsurname) 
        if bnamecount > 1:
            self.addNoteToPerson(f"--BIRTHNAME: Person has {bnamecount} birthnames", person)
        elif bnamecount ==  0:      
            self.addNoteToPerson("--BIRTHNAME: No birthname found, define one.", person)                 
        return     # Problem: no birthname found

            
    def run(self):
        with self.user.progress(
                _("Checking for birthname issues"), '', self.db.get_number_of_people()) as step:
            for phandle in self.db.get_person_handles():
                step()
                self.checkForIssues(self.db.get_person_from_handle(phandle))  
  
#        self.db.enable_signals()
#        self.db.request_rebuild() 
               
    
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
        tool.ToolOptions.__init__(self, name, person_id)


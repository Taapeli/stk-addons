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

from name_normalizer import NameNormalizer

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
 
from gramps.gui.plug import tool
from gramps.gen.db import DbTxn
#from gramps.gui.utils import ProgressMeter
from gramps.gen.lib import Person, Name, NameType, Note, NoteType, Tag 
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
##
# MarkBirthnameIssues
#
#-------------------------------------------------------------------------

class MarkBirthnameIssues(tool.BatchTool):
    
    first_normalizer = NameNormalizer('first')
    print('first_normalizer created')
    last_normalizer = NameNormalizer('last_extended')
    print('last_normalizer created')
    patronyme_normalizer = NameNormalizer('patronym')
    print('patronym_normalizer created')
    cod_normalizer = NameNormalizer('cause_of_death')
    print('cod_normalizer created')


    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.user = user
        tool.BatchTool.__init__(self, dbstate, user, options_class, name)
        if not self.fail:
            self.run()

    """Mark names of persons with no birth surname or other than parent's surname"""
 
#     name        = _('Persons with missing birthname or odd birth surname')
#     description = _("Matches persons with no  birth surname or other than parent surname")
#     category    = _('General tools')

      
    def checkTagExistence(self, otext):
        with DbTxn(_("Read Tag"), self.db):
            tag = self.db.get_tag_from_name(otext)
        if tag != None: 
                LOG.debug('Tag found by name, no duplicates: ' + otext + ' ' + tag.get_name())       
        else:       
            tag = Tag()                  
            tag.set_name(otext)
            tag.set_color("#EF2929")
            with DbTxn(_("Add Tag"), self.db) as trans:
                thandle = self.db.add_tag(tag, trans)
                LOG.debug('Tag added: ' + tag.get_name() + ' ' + thandle)
        return tag  
  
    def addNewNote(self, notecontent):
        with DbTxn(_("Add New Note"), self.db) as ntrans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, ntrans)
#            self.db.commit_note(new_note, ntrans)
            return note_handle

    def addNoteToName(self, notecontent, aPerson, aName):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(NoteType.RESEARCH)
            note_handle = self.db.add_note(new_note, trans)
            aName.add_note(note_handle)
            self.db.commit_note(aName, trans)
 
    def addNoteToPerson(self, type, notecontent, aPerson):
        with DbTxn(_("Add Note To Object"), self.db) as trans:
            new_note = Note(notecontent)
            new_note.set_type(type)
            note_handle = self.db.add_note(new_note, trans)
            aPerson.add_note(note_handle)
            self.db.commit_person(aPerson, trans)
            return   

    def getNames(self, phandle):
        person = self.db.get_person_from_handle(phandle)
        names = [person.get_primary_name()] + person.get_alternate_names()
        return(names)  

    def parseFirstname(self, pname):
        fname = pname.split()
          
    def genetivize(self, fname, lang):
        genetive = '???'
        name = fname.strip('*')
        if lang == 'fi': 
    #                matchobj = re.search("^(\w+)([k{2}|p{2}|t{2}])([aeiouyäöå])$", name)
            matchobj = re.search("^(\w+)([k|p|t}]{2})([aeiouyäöå])$", name)                
            if matchobj:
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
        clang = '??'
        fname = ''
        pnyme = self.patronyme_normalizer.normalize(nyme)
        if   nyme.endswith(('poika', 'tytär', 'tr')): clang = 'fi'
        elif nyme.endswith(('son', 'dotter', 'dr.')): clang = 'se'
        for name in pnames:
            fname = self.genetivize(name.first_name.split()[0], clang)
            if   nyme.endswith(('poika')): fname = fname + 'poika'
            elif nyme.endswith(('son')): fname = fname + 'son'
            elif nyme.endswith(('tytär')): fname = fname + 'tytär'
            elif nyme.endswith(('dotter')): fname = fname + 'dotter'
            fnyme = self.patronyme_normalizer.normalize(fname)
            # nfname = str(unicodedata.normalize('NFC', name.first_name.decode('utf8')))
            # print("    Nymes:" + str(nnyme) +  " - " + str(nfname))
            # Following algorithm is a crude preliminary one,  reference names should be used instead
            
            if pnyme == fnyme:
#                print(f"{lang}  {nyme} = { nfname}")     
                return True 
#        print(f"{lang}  {nyme} <> { nfname}")      
        return False
     
    def compareSurnames(self, pnames, surname):
        # Normalize stings before compare because of accented characters
        nsurname = self.last_normalizer.normalize(surname)
        for name in pnames:
            npsurname = self.last_normalizer.normalize(str(name.get_surname()))
            if nsurname == npsurname:
                return True
        print(f"{nsurname} <>  {npsurname}")    
        return False
    
    def checkForIssues(self, person):
#        fname = None

        bsurname = ''
        bnamecount = 0
        names = [person.get_primary_name()] + person.get_alternate_names()
        for pname in names:
            pid = person.gramps_id
#            surname = pname.get_surname()
#            print(f"{pid}  {surname}")
            if pname.type == NameType.BIRTH:
                bnamecount += 1

                bsurname = str(pname.get_surname())
                # print("Birth surname " + bsurname)
                bpatronyme = str(pname.suffix)
                # print("Birth patronyme " + bpatronyme)
                if bsurname == '':
                    if bpatronyme == "": 
                        # print("T    Both birth surname and patronyme/matronyme empty")
                        self.addNoteToPerson(NoteType.TODO, '--BNE001: Both birth surname and patronyme/matronyme empty.', person)

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
                                self.addNoteToPerson(NoteType.RESEARCH, f"--PNW001: Patronyme/matronyme {bpatronyme} does not agree with parents first name " , person)
                         
                        if bsurname:
                            if fnames and self.compareSurnames(fnames, bsurname):
                                continue 
                            elif mnames and self.compareSurnames(mnames, bsurname):
                                continue
                            else:   
                                self.addNoteToPerson(NoteType.RESEARCH, f"--SNW001: Surname {bsurname}  not same as parents surnames " , person)

#       Other checks and operations            
            pfnames = pname.first_name.split() 
            if not pfnames:
                # print("T    First name empty")
                self.addNoteToPerson(NoteType.TODO, '--FNE001: First name empty, add one.', person)
            else: 
#                print(pfnames)
                for fname in pfnames: 
#                    print(fname) 
                    if fname.endswith('*'):
                        print(f"First name is marked as a call name  {fname} ")
                        cname = fname.strip('*')
                        person.primary_name.set_call_name(cname)
                        
                        break
                pass                     
 
        if bnamecount > 1:
            self.addNoteToPerson(NoteType.TODO, f"--BNE001: Person has {bnamecount} birthnames, define the right one", person)
        elif bnamecount ==  0:      
            self.addNoteToPerson(NoteType.RESEARCH, "--BNW002: No birthname found, define one.", person)                 
        return     # Problem: no birthname found

            
    def run(self):
        tag = self.checkTagExistence('Name issue accepted')
        with self.user.progress(
                _("Checking for birthname issues"), '', self.db.get_number_of_people()) as step:
            for phandle in self.db.get_person_handles():
                step()
                person = self.db.get_person_from_handle(phandle)
                ptags = person.get_tag_list()
                if not tag in ptags:
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


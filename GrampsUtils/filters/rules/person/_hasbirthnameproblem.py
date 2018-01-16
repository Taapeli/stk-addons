'''
Created on 7.4.2017

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
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .. import Rule
from ....lib import Person
from ....lib import NameType

import logging
LOG = logging.getLogger("filters")
LOG.setLevel(logging.DEBUG)

cout = "C:\\temp\\result0.csv" 
#-------------------------------------------------------------------------
# Persons with missing or odd birth surname"
#-------------------------------------------------------------------------
class HasBirthnameProblem(Rule):
    """Persons with no birth surname or other than parent's surname"""
    

    name        = _('Persons with missing birthname or odd birth surname')
    description = _("Matches persons with no  birth surname or other than parent surname")
    category    = _('General filters')

    def apply(self,db,person):

        def compareSurnames(self, parentHandle, surname):
            parent = db.get_person_from_handle(parentHandle)
            pnames = [parent.get_primary_name()] + parent.get_alternate_names()
            for name in pnames:
                if surname == str(name.get_surname()):
                    return True
            return False

        def extractChristianName(self, patronyme):
            return None

        bsurname = ''
        names = [person.get_primary_name()] + person.get_alternate_names()
        for name in names:
            if name.type == NameType.BIRTH:
                bsurname = str(name.get_surname())
                bchristname = str(name.first_name)
#                LOG.debug("Birth surname " + bsurname) 
                if bsurname == '':
                    LOG.debug("F    Birth surname empty, patronyme/matronyme assumed") 
                    return False    # Empty surname, patronyme/matronyme assumed
                else:   
                    pFamilies = person.get_parent_family_handle_list()
                    if len(pFamilies) == 0:
                        LOG.debug("F    Birthname %s found but no parent family exists, inconclusive " % bsurname) 
                        return False            # Birthname found but no parent family exists, inconclusive     
                    for phandle in pFamilies:
                        pFamily = db.get_family_from_handle(phandle)
                        fhandle = pFamily.get_father_handle()
                        if fhandle:
                            if compareSurnames(self, fhandle, bsurname):
                                LOG.debug("F    Surname %s same as fathers surname, no problem " % bsurname) 
                                return False    # Surname sane as fathers surname, no problem
                        mhandle = pFamily.get_mother_handle()                            
                        if mhandle:
                            if compareSurnames(self, mhandle, bsurname):
                                LOG.debug("F    Surname %s same as mothers surname, no problem " % bsurname) 
                                return False    # Surname same as mothers surname, no problem
                    LOG.debug("T    No matching surname %s found " % bsurname)         
                    return True    # Problem: No matching surname found
        LOG.debug("T    No birthname found, add one ")                 
        return True    # Problem: no birthname found

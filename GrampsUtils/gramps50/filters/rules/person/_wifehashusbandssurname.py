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

#-------------------------------------------------------------------------
# "Wifes with husbands surname"
#-------------------------------------------------------------------------
class WifeHasHusbandsSurname(Rule):
    """Wifes that have husbands surname as other than married name"""

    name        = _('Wifes with husbands surname')
    description = _("Matches wifes that have husbands surname as other than married name")
    category    = _('General filters')

    def apply(self,db,person):
        if person.gender == Person.FEMALE:
            families = person.get_family_handle_list()
            if len(families) > 0:
                wnames = [person.get_primary_name()] + person.get_alternate_names()
                for fhandle in families:
                    hname = ''
                    hhandle = db.get_family_from_handle(fhandle).get_father_handle()
                    if hhandle != None: 
                        hname = str(db.get_person_from_handle(hhandle).get_primary_name().get_surname())
                        if hname != '':
                            for wname in wnames:
                                if wname.type != NameType.MARRIED and str(wname.get_surname()) == hname:
                                    return True
        return False

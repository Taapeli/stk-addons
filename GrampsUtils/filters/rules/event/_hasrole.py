'''
Created on 27.7.2017

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

"""
Filter rule to match persons having a personal event with a specified role.
"""
#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

import logging
LOG = logging.getLogger("filters")
LOG.setLevel(logging.INFO)

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from ....lib.event import Event
from ....lib.eventroletype import EventRoleType
from ....lib.person import Person
from .. import Rule


#-------------------------------------------------------------------------
#
# HasEvent
#
#-------------------------------------------------------------------------
class HasRole(Rule):
    """Rule that checks for events having persons referring to them with a specified role"""

    labels      = [ _('Role:'), ]
    name        =  _('Events having persons referring to them with a specified role')
    description = _('Matches events having persons referring to them with a specified role')

    def apply(self, db, event):
        print(event.serialize())
        try:
            referrers = db.find_backlink_handles(event.handle, include_classes=None)
            print(referrers.serialize())
            for referrer in referrers:
                print(referrer.serialize())
                if referrer[0] == 'Person':
                    person = db.get_person_from_handle(referrer[1])
                    print(person.to_struct())
                    return True
        except ex:
            print('Virhe ' + ex.serialize())
        return False    
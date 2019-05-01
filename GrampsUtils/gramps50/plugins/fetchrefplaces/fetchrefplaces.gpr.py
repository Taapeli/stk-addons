#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2016      TimNal
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
Gramps registration file
"""

#------------------------------------------------------------------------
#
# Import Place hierarchies from reference places database
#
#------------------------------------------------------------------------

register(GRAMPLET,
         id = "Import Reference Places",
         name = _("FetchRefPlaces"),
         description = _("Gramplet to import place hierarchies from the Isotammi reference database"),
         status = STABLE,
         version = '0.0.9',
         gramps_target_version = '5.0',
         fname = "fetchrefplaces.py",
         gramplet = 'FetchRefPlaces',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("FetchRefPlaces"),
         help_url="FetchRefPlaces Gramplet",
         include_in_listing = True,
        )

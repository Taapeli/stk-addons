#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015      Nick Hall
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
# Generate Place
#
#------------------------------------------------------------------------

register(TOOL, 
id    = 'saveplacehierarchy',
name  = _("Save place hierarchy in NOTEs"),
description  = _("Save place hierarchy and types in NOTEs"),
version = '1.0',
gramps_target_version = "5.0",
status = STABLE,
fname = 'saveplacehierarchy.py',
authors = ["Kari Kujansuu"],
authors_email = ["kari.kujansuu@gmail.com"],
category = TOOL_DBPROC,
toolclass = 'SavePlaceHierarchy',
optionclass = 'SavePlaceHierarchyOptions',
tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI]
)

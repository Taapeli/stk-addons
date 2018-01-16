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
# Process Notes
#
#------------------------------------------------------------------------

register(TOOL, 
id    = 'processcustomnotes',
name  = _("Move custom notes to proper attributes "),
description =  _("Move custom notes to proper attributes"),
version = '1.0',
gramps_target_version = "4.2",
status = STABLE,
fname = 'processcustomnotes.py',
authors = ["TimNal"],
authors_email = ["timo.nallikari@gmail.com"],
category = TOOL_DBPROC,
toolclass = 'ProcessCustomNotes',
optionclass = 'GenerateNoteOptions',
tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI]
)

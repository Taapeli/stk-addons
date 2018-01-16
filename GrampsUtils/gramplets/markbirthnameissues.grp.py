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
# Mark birthday issues with tags
#
#------------------------------------------------------------------------

register(TOOL, 
id    = 'markbirthnameissues',
name  = _("Mark birthname issues with tags"),
description =  _("Mark birthname issues with tags"),
version = '0.1',
gramps_target_version = MODULE_VERSION,
status = STABLE,
fname = 'markbirthnameissues.py',
authors = ["TimNal"],
authors_email = ["a@b.c"],
category = TOOL_DBPROC,
toolclass = 'MarkBirthnameIssues',
optionclass = 'MarkBirthnameIssuesOptions',
tool_modes = [TOOL_MODE_GUI]
    )

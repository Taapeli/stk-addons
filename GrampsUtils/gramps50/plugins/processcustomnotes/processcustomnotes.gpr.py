#
# Gramps - a GTK+/GNOME based genealogy program
#
#

"""
Gramps registration file
"""

#------------------------------------------------------------------------
#
# Process Custom Notes
#
#------------------------------------------------------------------------

register(TOOL, 
id    = 'processcustomnotes',
name  = _("Move custom notes to proper attributes "),
description =  _("Move custom notes to proper attributes"),
version = '1.0',
gramps_target_version = "5.0",
status = STABLE,
fname = 'processcustomnotes.py',
authors = ["TimNal"],
authors_email = ["timo.nallikari@gmail.com"],
category = TOOL_DBPROC,
toolclass = 'ProcessCustomNotes',
optionclass = 'ProcessCustomNotesOptions',
tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI]
)

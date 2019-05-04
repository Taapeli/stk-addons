#
# Gramps - a GTK+/GNOME based genealogy program
#
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
name  = _("Mark birthname issues with notes"),
description =  _("Mark birthname issues with todo notes"),
version = "0.1",
gramps_target_version = "5.0",
status = STABLE,
fname = 'markbirthnameissues.py',
category = TOOL_DBPROC,
toolclass = 'MarkBirthnameIssues',
optionclass = 'MarkBirthnameIssuesOptions',
tool_modes = [TOOL_MODE_GUI, TOOL_MODE_CLI]
)

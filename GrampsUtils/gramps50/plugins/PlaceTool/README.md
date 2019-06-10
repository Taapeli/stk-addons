# PlaceTool
# ---------
# Author: kari.kujansuu@gmail.com
# 9 Jun 2019
#
# Gramplet to change properties of multiple places at the same time.
# The properties that can be changed are:
#
# - place type
# - tag
# - enclosing place
#
# The gramplet can also generate a place hierarchy from place names or titles.
#
# For the enclosing place first select the place that should enclose the other places 
# and click the "Set enclosing place" button. The selected place will be displayed.
# Then select any number of places that should  be enclosed by the first one
# and click the "Apply to selected places" button. 
#
# A place might already have an enclosing place. In that case the new place will be added
# and the place will end up being enclosed by multiple places. This is quite OK but
# you can also remove the previous enclosing places by checking the box "Clear original enclosing places".
# This can e.g. be used to "move" the places under another place.
#
# Attempts to set a duplicate enclosing place or a loop (so that a place contains itself) 
# are quietly bypassed.
#
# You can also set the type of the selected place or assign any tag if needed.
# The operations can be combined so that e.g. the place type and enclosing place can be set 
# at the same time. Type and tag can be selected from pre-existing ones or you can type
# a new name if needed.
#
# Any existing tags can also be first removed if the "Clear tags" checkbox is marked. Otherwise
# the new tag is added the set of the tags for the places. 
#
# If the enclosing place, type or tag is not specified, then the corresponding
# setting is not changed.
#
# If a place name contains comma separated names then the gramplet can change this
# to a place hierarchy. For example if the name is of the form "place1, place2, place3"
# then two new places, place2 and place3 are created, the name of the original place
# is changed to place1 and the places are put in the hierarchy "place1 < place2 < place3".
# Duplicate place names at the same level are automatically merged. The original names
# can also be separate by spaces instead of commas - but then you must be careful that
# the names do not contain spaces.
#
# The hierarchy can also be generated in reverse, e.g. the result can also be 
# "place3 < place2 < place1" if the corresponding checkbox is marked.
#
# The place type and tag setting affects only the original place.
#
# If a new enclosing place is also specified then the new hierarchy is placed under the
# enclosing place.
#
# The "Clear selections" button will clear the form.
#
# The changes are done under a transaction and they can be undone 
# from the Gramps menu "Edit > Undo Setting place properties". 
#
# The "Filter" gramplet can be used to search for the places that need changes. This gramplet
# does not have direct support for filters.
#
# This gramplet can only be added on the Places view.
 
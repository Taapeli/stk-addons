'''
Created on 12.1.2017

@author: TimNal
'''
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
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


"""Import / Database Processing / Import repository-place hierarchies from cvs file """

import os
import sys
import csv
import time
import logging
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

from gramps.gen.errors import GrampsImportError
from gramps.gen.db import DbTxn
from gramps.gen.lib import Note, NoteType, Place, PlaceName, PlaceRef, PlaceType, Source, Tag
from gramps.gen.utils.libformatting import ImportInfo
# from gramps.gui.utils import ProgressMeter
# from gramps.gen.plug.utils import OpenFileOrStdin
from gramps.gen.config import config as configman

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

# LOG = logging.getLogger(".importPlaces")


#-------------------------------------------------------------------------
#
# Import Place hierarchies from a csv file
#
#-------------------------------------------------------------------------

# refstr = 'r'


pidno = None

refstr = ''

tag = None
country = None            # Current country
state = None              # Current state 
municipality = None       # Current municipality
village = None            # Current village


def importPlaceHierarchies(db, filename, user):
    
    all_countries = []                     # Countries in the database 
    municipalities_of_current_country = []   # Municipalities in the current state
    villages_of_current_municipality = []  # Villages in the current municipality
    farms_of_current_village = []
    buildings_of_current_farm = []

    
    h_count = 0    # Header line count
    country_count = 0    # Country count (valtio)
    municipality_count = 0    # Municipality count (kunta)
    village_count = 0    # Village count (kylä)
    farm_count = 0    # farm count (tila)
    building_count = 0
    unknown_count = 0    # Unknown row count
    
    def get_level0(db):
        for handle in db.find_place_child_handles(''):
            place = db.get_place_from_handle(handle)
            if int(place.get_type()) == PlaceType.COUNTRY:
                all_countries.append(place)
        return all_countries
 
    def parseNames(pname, plang='fi'):  
        pnames = pname.split(',') 
        LOG.debug('Place name %s split into %d pieces' % (pname, len(pnames)))
        priName = (pnames[0].strip(), plang) 
        altNames = []
        if len(pnames) > 1:
            del pnames[0]
            for aname in pnames:
                altName = PlaceName()
                anameparts = aname.split(':')
                if len(anameparts) == 1:
                    altName.set_value(anameparts[0].strip())
                    altName.set_language('se')
                    altNames.append(altName)
                elif len(anameparts) == 2: 
                    altName.set_value(anameparts[1].strip())
                    altName.set_language(anameparts[0].strip())
                    altNames.append(altName)
                else:
                    LOG.error('Pieleen meni? %s' % aname)
        return priName, altNames                      

    def findPlace(pid, pname):
        place = None
        if pid != '':
            with DbTxn(_("Read place"), db):
                place = db.get_place_from_id(pid)
                if place != None:    
                    LOG.info('Place read by id: ' + pid + ' ' + place.get_name().get_value())
                else:    
                    LOG.error('Place NOT found by id: ' + pid + ' ' + pname)
                    raise GrampsImportError('Place NOT found by id: ', pid + '/' + pname)
        return place  
    
    def checkPlaceDuplicate(pname, old_places):
        if len(old_places) > 0:
            for old_place in old_places:
                LOG.debug('Comparing ' + pname + ' with ' + old_place.get_name().get_value())
                if old_place.get_name().get_value() == pname:
    #                LOG.debug('Found match ' + pname + ' with ' + place.get_name().get_value() + ' of type ' + place.__class__.__name__ ) 
                    return old_place
            return None
 
    def addPlace(priName, altNames, ptype, refPlace=None):
        place = Place()
        placeName = PlaceName() 
        placeName.set_value(priName[0])
        placeName.set_language(priName[1])
        place.set_name(placeName)

        if len(altNames) > 0:
            place.set_alternative_names(altNames)                
#        place.set_change_time(chgtime)
        place.set_type(ptype)
#        place.add_tag(tags[ptype])
        place.add_tag(reftag)
        if refPlace != None:
            placeRef = PlaceRef()
            placeRef.set_reference_handle(refPlace.get_handle())
            place.add_placeref(placeRef)
#        tag.set_color("#EF2929")
        with DbTxn(_("Add Place"), db) as trans:
            phandle = db.add_place(place, trans)

            LOG.debug('Place added: ' + place.get_name().get_value() + ' ' + phandle)
        return place 
    
    def checkTagExistence(otext):

        with DbTxn(_("Read Tag"), db):
            tag = db.get_tag_from_name(otext)
        if tag != None: 
                LOG.debug('Tag found by name, no duplicates: ' + otext + ' ' + tag.get_name())       
        else:       
            tag = Tag()                  
            tag.set_name(otext)
            tag.set_color("#EF2929")
            with DbTxn(_("Add Tag"), db) as trans:
                thandle = db.add_tag(tag, trans)
                LOG.debug('Tag added: ' + tag.get_name() + ' ' + thandle)
        return tag  
      
    def findNextPidno(pidstrt):
        with DbTxn(_("Find next pidno"), db):
            prefix_save = db.get_place_prefix()
            db.set_place_id_prefix(pidstrt + '%05d')  
            next_pidno = db.find_next_place_gramps_id() 
            LOG.debug('Next pidno = ' + next_pidno)
            db.set_place_id_prefix(prefix_save) 
        return next_pidno             
                           
    chgtime = int(time.time())
    LOG.info("   chgtime = " + str(chgtime)) 
  
    fdir = os.path.dirname(filename) 
  
    fh = logging.FileHandler(fdir + '\\placeimport.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    LOG.addHandler(fh) 
                  
    LOG.info("   fdir = " + fdir)
    cout = fdir + "\\presult.csv" 
    LOG.debug('ini file handling')
     
    config = configman.register_manager("importplaces")
    config.register("options.refstring", "r") 
    config.load()
    config.save()

#    refstr = config.get('options.refstring')
    reftag = checkTagExistence('Referenssi').get_handle()
    
    '''
    tags = {}
#    Dictionary  tagtypes     placetype: tag name    
    tagTypes = {PlaceType.COUNTRY: "Referenssivaltio", 
                PlaceType.STATE: "Referenssilääni", 
                PlaceType.MUNICIPALITY: "Referenssikunta", 
                PlaceType.VILLAGE: "Referenssikylä",
                PlaceType.FARM: "Referenssitila",
                PlaceType.BUILDING: "Referenssitalo"}
           
    for key, value in tagTypes.items():
        tags[key] = checkTagExistence(value).get_handle()
    '''    
        
    all_countries = get_level0(db)
    
    recno = 0    
        
    try:
        with open(cout, 'w', newline = '\n', encoding="utf-8-sig") as csv_out:
            r_writer = csv.writer(csv_out, delimiter=';')
            with open(filename, 'r', encoding="utf-8-sig") as t_in:
#                rhandle = None
                phandle = None
                t_dialect = csv.Sniffer().sniff(t_in.read(1024))
                t_in.seek(0)
                t_reader = csv.reader(t_in, t_dialect)
                LOG.info('CSV input file delimiter is ' + t_dialect.delimiter)
                         
                for row in t_reader:
                    recno += 1
                    rectype = row[5]         # Record type = Gramps place type name (fi_FI)
#                    LOG.debug('Row type: -' + row[0] + '-')
                    if recno == 1:
                        LOG.debug('First row: ' + row[0])
                        h_count += 1  
                        r_writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])
                    else:
                        idno = row[4]                       # Possibly previously assigned Gramps object id
                        handle = row[7].strip('"')          # Possibly previously assigned Gramps object handle
                        
                        if rectype in ('Valtio', 'Country'):
                            priName,  altNames = parseNames(row[0])
                            country_count += 1
                            result = None
                            if idno != '':
                                result = findPlace(idno, priName[0])
                            else:
                                result = checkPlaceDuplicate(priName[0], all_countries)     
                            if result != None:
                                LOG.debug('Country row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                                country = result
                                country.set_alternative_names(altNames)
                                with DbTxn(_("Update Country"), db) as trans:
                                    db.commit_place(country, trans)                                
                            else:
                                country = addPlace(priName, altNames, PlaceType.COUNTRY)
                            municipalities_of_current_country = []
                            for cname, handle in db.find_backlink_handles(country.get_handle(), ['Place']):
                                municipalities_of_current_country.append(db.get_place_from_handle(handle))

                            chandle = country.get_handle()
                            cidno = country.get_gramps_id()                                
                            try: 
                                r_writer.writerow([row[0], row[1], row[2], row[3], cidno, row[5], row[6], chandle])
                            except IOError:    
                                LOG.error('Error writing country-csv '  + IOError.strerror)   
                            LOG.debug('Old municipalities ' + str(len(municipalities_of_current_country)))
                            
                        elif rectype in ('Kunta', 'Municipality', 'Kaupunki', 'Town'):
                            priName,  altNames = parseNames(row[1])
                            LOG.debug('Municipality/Town row: ' + priName[0])
                            municipality_count += 1
                            result = None
                            if idno != '':
                                result = findPlace(idno, priName[0])
                            else:
                                result = checkPlaceDuplicate(priName[0], municipalities_of_current_country) 
                            if result != None:
                                LOG.debug('Municipality row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                                municipality = result
                                municipality.set_alternative_names(altNames)
                                with DbTxn(_("Update Municipality"), db) as trans:
                                    db.commit_place(municipality, trans)                                                
                            else: 
                                if rectype in ('Kunta', 'Municipality'): 
                                    municipality = addPlace(priName, altNames, PlaceType.MUNICIPALITY, country)
                                else:
                                    municipality = addPlace(priName, altNames, PlaceType.TOWN, country) 
                                municipalities_of_current_country.append(municipality)
                            villages_of_current_municipality = []
                            for vname, handle in db.find_backlink_handles(municipality.get_handle(), ['Place']):
                                villages_of_current_municipality.append(db.get_place_from_handle(handle))

                            mhandle = municipality.get_handle()
                            midno = municipality.get_gramps_id()                    
                            try:
                                r_writer.writerow([row[0], row[1], row[2], row[3], midno, row[5], row[6], mhandle])
                            except IOError:    
                                LOG.error('Error writing municipality-csv '  + IOError.strerror)
                            LOG.debug('Old municipalities ' + str(len(municipalities_of_current_country)))    
 
                        elif rectype in ('Kylä', 'Village'):
                            priName,  altNames = parseNames(row[2]) 
                            LOG.debug('Village row: ' + priName[0])
                            village_count += 1
                            if idno != '':
                                result = findPlace(idno, priName[0])
                            else:
                                result = checkPlaceDuplicate(priName[0], villages_of_current_municipality)     
                            if result != None:
                                LOG.debug('Village row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')                                
                                village = result
                                village.set_alternative_names(altNames)              
                                with DbTxn(_("Update Village"), db) as trans:
                                    db.commit_place(village, trans)                                
                            else: 
                                village = addPlace(priName, altNames, PlaceType.VILLAGE, municipality)
                                villages_of_current_municipality.append(village) 
                            farms_of_current_village = []
                            for fname, handle in db.find_backlink_handles(village.get_handle(), ['Place']):
                                farms_of_current_village.append(db.get_place_from_handle(handle))
              
                            vhandle = village.get_handle()
                            vidno = village.get_gramps_id()                    
                            try:
                                r_writer.writerow([row[0], row[1], row[2], row[3], vidno, row[5], row[6], vhandle])
                            except IOError:    
                                LOG.error('Error writing village-csv '  + IOError.strerror) 
                            LOG.debug('Old villages ' + str(len(villages_of_current_municipality))) 
                            
                        elif rectype in ('Tila', 'Farm'):
                            priName,  altNames = parseNames(row[3])
                            LOG.debug('Farme row: ' + priName[0])
                            result = None
                            farm_count += 1
                            if handle != '':
                                result = findPlace(idno, priName[0])
                            else:
                                result = checkPlaceDuplicate(priName[0], farms_of_current_village)
                            if result != None:
                                LOG.debug('Farm row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                                farm = result
                                farm.set_alternative_names(altNames)  
                                with DbTxn(_("Update Farm"), db) as trans:
                                    db.commit_place(farm, trans)
                            else:       
                                farm = addPlace(priName, altNames, PlaceType.FARM, village)
                                farms_of_current_village.append(farm)
                                
                            buildings_of_current_farm = []
                            for bname, handle in db.find_backlink_handles(farm.get_handle(), ['Place']):
                                buildings_of_current_farm.append(db.get_place_from_handle(handle))
              
                            fhandle = farm.get_handle()
                            fidno = farm.get_gramps_id()                                
                            try: 
                                r_writer.writerow([row[0], row[1], row[2], row[3], fidno, row[5], row[6], fhandle])
                            except IOError:    
                                LOG.error('Error writing farm-csv '  + IOError.strerror) 
                            LOG.debug('Old farmss ' + str(len(farms_of_current_village))) 
                                                                
                        elif rectype in ('Rakennus', 'Building'):
                            priName,  altNames = parseNames(row[4])
                            LOG.debug('Building row: ' + priName[0])
                            result = None
                            building_count += 1
                            if handle != '':
                                result = findPlace(idno, priName[0])
                            else:
                                result = checkPlaceDuplicate(priName[0], buildings_of_current_farm)
                            if result != None:
                                LOG.debug('Building row is a duplicate of ' + result.get_name().get_value() + ' and updates the existing one)')
                                building = result
                                # &TODO: some updating  
                                with DbTxn(_("Update Farm"), db) as trans:
                                    db.commit_place(building, trans)
                            else:       
                                building = addPlace(priName, altNames, PlaceType.BUILDING, farm)
                                buildings_of_current_farm.append(building)
                                
                            bhandle = building.get_handle()
                            bidno = building.get_gramps_id()                                
                            try: 
                                r_writer.writerow([row[0], row[1], row[2], row[3], bidno, row[5], row[6], bhandle])
                            except IOError:    
                                LOG.error('Error writing building-csv '  + IOError.strerror) 
                            LOG.debug('Old buildings ' + str(len(buildings_of_current_farm)))                                     
        
                        else:
                            unknown_count += 1
                            LOG.error('Unknown rectype on line ' + str(recno) + ': ' + rectype)
                            raise GrampsImportError('Unknown record type ' + rectype)
        
    except:
        exc = sys.exc_info()[0]
        LOG.error('*** Something went really wrong! ', exc )
        
        return ImportInfo({_('Results'): _('Something went really wrong  ')})
    
    results =  {  _('Results'): _('Input file handled.')
                , _('    Countries      '): str(country_count)
                , _('    Municipalities '): str(municipality_count)
                , _('    Villages       '): str(village_count)
                , _('    Farms          '): str(farm_count)
                , _('    Buildings      '): str(building_count)
                , _('    Unknown types  '): str(unknown_count)
                , _('  Total            '): str(country_count + municipality_count + village_count + farm_count + building_count + unknown_count)  }
     
    LOG.info('Input file handled, ' + str(recno) + ' rows')
    LOG.info('    Countries      ' + str(country_count))
    LOG.info('    Municipalities ' + str(municipality_count))
    LOG.info('    Villages       ' + str(village_count))
    LOG.info('    Farms          ' + str(farm_count))
    LOG.info('    Buildings      ' + str(building_count))
    LOG.info('    Unknown types  ' + str(unknown_count))
    LOG.info('  Total            ' + str(country_count + municipality_count + village_count + farm_count + building_count + unknown_count))
    
    db.enable_signals()
    db.request_rebuild()

    return ImportInfo(results)   

                       


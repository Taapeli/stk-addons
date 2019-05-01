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
from test.badsyntax_future3 import result


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
# from gramps.gui.utils import ProgressMeter
# from gramps.gen.plug.utils import OpenFileOrStdin
# from gramps.gen.config import config as configman

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

# LOG = logging.getLogger(".importPlaces")
from gramps.gen.utils.libformatting import ImportInfo

#-------------------------------------------------------------------------
#
# Import Repositories and Sources
#
#-------------------------------------------------------------------------


def importPlaceHierarchy(db, filename, user):
    
    def findNextPidno(pidstrt):
        with DbTxn(_("Find next pidno"), db):
            db.set_repository_id_prefix(pidstrt + '%04d')  
            next_pidno = db.find_next_place_gramps_id() 
            LOG.debug('Next pidno = ' + next_pidno)
            db.set_repository_id_prefix('R%04d') 
        return next_pidno             
                       
    def findNextSidno(ridno):
        with DbTxn(_("Find next sidno"), db):
            db.set_place_id_prefix(ridno + '%03d')
            next_sidno = db.find_next_place_gramps_id() 
            LOG.debug('Next sidno = ' + next_sidno) 
            db.set_place_id_prefix('S%04d')   
        return next_sidno  
    
    def findPlace(id, handle, name):
        pid = ''
        phandle = ''
        place = None
        if handle != '':
            with DbTxn(_("Read place"), db) as trans:
                place = db.get_place_from_handle(handle)
                if place != None:    
                    LOG.info('Place read by handle: ' + handle + ' ' + place.get_name())
                else:    
                    LOG.error('Place NOT found by handle: ' + handle + ' ' + pname)
                    raise GrampsImportError('Place NOT found by handle: ', handle + '/' + pname)

        return place
 
    def addPlace(pname, ptype, refPlace=None):
        place = Place()
        placeName = PlaceName() 
        placeName.set_value(pname)
        place.set_name(placeName)
#        place.set_change_time(chgtime)
        place.set_type(ptype)
        place.add_tag(tags[ptype])
        if refPlace != None:
            placeRef = PlaceRef()
            placeRef.set_reference_handle(refPlace.get_handle())
            place.add_placeref(placeRef)
#        tag.set_color("#EF2929")
        with DbTxn(_("Add Place"), db) as trans:
            phandle = db.add_place(place, trans)
            LOG.debug('Place added: ' + place.get_name().get_value() + ' ' + phandle)
        return place                     
    
    fdir = os.path.dirname(filename) 
    '''
    fh = logging.FileHandler(fdir + '\\placeimport.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    LOG.addHandler(fh) 
    '''                  
    LOG.info("   fdir = " + fdir)
    cout = fdir + "\\result0.csv" 
    LOG.debug('ini file handling')
     
    '''  
    config = configman.register_manager("importplaces")
    config.register("options.repositoryidrng", "1000")    
    config.register("options.repositoryincr", "1") 
    config.register("options.placeidrng", "1000")    
    config.register("options.placeidincr", "1") 
    config.register("options.refstring", "r") 
    config.load()
    config.save()
    
    repository_idrange = int(config.get('options.repositoryidrng'))
    repository_incr = int(config.get('options.repositoryincr'))
    place_idrange = int(config.get('options.placeidrng'))
    place_idincr = int(config.get('options.placeidincr'))
    refstr = config.get('options.refstring')
    repository_idno  = 0
    place_idno = 0
    '''
    
    h_count = 0    # Header line count
    t_count = 0    # Tag count
    p_count = 0    # Province count (lääni)
    c_count = 0    # Community count (kunta)
    v_count = 0    # Village count (kylä)
    u_count = 0    # Unknown row count
    
    pidno = None
    sidno = None
  
    country = None  
    province = None
    municipality = None
    village = None
    
    placeTypes = {"lääni": 1, "kunta": 2, "kylä": 3}
    tags = {PlaceType.COUNTRY: "Referenssivaltio", PlaceType.PROVINCE: "Referenssilääni", PlaceType.MUNICIPALITY: "Referenssikunta", PlaceType.VILLAGE: "Referenssikylä"}       # Dictionary  recordtype: tag

    chgtime = int(time.time())
    LOG.info("   chgtime = " + str(chgtime)) 

    try:
        with open(cout, 'w', newline = '\n', encoding="utf-8") as csv_out:
            r_writer = csv.writer(csv_out, delimiter=';')
            with open(filename, 'r', encoding="utf-8") as t_in:
                rhandle = None
                phandle = None
                t_dialect = csv.Sniffer().sniff(t_in.read(1024))
                t_in.seek(0)
                t_reader = csv.reader(t_in, t_dialect)
                LOG.info('CSV input file delimiter is ' + t_dialect.delimiter)
                
                
                for row in t_reader:
                    rectype = row[0]         # Record type = Gramps place type name (fi_FI)
                    LOG.debug('Row type: -' + row[0] + '-')
                    if rectype == 'type':
                        LOG.debug('First row: ' + row[0])
                        h_count += 1  
                        r_writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])
                    else:
                        idno = row[1]                       # Possibly previously assigned Gramps object id
                        handle = row[2].strip('"')          # Possibly previously assigned Gramps object handle
                        pname = row[3].strip()
                        LOG.debug("Rectype " + rectype +'  name = ' + pname)

                        if rectype == 'valtio':
                            result = findPlace(idno, handle, pname)
                            if result != None:
                                country = result
                            else:
                                country = addPlace(pname, PlaceType.COUNTRY)
                            if handle != '':   
                                with DbTxn(_("Update Country"), db) as trans:
                                    db.commit_place(country, trans)
                            chandle = country.get_handle()
                            cidno = country.get_gramps_id()                                
                            try: 
                                r_writer.writerow([row[0], row[1],cidno, chandle, row[4], row[5], row[6], row[7]])
                            except IOError:    
                                LOG.error('Error writing country-csv '  + IOError.strerror)   
    
                            
                        elif rectype == 'lääni':
                            LOG.debug('Province row: ' + pname)
                            p_count += 1
                            result = findPlace(pidno, phandle, pname)
                            if result != None:
                                province = result                         
                                LOG.info('Province found by name, no duplicates: ' + pname + ' ' + province.get_name().get_value())       
                            else:       
                                province = addPlace(pname, PlaceType.PROVINCE, country)
                            if handle != '':   
                                with DbTxn(_("Update Province"), db) as trans:
                                    db.commit_place(province, trans)
                            phandle = province.get_handle()
                            pidno = province.get_gramps_id()                                
                            try: 
                                r_writer.writerow([row[0], row[1], pidno, phandle, row[4], row[5], row[6], row[7]])
                            except IOError:    
                                LOG.error('Error writing province-csv '  + IOError.strerror)   

                        elif rectype == 'kunta':
                            LOG.debug('Municipality row: ' + pname)
                            c_count += 1
                            result = findPlace(pidno, phandle, pname)
                            if result != None:
                                municipality = result
                            else:  
                                municipality = addPlace(pname, PlaceType.MUNICIPALITY, province)
                            if handle != '':   
                                with DbTxn(_("Update Municipality"), db) as trans:
                                    db.commit_place(municipality, trans)
                            mhandle = municipality.get_handle()
                            midno = municipality.get_gramps_id()                    
                            try:
                                r_writer.writerow([row[0], row[1], midno, mhandle, row[4], row[5], row[6], row[7]])
                            except IOError:    
                                LOG.error('Error writing municipality-csv '  + IOError.strerror)     
                            
                        elif rectype == 'kylä':
                            LOG.debug('Village row: ' + pname)
                            v_count += 1
                            result = findPlace(pidno, phandle, pname)
                            if result != None:
                                village = result
                            else: 
                                village = addPlace(pname, PlaceType.VILLAGE, municipality)           
                            if handle != '':                 
                                with DbTxn(_("Update Village"), db) as trans:
                                    db.commit_place(village, trans)
                            vhandle = village.get_handle()
                            vidno = village.get_gramps_id()                    
                            try:
                                r_writer.writerow([row[0], row[1], vidno, vhandle, row[4], row[5], row[6], row[7]])
                            except IOError:    
                                LOG.error('Error writing village-csv '  + IOError.strerror)  
    
                        else:
                            u_count += 1
                            LOG.error('Unknown rectype: ' + rectype)
                            raise GrampsImportError('Unknown record type ' + rectype)
        
    except:
        exc = sys.exc_info()[0]
        LOG.error('*** Something went really wrong! ', exc )
        
        return ImportInfo({_('Results'): _('Something went really wrong  ')})
    
    results =  {  _('Results'): _('Input file handled.')
                , _('    Tags           '): str(t_count)
                , _('    Provinces      '): str(p_count)
                , _('    Communities    '): str(c_count)
                , _('    Villages       '): str(v_count)
                , _('    Unknown types  '): str(u_count)
                , _('  Total            '): str(t_count + p_count + c_count + v_count + u_count)  }
     
    LOG.info('Input file handled.')
    LOG.info('    Tags           ' + str(t_count))
    LOG.info('    Provinces      ' + str(p_count))
    LOG.info('    Communities    ' + str(c_count))
    LOG.info('    Villages       ' + str(v_count))
    LOG.info('    Unknown types  ' + str(u_count))
    LOG.info('  Total            ' + str(t_count + p_count + c_count + v_count + u_count))
    
    db.enable_signals()
    db.request_rebuild()

    return ImportInfo(results)   

                       


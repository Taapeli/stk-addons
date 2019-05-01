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


"""Import / Database Processing / Import repository-source hierarchies from cvs file """

import os
import sys
import csv
import time
import logging
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

from gramps.gen.errors import GrampsImportError
from gramps.gen.db import DbTxn
from gramps.gen.lib import Note, NoteType, Repository, RepoRef, RepositoryType, Source, Tag
# from gramps.gui.utils import ProgressMeter
# from gramps.gen.plug.utils import OpenFileOrStdin
from gramps.gen.config import config as configman

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

# LOG = logging.getLogger(".importSources")
from gramps.gen.utils.libformatting import ImportInfo

#-------------------------------------------------------------------------
#
# Import Repositories and Sources
#
#-------------------------------------------------------------------------



def importSources(db, filename, user):
    
    def findNextRidno(ridstrt):
        with DbTxn(_("Find next ridno"), db):
            db.set_repository_id_prefix(ridstrt + '%03d')  
            next_ridno = db.find_next_repository_gramps_id() 
            LOG.debug('Next ridno = ' + next_ridno)
            db.set_repository_id_prefix('R%04d') 
        return next_ridno             
                       
    def findNextSidno(ridno):
        with DbTxn(_("Find next sidno"), db):
            db.set_source_id_prefix(ridno + '%03d')
            next_sidno = db.find_next_source_gramps_id() 
            LOG.debug('Next sidno = ' + next_sidno) 
            db.set_source_id_prefix('S%04d')   
        return next_sidno             
    
    fdir = os.path.dirname(filename) 
    '''
    fh = logging.FileHandler(fdir + '\\sourceimport.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    LOG.addHandler(fh) 
    '''                  
    LOG.info("   fdir = " + fdir)
    cout = fdir + "\\result0.csv" 
    LOG.debug('ini file handling')
   
    config = configman.register_manager("importsources")
    '''
    config.register("options.repositoryidrng", "1000")    
    config.register("options.repositoryincr", "1") 
    config.register("options.sourceidrng", "1000")    
    config.register("options.sourceidincr", "1") 
    ''' 
    config.register("options.refstring", "r")

    config.load()
    config.save()
    '''     
    repository_idrange = int(config.get('options.repositoryidrng'))
    repository_incr = int(config.get('options.repositoryincr'))
    source_idrange = int(config.get('options.sourceidrng'))
    source_idincr = int(config.get('options.sourceidincr'))
    '''
    refstr = config.get('options.refstring')
    '''
    repository_idno  = 0
    source_idno = 0
    '''
                      
    t_count = 0
    r_count = 0
    s_count = 0
    c_count = 0
    u_count = 0
    
    ridno = None
    sidno = None
    
    tags = {}       # Dictionary  recordtype: tag

    chgtime = int(time.time())
    LOG.info("   chgtime = " + str(chgtime)) 

    try:
        with open(cout, 'w', newline = '\n', encoding="utf-8") as csv_out:
            r_writer = csv.writer(csv_out, delimiter=';')
            with open(filename, 'r', encoding="utf-8") as t_in:
                rhandle = None
                t_dialect = csv.Sniffer().sniff(t_in.read(1024))
                t_in.seek(0)
                t_reader = csv.reader(t_in, t_dialect)
                LOG.info('CSV input file delimiter is ' + t_dialect.delimiter)
                for row in t_reader:
                    
                    rectype = row[0]         # Record type = Gramps object id prefix character
                    LOG.debug('Row type: -' + row[0] + '-')
                    if rectype == '#':
                        LOG.debug('Comment row: ' + row[0])
                        c_count += 1  
                        r_writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])

                    else:
                        idno = row[2]                       # Possibly previously assigned Gramps object id
                        handle = row[3].strip('"')          # Possibly previously assigned Gramps object handle
                        otext = row[4].strip()
                        LOG.debug('Handle = ' + handle)
                    
                        if rectype == 'T':
                            LOG.debug('Tag row: ' + row[0])
                            thandle = ''
                            t_count += 1
                            recobj  = row[1]     # Tag related to repositories or sources
                            tag = None
                            with DbTxn(_("Read Tag"), db):
                                tag = db.get_tag_from_name(otext)
                            if tag != None: 
                                LOG.info('Tag found by name, no duplicates: ' + otext + ' ' + tag.get_name())       
                                thandle = tag.get_handle()
                            else:       
                                tag = Tag()                  
                                tag.set_name(otext)
                                tag.set_change_time(chgtime)
                                tag.set_color("#EF2929")
                                with DbTxn(_("Add Tag"), db) as trans:
                                    thandle = db.add_tag(tag, trans)
                                    LOG.info('Tag added: ' + tag.get_name() + ' ' + thandle)
                            tags[recobj] = tag
                            try: 
                                r_writer.writerow([rectype, recobj, '', '"' + thandle + '"', otext, '', '', '', ''])
                            except IOError:    
                                LOG.error('Error writing T-csv '  + IOError.strerror)   
            
                        elif rectype == 'R':
                            LOG.debug('Repository row: ' + row[0])
                            rhandle = ''
#                            source_idno = 0
                            r_count += 1
                            repotype = row[1]         # repository type number
                            if idno == '':
                                # repository type based numbering should be applied but not supplied by Gramps
                                ridno = findNextRidno(rectype + 'r' + repotype)
#                                repository_idno = repository_idno + repository_incr
#                                ridno = rectype + refstr + str(int(repotype) * repository_idrange + repository_idno)
                            else:
                                ridno = idno 
                            LOG.debug('Ridno = ' + str(ridno))    
                            repository = Repository() 
                            if handle != '':
                                with DbTxn(_("Read Repository"), db) as trans:
                                    repository = db.get_repository_from_handle(handle)
                                    if repository == None:        
                                        LOG.error('Repository NOT found by handle: ' + handle + ' ' + otext)
                                        raise GrampsImportError('Repository NOT found by handle: ', handle + '/' + otext)   
                            repositoryType = RepositoryType()
                            repositoryType.set(int(repotype))       
                            repository.set_type(repositoryType)
                            repository.set_gramps_id(ridno)
                            repository.set_name(otext)
                            repository.set_change_time(chgtime)
                            if tags.get(rectype) != None:
                                repository.add_tag(tags[rectype].get_handle())
                            if handle == '':                 
                                with DbTxn(_("Add Repository"), db) as trans:
                                    rhandle = db.add_repository(repository, trans)
                            else:   
                                with DbTxn(_("Update Repository"), db) as trans:
                                    db.commit_repository(repository, trans)
                                    rhandle = handle    
                            try:
                                r_writer.writerow([rectype, repotype, ridno, '"' + rhandle + '"', otext, '', '', '', ''])
                            except IOError:    
                                LOG.error('Error writing R-csv '  + IOError.strerror)     
                            
                        elif rectype == 'S':
                            LOG.debug('Source row: ' + row[0])
                            shandle = ''
                            sidno = ''
                            s_count += 1
                            attribs = (row[5], row[6], row[7]) 

                            if idno == '':
                                LOG.debug('Ridno for sidno = ' + str(ridno))                             
                                sidno = findNextSidno(ridno)   
#                                source_idno = source_idno + source_idincr
#                                sidno = rectype + refstr + str((int(repotype) * repository_idrange + repository_idno) * source_idrange + source_idno)
                            else:
                                sidno = idno 
                            LOG.debug('Sidno = ' + str(sidno))   
                            source = Source()
                            if handle != '':
                                with DbTxn(_("Read Source"), db) as trans:
                                    source = db.get_source_from_handle(handle)
                                    if source == None:        
                                        LOG.error('Source NOT found by handle: ' + handle + ' ' + otext)
                                        raise GrampsImportError('Source NOT found by handle: ', handle + '/' + otext)   
                            source.set_gramps_id(sidno)
                            source.set_title(otext)
                            source.set_author(attribs[0])
                            source.set_publication_info(attribs[1])
                            source.set_abbreviation(attribs[2])
                            if tags.get(rectype) != None:
                                source.add_tag(tags[rectype].get_handle())
                            repoRef = RepoRef()
                            repoRef.set_reference_handle(rhandle) 
                            source.add_repo_reference(repoRef)
                            source.set_change_time(chgtime)
                            if handle == '':                 
                                with DbTxn(_("Add Source"), db) as trans:
                                    shandle = db.add_source(source, trans)
                            else:   
                                with DbTxn(_("Update Source"), db) as trans:
                                    db.commit_source(source, trans)
                                    shandle = handle    
                            try:
                                r_writer.writerow([rectype, '', sidno, '"' + shandle + '"', otext, attribs[0], attribs[1], attribs[2], ''])
                            except IOError:    
                                LOG.error('Error writing S-csv '  + IOError.strerror)  
     
    
                        else:
                            u_count += 1
                            LOG.debug('Unknown rectype: ' + rectype)
                            raise GrampsImportError('Unknown record type ' + rectype) 
        
    except:
        exc = sys.exc_info()[0]
        LOG.error('*** Something went really wrong! ', exc )
        
        return ImportInfo({_('Results'): _('Something went really wrong  ')})
    
    results =  {  _('Results'): _('Input file handled.')
                , _('    Tags           '): str(t_count)
                , _('    Repositories   '): str(r_count)
                , _('    Comments       '): str(c_count)
                , _('    Unknown types  '): str(u_count)
                , _('  Total            '): str(t_count + r_count + s_count + c_count + u_count)  }
     
    LOG.info('Input file handled.')
    LOG.info('    Tags           ' + str(t_count))
    LOG.info('    Repositories   ' + str(r_count))
    LOG.info('    Sources        ' + str(s_count))
    LOG.info('    Comments       ' + str(c_count))
    LOG.info('    Unknown types  ' + str(u_count))
    LOG.info('  Total            ' + str(t_count + r_count + s_count + c_count + u_count))
    
    db.enable_signals()
    db.request_rebuild()

    return ImportInfo(results)   

                       


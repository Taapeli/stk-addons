'''
Created on 1.2.2017

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


"""Import / Database Processing / Import repository-source hierarchies from scvs file """

import os
import sys
import csv
import time
import logging
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

from gramps.gen.errors import GrampsImportError
from gramps.gen.db import DbTxn
from gramps.gen.lib import Note, NoteType, Repository, RepoRef, RepositoryType, Source, Tag, Url, UrlType
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



def importReferenceSources(db, filename, user):
    
    def findNextRidno(ridstrt):
        with DbTxn(_("Find next ridno"), db):
            prefix_save = db.get_repository_prefix()
            db.set_repository_id_prefix(ridstrt + '%04d')  
            next_ridno = db.find_next_repository_gramps_id() 
            LOG.debug('Next ridno = ' + next_ridno)
            db.set_repository_id_prefix(prefix_save) 
        return next_ridno             
                       
    def findNextSidno(ridno):
        with DbTxn(_("Find next sidno"), db):
            prefix_save = db.get_source_prefix()
            db.set_source_id_prefix(ridno + '%04d')
            next_sidno = db.find_next_source_gramps_id() 
            LOG.debug('Next sidno = ' + next_sidno) 
            db.set_source_id_prefix(prefix_save)   
        return next_sidno             

    def addRepository(repositoryName, repositoryUrl, reftag):
        ridno = db.find_next_repository_gramps_id()
        repository = Repository() 
        repositoryType = RepositoryType()
        repositoryType.set(RepositoryType.ARCHIVE)
        repository.set_type(repositoryType)
        repository.set_gramps_id(ridno)
        repository.set_name(repositoryName)
        urlList = []
#        for urlPath in repositoryUrls:
        url = Url()
        url.set_path(repositoryUrl)
        url.set_description('Sshy')
        url.set_type(UrlType.WEB_HOME)
        urlList.append(url)
        repository.set_url_list(urlList) 
        repository.set_change_time(chgtime)
        if reftag != None:
            repository.add_tag(reftag.get_handle())
        with DbTxn(_("Add Repository"), db) as trans:
            rhandle = db.add_repository(repository, trans)
        return repository

    def addSource(sourceName, attribs, reftag, repository):
        snote = addNote(attribs[3], NoteType.SOURCE)
        sidno = db.find_next_source_gramps_id() 
        source = Source()
        source.set_gramps_id(sidno)
        source.set_title(sourceName)
        source.set_author(attribs[0])
        source.set_publication_info(attribs[1])
        source.set_abbreviation(attribs[2])
        source.add_note(snote.get_handle())
        if reftag != None:
            source.add_tag(reftag.get_handle())
        repoRef = RepoRef()
        repoRef.set_reference_handle(repository.get_handle()) 
        source.add_repo_reference(repoRef)
        source.set_change_time(chgtime)
        with DbTxn(_("Add Source"), db) as trans:
            shandle = db.add_source(source, trans)
        return source

    def addNote(ntext, ntype):
        nidno = db.find_next_note_gramps_id() 
        note = Note(ntext)
        note.set_gramps_id(nidno)
        note.set_type(ntype)
        if reftag != None:        
            note.add_tag(reftag.get_handle())
        note.set_change_time(chgtime)
        with DbTxn(_("Add Note"), db) as trans:
            nhandle = db.add_note(note, trans)
            LOG.debug('Note added: ' + ntext  + ' ' + nhandle)
        return note    
      
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
  
    
    fdir = os.path.dirname(filename) 
 
    fh = logging.FileHandler(fdir + '\\sourceimport.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    LOG.addHandler(fh) 
                
    LOG.info("   fdir = " + fdir)
#    cout = fdir + "\\sresult.csv" 
    LOG.debug('ini file handling')
   
    config = configman.register_manager("importsources")
    config.register("options.refstring", "r")

    config.load()
    config.save()
    refstr = config.get('options.refstring')

    r_count = 0
    s_count = 0
    u_count = 0

    reftext = 'Referenssi'
    reftag = checkTagExistence(reftext)

    chgtime = int(time.time())
    LOG.info("   chgtime = " + str(chgtime)) 

    try:
        with open(filename, 'r', encoding="utf-8") as t_in:
            t_dialect = csv.Sniffer().sniff(t_in.read(2048))
            t_dialect.delimiter = ";"                
            t_in.seek(0)   
            t_reader = csv.reader(t_in, t_dialect)
            LOG.info('CSV input file delimiter is ' + t_dialect.delimiter)
            for row in t_reader:
                rectype = row[0]         # Record type = Gramps object id prefix character
#                otext = row[4].strip()
                if rectype == 'Arkisto':
                    repoName = row[1]
                    LOG.debug('New repository: ' + repoName)
                    r_count += 1
#                    repotype = row[1]         # repository type number
                    repoUrl = row[3]
                    LOG.debug("===========================> " + repoUrl)
                    repository = addRepository(repoName, repoUrl, reftag)   

                elif rectype == 'Lähde':
                    sourceName = row[1]
                    LOG.debug('Source row: ' + sourceName)
                    s_count += 1
                    sourceNote = 'Sshy: ' + row[4]
                    attribs = ("", "", "", sourceNote)  # Author, Publication-info, Abbreviation, Note-text
                    LOG.debug('New source: ' + sourceName)
                    addSource(sourceName, attribs, reftag, repository)

                else:
                    u_count += 1
                    LOG.debug('Unknown rectype: ' + rectype)
#                    raise GrampsImportError('Unknown record type ' + rectype) 
    
    except:
        exc = sys.exc_info()[0]
        LOG.error('*** Something went really wrong! ', exc )
        
        return ImportInfo({_('Results'): _('Something went really wrong  ')})
    
    results =  {  _('Results'): _('Input file handled.')
                , _('    Repositories   '): str(r_count)
                , _('    Sources        '): str(s_count) }
     
    LOG.info('Input file handled.')
    LOG.info('    Repositories   ' + str(r_count))
    LOG.info('    Sources        ' + str(s_count))
    
    db.enable_signals()
    db.request_rebuild()

    return ImportInfo(results)   

                       


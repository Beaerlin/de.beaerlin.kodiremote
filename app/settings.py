import os
import sys

import logging
import configparser as ConfigParser
log = logging.getLogger('settings')

class Settings(object):
    def __init__(self, path):
        
        path = os.path.abspath(path)
        self._touch(path)
        print('Settingsfile: %s'%path)
        log.debug('Settingsfile: %s'%path)
        self.path = path

    def _touch(self,path):
        
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        
        log.debug('Touching:%s'%path)
        open(path,'a').close()

    def get_sections(self):
        log.debug('Get Sections')
        parser = ConfigParser.RawConfigParser( )
        parser.read(self.path)
        sections = parser.sections()

        return sections

    def get_options(self, section):
        log.debug('Get Options: %s'%section)
        section = str(section)
        parser = ConfigParser.RawConfigParser( )
        parser.read(self.path)
        options = parser.options(section)
        return options

            
    def get(self, section, option):
        log.debug('Read: %s/%s'%(section,option))
        try:
            section = str(section)
            option = str(option)
            parser= ConfigParser.RawConfigParser( )
            parser.read(self.path)
            value = parser.get(section, option)
            log.debug('Got: %s'%value)
            return value
        except:
            log.debug('Got no Value:%s/%s'%(section,option))
            return None

    def set(self, section, option, value):
        log.debug('Write: %s/%s:%s'%(section,option,value))
        section = str(section)
        option = str(option)
        value = str(value)
        parser = ConfigParser.RawConfigParser( )
        if os.path.isfile( self.path ):
            parser.read( self.path )
        try:
            parser.add_section(section)
        except:
            pass
        parser.set(section, option, value)
        file_object = open(self.path, 'w')
        parser.write(file_object)
        file_object.close()
        
    def del_section(self,section):
        parser = ConfigParser.RawConfigParser( )
        if os.path.isfile( self.path ):
            parser.read( self.path )
        parser.remove_section(section)
        file_object = open(self.path, 'w')
        parser.write(file_object)
        file_object.close()


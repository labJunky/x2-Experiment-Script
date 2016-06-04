import socket
import os
import errno
import datetime

class Environs(dict):
    '''A dictionary containing usefuls paths'''            
   
    @staticmethod
    def factory(name=socket.gethostname()):
        '''Returns the required set of paths'''
        return {'192.168.104.162':Conveyor,
                 'conveyor':Conveyor,
                 '192.168.104.187':Control, 
                 'control':Control,
                 '192.168.104.186':Imaging,
                 'imaging':Imaging,
                 '192.168.100.132':Labjunky,
                 'labjunky':Labjunky,
                 '192.168.100.194':Zeus,
                 'Zeus':Zeus}[name]()
    
    def todaysScriptFolder(self):
        timestamp = datetime.datetime.now()
        yearFolder = os.path.join(self['Data'], timestamp.strftime("%Y"))
        monthFolder = os.path.join(yearFolder, timestamp.strftime("%y%m"))
        dayFolder = os.path.join(monthFolder, timestamp.strftime("%y%m%d"))
        scriptFolder = os.path.join(dayFolder, 'Scripts')
        inScripts = os.path.join(scriptFolder, 'Instrument Scripts')
        return {'Scripts':scriptFolder,'Instrument Scripts': inScripts}
            
class Conveyor(Environs):
    def __init__(self):
        self['Data']='E:\AtomChip Data'
        self['RemoteData'] = 'Z:\AtomChip Data'
        self['Scripts'] = 'E:\AtomChip Data\Scripts\ScriptRunFolder'
        self['Database'] = 'E:\AtomChip Data\Scripts\Settings Database\DeviceSettingsAtomChip.xml'

class Control(Environs):
    def __init__(self):
        self['Data'] ='D:\AtomChip Data'
        self['RemoteData'] = 'Z:\AtomChip Data'
        self['Scripts'] = 'D:\AtomChip Data\Scripts\ScriptRunFolder'
        self['Database'] = 'D:\AtomChip Data\Scripts\Settings Database\DeviceSettingsAtomChip.xml'
            
class Imaging(Environs):
    def __init__(self):
        self['Data'] ='D:\AtomChip Data'
        self['RemoteData'] = 'Z:\AtomChip Data'
        self['Scripts'] = 'D:\AtomChip Data\Scripts\ScriptRunFolder'
        self['Database'] = 'D:\AtomChip Data\Scripts\Settings Database\DeviceSettingsAtomChip.xml'
 
class Zeus(Environs):
    '''Paul's Labtop windows'''  
    def __init__(self):
        self['Data'] ='C:\Users\Administrator\Desktop\Crete\Data'
        self['RemoteData'] = 'Z:\AtomChip Data'
        self['Scripts'] = 'C:\Users\Administrator\Desktop\Crete\Data\Scripts\ScriptRunFolder'
        self['Database'] = 'C:\Users\Administrator\Desktop\Crete\Data\Scripts\Settings Database\DeviceSettingsAtomChip.xml'      
    
class Labjunky(Environs):
    '''Paul's labtop mac'''
    def __init__(self):
        self['Data'] ='/Users/paul/Data/University stuff/CQT/Data'
        self['RemoteData'] = '/Users/paul/Data/University stuff/CQT/Data'
        self['Scripts'] = '/Users/paul/Data/University stuff/CQT/Data/Scripts/ScriptRunFolder'
        self['Database'] = '/Users/paul/Data/University stuff/CQT/Data/DeviceSettingsAtomChip.xml'
        
class FolderCreator():
    '''FolderCreator handles creating data folders'''
    def createDataFolders(self, computer='local'):
        '''From the current Date, create the data folders on the local or remote computer'''
        paths = Environs.factory()
        if computer == 'local':
            folders = self._getPaths(paths['Data'])
        if computer == 'remote':
            folders = self._getPaths(paths['RemoteData'])
        [self._make_sure_path_exists(folder) for folder in folders]

    def _make_sure_path_exists(self,path):
        '''If the path doesn't exist, make it.'''
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
                
    def _getPaths(self, DataPath):
        '''Return a list of Paths'''
        timestamp = datetime.datetime.now()
        yearFolder = os.path.join(DataPath, timestamp.strftime("%Y"))
        monthFolder = os.path.join(yearFolder, timestamp.strftime("%y%m"))
        dayFolder = os.path.join(monthFolder, timestamp.strftime("%y%m%d"))
        scriptFolder = os.path.join(dayFolder, 'Scripts')
        inScripts = os.path.join(scriptFolder, 'Instrument Scripts')
        objFolder = os.path.join(dayFolder, 'Images','ObjectImages')
        refFolder = os.path.join(dayFolder, 'Images','RefImages')
        bgFolder = os.path.join(dayFolder, 'Images','BGImages')
        processedFolder = os.path.join(dayFolder, 'Images','ProcessedImages')
        matlabFolder = os.path.join(dayFolder, 'Images','MatlabProcessed')
        return [scriptFolder, inScripts, objFolder, refFolder, bgFolder, processedFolder, matlabFolder]

if __name__ == '__main__':
    fileSystem = Environs.factory()
    print fileSystem['Data']
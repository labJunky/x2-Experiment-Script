"Import the XML database"
import xml.etree.cElementTree as ET
import devices
reload(devices)
from devices import Devices
from databaseHelpers import XmlHelper
        
class Labels(list):
    def __init__(self, dbTree):
        super(Labels, self).__init__([label.text for label in dbTree.iterfind('.//label')])

class Stages(dict):
    def __init__(self, dbTree):
        dbHelper = XmlHelper()
        super(Stages, self).__init__({dbHelper.search(stage, 'name').text:dbHelper.search(stage, 'colour').text
                                     for stage in dbTree.iterfind('.//stage')})

class Database():
    """Represents the xml experiment Database"""
    def __init__(self, path='/Users/paul/Data/University stuff/CQT/Data/DeviceSettingsAtomChip.xml'):
        """Loads the database from the given path"""
        #Read Database into ElementTree
        dbTree = ET.ElementTree(file=path) 
        
        self.devices = Devices(dbTree)
        self.labels = Labels(dbTree)
        self.stages = Stages(dbTree)
    
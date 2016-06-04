from databaseHelpers import XmlHelper
import databaseExceptions
reload(databaseExceptions)
from databaseExceptions import UndefinedState, UndefinedLevel
import xml.etree.cElementTree as ET

#Use the Search function from the helper
dbHelp = XmlHelper()

class Devices(dict):
    """Represent in a dictionary the xml database with all the device settings and configurations"""
    def __init__(self, dbTree):
        """Load devices from the database into this dictionary object"""
        #Load Analog output devices
        for deviceXML in dbTree.iterfind('.//ao'):
            deviceElem = AoDevice(dbTree, deviceXML)
            self[deviceElem['name']] = deviceElem
        #Load Digital Devices
        for deviceXML in dbTree.iterfind('.//dio'):
            deviceElem = DioDevice(dbTree, deviceXML)
            self[deviceElem['name']] = deviceElem
        #Load Ethernet Analog Output Devices
        for deviceXML in dbTree.iterfind('.//ethernet'):
            deviceElem = EthernetDevice(dbTree, deviceXML)
            self[deviceElem['name']] = deviceElem
        #Load Rf Output Devices
        for deviceXML in dbTree.iterfind('.//rf'):
            deviceElem = RfDevice(dbTree, deviceXML)
            self[deviceElem['name']] = deviceElem
        self.names = self.keys()
    
    def __getattr__(self, name):
        return self.__getitem__(name)

    def __setattr__(self,name,value):
        self.__setitem__(name,value)
        
    def search(self, channel):
        #Return a dictionary containing information about the channel item
        #search('MOT coil') searches all devices and returns the channel
        try:
            return [self[key]['channels'][channel] for key in self.keys() if (key != 'names' and channel in self[key]['channels'])][0]
        except IndexError:
            return None
    
    def searchForDevice(self, channel):
        #Return a dictionary containing information about the device item
        #search('MOT coil') searches for the device with that channel
        try:
            return [self[key] for key in self.keys() if (key != 'names' and channel in self[key]['channels'])][0]
        except IndexError:
            return None
            
class Device(dict):
    """Represents, in a dictionary, a generic device's settings and configurations from the xml database"""
    def __init__(self, dbTree, deviceXML): 
        """Load a device from the database into a dictionary"""
        self._dbTree = dbTree
        self._loadDevice(deviceXML)
                
    def _loadDevice(self, deviceXml ):
        """Load from the database an analog_output device configuration"""
        self['name'] = deviceXml.attrib['name']
        self.name = self['name']
    
        self._deviceXPath = './/'+self['type']+'[@name='+"'"+self['name']+"'"+']/config'
                        
        #Load limits_inUse if there are any
        self._limitsXML = self._dbTree.find(self._deviceXPath + '/limits_inUse')
        self.limits = {}
        if self._limitsXML != None:
            self.limits = {child.tag:{'voltage_limit': dbHelp.search(child, 'voltage_limit').text,
                                'current_limit': dbHelp.search(child, 'current_limit').text} for child in self._limitsXML}
        else:
            self.limits['limit'] = None
            
        #Load channels into the device directory                       
        self.channels = self._loadChannelConfig()
    
        #Load information into device dictionary
        self['range'] = self._loadRange();
        self['triggering'] = self._loadTriggering()
        self['channels'] = self.channels
        self['limits'] = self.limits
            
    def _loadRange(self):
        """Load range information"""
        rangeXML  = self._dbTree.find(self._deviceXPath + '/range_inUse')
        range = {'units': rangeXML.attrib['units']}
        range['min'] = float(dbHelp.search(rangeXML, 'min').text)
        range['max'] = float(dbHelp.search(rangeXML, 'max').text)
        return range
    
    def _loadTriggering(self):
        #Load triggering information
        triggeringXML  = self._dbTree.find(self._deviceXPath + '/triggering_inUse')
        triggering = {}
        triggering['startTrigger'] = dbHelp.search(triggeringXML, 'start_trigger').text
        triggering['clock'] = dbHelp.search(triggeringXML, 'clock').text
        return triggering
            
    def _loadChannelConfig(self):
        """Load the channel configuration from the XML into the channels dictionary."""
        channelList = self._prepareChannelDetails(self.type)
        channels = {channel.channelName:channel for channel in channelList}
        return channels    
        
    def _prepareChannelDetails(self, channelType):
        self._channelXPath = self._deviceXPath + '/channels_inUse/name'
        #Extract the channel xml from the database
        channelInUseXml = [channelXml for channelXml in self._dbTree.iterfind(self._channelXPath)]
        channelConfigXml = [configXml for configXml in self._dbTree.iterfind(self._deviceXPath + '/channel_config')]
        channelXml = [configuration for configuration in zip(*[channelInUseXml,channelConfigXml])]
        #Load, from the channel Xml, the channel details
        #channelInUseXml and channelConfigXml should be in the same order for the below
        #list operation. But this is not always so. 
        #This means I have ignored the config[0] item.
        #This means that all channels are labeled 'unrestricted'
        #even though this may be incorrect.
        
        #but we can configure the channel then search for the channel and pull out the 
        #correct 'restricted'/'unrestricted' label!
        return [Channel.factory(channelType,config[0], config[1]) for config in channelXml]
        
        
class AoDevice(Device):
    """An Analog Output device. It loads the AO specific information on 
    top of the generic device configuration"""
    
    def __init__(self, dbTree, deviceXML):
        """Load the generic Device settings, and then load the AO specific settings"""
        self.type = 'ao'
        self['type'] = 'ao'
        Device.__init__(self, dbTree, deviceXML)

    
class DioDevice(Device):
    """An Digital IO device. It loads the DIO specific information on 
    top of the generic device configuration"""
    
    def __init__(self, dbTree, deviceXML):
        """Load the generic Device settings, and then load the AO specific settings"""
        self.type = 'dio'
        self['type'] = 'dio'
        Device.__init__(self, dbTree, deviceXML)
        
    def _loadRange(self):
        """No range info for DIO devices"""
        pass
    
class EthernetDevice(Device):
    """An ethernet analog output device. This loads the ethernet specific information on 
    top of the generic device configuration"""
    
    def __init__(self, dbTree, deviceXML):
        """Load the generic Device settings, and then load the ethernet AO specific settings"""
        self.type = 'ethernet'
        self['type'] = 'ethernet'
        Device.__init__(self, dbTree, deviceXML)
        
    def _loadTriggering(self):
        """Load the generic Device settings, and then load the ethernet AO specific triggering settings"""
        #Load triggering information
        triggeringXML  = self._dbTree.find(self._deviceXPath + '/triggering_inUse')
        triggering = {child.tag:{'startTrigger': dbHelp.search(child, 'start_trigger').text,
                                'clock': dbHelp.search(child, 'clock').text} for child in triggeringXML}
        return triggering
        
    def _loadRange(self):
        """Load range information for Ethernet supplies"""
        rangeXML  = self._dbTree.find(self._deviceXPath + '/range_inUse')
        range = {child.tag:{'current': dbHelp.search(child, 'current').text,
                                'voltage': dbHelp.search(child, 'voltage').text} for child in rangeXML}
        range['units'] = rangeXML.attrib['units']
        return range
        
class RfDevice(Device):
    """An Rf output device. This loads the rf specific information on 
    top of the generic device configuration"""
    
    def __init__(self, dbTree, deviceXML):
        """Load the generic Device settings, and then load the rf specific settings"""
        self.type = 'rf'
        self['type'] = 'rf'
        Device.__init__(self, dbTree, deviceXML)  
    
class Channel(dict):
    def __init__(self, channelXml, configXml):
        """Load channel configuration"""
        self._loadChannelInUse(configXml)
        self._loadChannelConfig(configXml)
        
    @staticmethod
    def factory(channelType, channelXml, configXml):
        channelSelector = {'ao': Channel, 'dio': DioChannel, 'ethernet': Channel, 'rf': RfChannel}
        return channelSelector[channelType](channelXml, configXml)
        
    def calibrate(self, value):
        """Calibrate the value or state"""
        #Value could be a string refering to a state
        if isinstance(value, str): 
            #search states for the string, and calibrate
            stateValue = self._getState(value)
            return {'value':stateValue*self['calibration']['gradient']+self['calibration']['offset']}
        else:
            try:
                return {'value':value*self['calibration']['gradient']+self['calibration']['offset']}
            except TypeError:
                return {'value': None}
                
    def calibratedSafeState(self):
        return self.calibrate(self['safe_state'])
        
    def getAmplitude(self, value):
        """Get the value or state value"""
        #Value could be a string refering to a state
        if isinstance(value, str): 
            #search states for the string, and calibrate
            stateValue = self._getState(value)
            return stateValue
        else:
            try:
                return value
            except TypeError:
                return {'value': None}
    
    def _getState(self, value):
        """For the given string value find the state defined within the channel"""
        stateValue =  next((self['states'][state] for state in self['states'].keys() if state == value), None)
        if stateValue == None: 
            #The state was not found
            raise UndefinedState(value)
        else: 
            #The state as found
            return stateValue
        
    def _loadChannelInUse(self, configXml ):
        """Load the channels_inUse data from the xml element."""
        self.channelName = dbHelp.search(configXml, 'mappedTo').text
        super(Channel, self).__init__({'channel' : configXml.attrib['name'], 'type' : 'unrestricted' })
        
    def _loadChannelConfig(self, configXML):
        """Load the channel configuration from the XML into the channels dictionary."""
        try:
            states = {child.tag:float(child.text) for child in dbHelp.search(configXML, 'states')}
        except ValueError:
            states = {child.tag:child.text for child in dbHelp.search(configXML, 'states')}
        for child in dbHelp.search(configXML, 'calibration'):
            try:
                calibration = {'gradient' : float( dbHelp.search(configXML,'gradient').text ),
                            'offset' : float( dbHelp.search(configXML, 'offset').text ) }
            except ValueError:
                #If the text is not a number, set a default calibration
                calibration = {'gradient' : 1 ,'offset' : 0 }
        # Find the channel in the dictionary and add the states and calibration
        self['states'] = states
        self['calibration'] = calibration
        self['safe_state'] = dbHelp.search(configXML, 'safe_state').text
        self['units'] = dbHelp.search(configXML, 'units').text
        
class DioChannel(Channel):
    
    def calibrate(self, value):
        """Calibrate the value, state, or level"""
        #Value could be a number, or string refering to a state or level
        #Check if its a state
        if isinstance(value, str): 
            #search states for the string
            try:
                stateValue = self._getState(value)
                return {'value':self._getLevel(stateValue)}
            except UndefinedState:
                #It's not a state, but maybe it's a level
                level = self._getLevel(value)
                return {'value':level*self['calibration']['gradient']+self['calibration']['offset']}
        else:
            return {'value':value*self['calibration']['gradient']+self['calibration']['offset']}
    
    def getAmplitude(self, value):
        """Calibrate the value, state, or level"""
        #Value could be a number, or string refering to a state or level
        #Check if its a state
        if isinstance(value, str): 
            #search states for the string
            try:
                stateValue = self._getState(value)
                return self._getLevel(stateValue)
            except UndefinedState:
                #It's not a state, but maybe it's a level
                level = self._getLevel(value)
                return level
        else:
            return value
            
    def _getLevel(self, value):
        """For the given string value find the digital level defined within the channel"""
        levelValue =  next((self['digital_config']['levels'][value] 
                                for level in self['digital_config']['levels'].keys() if level == value), None)
        if levelValue == None: 
            #The level was not found
            raise UndefinedLevel(value)
        else:
            #The level was found
            return levelValue
    
    def _loadChannelConfig(self, configXML):
        """Load the channel configuration from the XML into the channels dictionary."""
        #Load Generic configuration
        Channel._loadChannelConfig(self, configXML)
        #Add DIO specific configuration
        self['digital_config'] = self._loadDigitalConfig(configXML)
    
    def _loadDigitalConfig(self, configXML):
        """Load the Digital configuration"""
        digitalConfig = {}
        _dioConfig = configXML.find('./digital_config')
        digitalConfig['type'] = dbHelp.search(_dioConfig, 'type').text
        #print dbHelp.search(_dioConfig, 'type').text
        digitalConfig['levels'] = {'high':float(dbHelp.search(_dioConfig, 'high').text), 
                                        'low':float(dbHelp.search(_dioConfig, 'low').text)}
        if digitalConfig['type'] == 'pulse':
            digitalConfig['width'] = float(dbHelp.search(_dioConfig, 'width').text)
            digitalConfig['delay'] = float(dbHelp.search(_dioConfig, 'delay').text)
        else:
            digitalConfig['width'] = 0
            digitalConfig['delay'] = 0
        return digitalConfig
    
    
class RfChannel(Channel):
    
    def calibrate(self, value):
        """Calibrate the rf channel's value. Return a dictionary of Frequency, Amplitude and phase."""
        if isinstance(value, str): 
            #search states for the string
            stateValue = self._getState(value)
            return {'value':{'amplitude':stateValue['amplitude']*self['calibration']['amplitude']['gradient']+self['calibration']['amplitude']['offset'],
                            'frequency':stateValue['frequency']*self['calibration']['frequency']['gradient']+self['calibration']['frequency']['offset'],
                            'phase':stateValue['phase']*self['calibration']['phase']['gradient']+self['calibration']['phase']['offset']}}
                     
        elif isinstance(value, dict):
            #Maybe value is a dictionary? With keys amplitude, frequency, and phase.
            return {'value':{'amplitude':value['amplitude']*self['calibration']['amplitude']['gradient']+self['calibration']['amplitude']['offset'],
                            'frequency':value['frequency']*self['calibration']['frequency']['gradient']+self['calibration']['frequency']['offset'],
                            'phase':value['phase']*self['calibration']['phase']['gradient']+self['calibration']['phase']['offset']}}
        elif isinstance(value, tuple):
            #Maybe value is a tuple (amplitude, frequency, phase)?
            return {'value':{'amplitude':value[0]*self['calibration']['amplitude']['gradient']+self['calibration']['amplitude']['offset'],
                            'frequency':value[1]*self['calibration']['frequency']['gradient']+self['calibration']['frequency']['offset'],
                            'phase':value[2]*self['calibration']['phase']['gradient']+self['calibration']['phase']['offset']}}
        elif isinstance(value, list):
            #Maybe value is a list [amplitude, frequency, phase]?
            return {'value':{'amplitude':value[0]*self['calibration']['amplitude']['gradient']+self['calibration']['amplitude']['offset'],
                            'frequency':value[1]*self['calibration']['frequency']['gradient']+self['calibration']['frequency']['offset'],
                            'phase':value[2]*self['calibration']['phase']['gradient']+self['calibration']['phase']['offset']}}
        else:
            #Maybe the value is just the amplitude? So return the calibrated amplitude
            return {'value':{'amplitude':value*self['calibration']['amplitude']['gradient']+self['calibration']['amplitude']['offset']}}  
   
    def getAmplitude(self, value):
        """Get the rf channel's value. Return the Amplitude"""
        if isinstance(value, str): 
            #search states for the string
            stateValue = self._getState(value)
            return stateValue['amplitude']
                     
        elif isinstance(value, dict):
            #Maybe value is a dictionary? With keys amplitude, frequency, and phase.
            return value['amplitude']
                        
        elif isinstance(value, tuple):
            #Maybe value is a tuple (amplitude, frequency, phase)?
            return value[0]
            
        elif isinstance(value, list):
            #Maybe value is a list [amplitude, frequency, phase]?
            return value[0]
            
        else:
            #Maybe the value is just the amplitude? So return the calibrated amplitude
            return value 
   
    def _loadChannelConfig(self, configXML):
        """Load the rf channel configuration from the XML into the channels dictionary."""
        states = {}
        for state in dbHelp.search(configXML, 'states'):
            states[state.tag] = {'frequency':float(dbHelp.search(state, 'frequency').text),
                                 'amplitude': float(dbHelp.search(state, 'amplitude').text),
                                 'phase': float(dbHelp.search(state, 'phase').text)}
        calibrationXML = dbHelp.search(configXML, 'calibration')
        try:
            freq = dbHelp.search(calibrationXML,'frequency')
            amp = dbHelp.search(calibrationXML,'amplitude')
            phase = dbHelp.search(calibrationXML,'phase')
            calibration = {'frequency' : {'gradient' :float(dbHelp.search(freq,'gradient').text),
                                            'offset' : float(dbHelp.search(freq, 'offset').text ) },
                            'amplitude' : {'gradient' :float(dbHelp.search(amp,'gradient').text),
                                            'offset' : float(dbHelp.search(amp, 'offset').text ) },
                            'phase' : {'gradient' :float(dbHelp.search(phase,'gradient').text),
                                            'offset' : float(dbHelp.search(phase, 'offset').text ) } }
        except ValueError:
            #If the text is not a number, set a default calibration
            calibration = {'frequency': {'gradient' : 1 ,'offset' : 0 },
                            'amplitude': {'gradient' : 1 ,'offset' : 0 },
                            'phase': {'gradient' : 1 ,'offset' : 0 } }
        # Find the channel in the dictionary and add the states and calibration
        self['states'] = states
        self['calibration'] = calibration
        self['safe_state'] = dbHelp.search(configXML, 'safe_state').text
        unitsXML = dbHelp.search(configXML, 'units')
        self['units'] = {'frequency': dbHelp.search(unitsXML, 'frequency').text,
                         'amplitude': dbHelp.search(unitsXML, 'amplitude').text,
                         'phase': dbHelp.search(unitsXML, 'phase').text}    
        
    
if __name__ == '__main__':
    import xml.etree.cElementTree as ET
    #File Path to the database
    dbPath = '/Users/paul/Data/University stuff/CQT/Data/MOT Test Setup/140405/DeviceSettingsAtomChip.xml'
    #Read Database into ElementTree
    dbTree = ET.ElementTree(file=dbPath) 
    devices = Devices(dbTree) 
    print devices.names
    
    chanPath = ".//ao[@name='Ao8a']/config/channels_inUse/name"
    chanconfigPath = ".//ao[@name='Ao8a']/config/channel_config"
    channelXml = dbTree.find(chanPath)
    configXml = dbTree.find(chanconfigPath)
    channel = Channel.factory('ao', channelXml, configXml)
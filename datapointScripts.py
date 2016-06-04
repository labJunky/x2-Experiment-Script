"Load a Datapoint script into python"
#ToDo update to read playfile events.


from databaseHelpers import XmlHelper
xmlHelper = XmlHelper()

class EventList(list):
    """Represent the Events in DataPoint Script"""    
    def __init__(self, scriptTree = None):
        if scriptTree == None:
            pass
        elif isinstance(scriptTree, list):
            super(EventList, self).__init__(scriptTree)
        else:
            self._loadList(scriptTree)
            
    def _loadList(self, scriptTree):
        super(EventList, self).__init__([Event.factory(eventXml) for eventXml in scriptTree.iterfind('.//event')]+
                                        [Event.factory(eventXml) for eventXml in scriptTree.iterfind('.//delay_label')])
        self.info = scriptTree.find('./info/script_comment').text

    def search(self, item):
        """Returns a list of matching items or events. Items can be a string 'comment' returning a list of comments,
        or a tuple ('name', 'MOT coil') which returns events who's name matches 'MOT coil'."""
        if type(item) == tuple:
            return [event for event in self if event[item[0]] == item[1]]
        else:
            return [event[item] for event in self]
    
        
class Event(dict):
    def __init__(self, eventXml=None):
        """ Initialise dictionary with None values"""
        if eventXml == None:
            self['time'] = None
            self['time_difference'] = None
            self['name'] = None
            self['newValue'] = None
            self['stage'] = None
            self['comment'] = None
            self['action'] = None
            self['calibratedValue'] = None
            self['device'] = None
            self['amplitude']=None
        else:
            self.loadEvent(eventXml)
        
    @staticmethod
    def factory(eventXml):
        eventType = {'changeValue': Event, 'delay': Delay, 'pulse': Pulse, 'rf': Rf, 'rampUp': Ramp, 'rampDown': Ramp, 'rfRamp':RfRamp}
        return eventType[xmlHelper.search(eventXml, 'action').text](eventXml)
    
    @staticmethod
    def createEventFromDict(eventData):
        event = Event()
        event['time'] = eventData['time']
        event['time_difference'] = eventData['time_difference']
        event['name'] = eventData['name']
        event['newValue'] = eventData['newValue']
        event['stage'] = eventData['stage']
        event['comment'] = eventData['comment']
        event['action'] = eventData['action']
        event['calibratedValue'] = eventData['calibratedValue']
        event['device'] = None
        event['amplitude']=None
        return event
        
    def loadEvent(self, eventXml):
        """Initialise by loading data from xml stored values"""
        self['time'] = float(xmlHelper.search(eventXml, 'time').text)
        self['time_difference'] = float(xmlHelper.search(eventXml, 'time_difference').text)
        self._loadChannel(eventXml)
        self._loadValue(eventXml)
        self['stage'] = xmlHelper.search(eventXml, 'stage').text
        self['comment'] = xmlHelper.search(eventXml, 'comment').text
        self._loadAction(eventXml)
        self['calibratedValue'] = None
        self['amplitude']=None
        self._convertFloatValue()
        self['device'] = None

    def _loadChannel(self, eventXml):
        self['name'] =  xmlHelper.search(eventXml, 'channel_name').text
        
    def _loadValue(self, eventXml):
        self['newValue'] = xmlHelper.search(eventXml, 'newValue').text
    
    def _loadAction(self, eventXml):
        self['action'] = xmlHelper.search(eventXml, 'action').text
        
    def _convertFloatValue(self):
        """If 'newValue' is a number (like '8'), convert it to a float.
            If it's a string (like 'on'), do nothing"""
        try:
            self['newValue'] = float(self['newValue'])
        except (ValueError, TypeError):
            pass
        
    def calibrate(self, channel):
        self['calibratedValue'] = channel.calibrate(self['newValue'])
        
    def unPack(self, channel=None):
        """For Pulse and Ramp etc, add the additional events to event list"""
        return []
        
    def delayEvent(self, channel=None):
        pass
        
    def getAmplitude(self, channel):
        self['amplitude'] = channel.getAmplitude(self['newValue'])
        
    def __hash__(self):
        return hash(('time', self['time'], 'name', self['name']))
    
    def __eq__(self, other):
        return self['time']==other['time'] and self['name']==other['name']
        
class Delay(Event):
    def _loadChannel(self, eventXml):
         self['name'] = xmlHelper.search(eventXml, 'label').text
         
    def _loadValue(self, eventXml):
        self['newValue'] = None
        
    def _convertFloatValue(self):
        pass
        
    def calibrate(self, channel):
        pass
    
class Pulse(Event):
    @staticmethod
    def createEventFromDict(eventData):
        event = Pulse()
        event['time'] = eventData['time']
        event['time_difference'] = eventData['time_difference']
        event['name'] = eventData['name']
        event['newValue'] = eventData['newValue']
        event['stage'] = eventData['stage']
        event['comment'] = eventData['comment']
        event['action'] = eventData['action']
        event['calibratedValue'] = eventData['calibratedValue']
        event['device'] = None
        event['amplitude']=None
        return event
        
    def unPack(self, channel=None):
        if channel != None and channel['digital_config']['type'] != 'changeValue':
            newTime = self['time']+channel['digital_config']['width']
            eventData = {'time':newTime, 
                         'time_difference':channel['digital_config']['width'],
                         'name':self['name'], 'newValue':'low', 'stage':self['stage'],
                         'comment':self['comment'], 'action':self['action'],
                         'calibratedValue':{'value':channel['digital_config']['levels']['low']} }
            return EventList([Event.createEventFromDict(eventData)])
        else:
            return []
    
    def delayEvent(self, channel=None):
        if channel != None:
            if channel['digital_config']['delay'] != 0:
                self['time'] = self['time'] - channel['digital_config']['delay']


class Rf(Event):
    def _loadAction(self, eventXml):
        self['additional_data'] = {'frequency' : float(xmlHelper.search(eventXml, 'frequency').text)/1000, 
                                   'phase' : float(xmlHelper.search(eventXml, 'phase').text)}
        self['action'] = xmlHelper.search(eventXml, 'action').text
    
    def calibrate(self, channel):
        if isinstance(self['newValue'], str):
            # its a state
            self['calibratedValue'] = channel.calibrate(self['newValue'])
        else:
            # its a value
            self['calibratedValue'] = channel.calibrate([self['newValue'],self['additional_data']['frequency'],self['additional_data']['phase']])


class Ramp(Event):
    """Ramp value up or down."""
    def _loadValue(self, eventXml):
        self['newValue'] = {'startValue': xmlHelper.search(eventXml, 'startValue').text,
                            'stopValue': xmlHelper.search(eventXml, 'stopValue').text }
                            
    def _convertFloatValue(self):
        try:
            self['newValue']['startValue'] = float(self['newValue']['startValue'])
        except (ValueError, TypeError):
            pass
        try:
            self['newValue']['stopValue'] = float(self['newValue']['stopValue'])
        except (ValueError, TypeError):
            pass
            
    def _loadAction(self, eventXml):
        self['additional_data'] = {'rampTime': float(xmlHelper.search(eventXml, 'ramp_time').text),
                                   'timeStep': float(xmlHelper.search(eventXml, 'time_step').text), 
                                   'valueStep': float(xmlHelper.search(eventXml, 'value_step').text) }
        self['action'] = xmlHelper.search(eventXml, 'action').text 
        
    def calibrate(self, channel):
        self['calibratedValue'] = {'startValue': channel.calibrate(self['newValue']['startValue']),
                                   'stopValue': channel.calibrate(self['newValue']['stopValue']),
                                   'valueStep': channel.calibrate(self['additional_data']['valueStep']) }
        #If the startValue > stopValue, valueStep should be negative. This forces it negative.
        if self['calibratedValue']['startValue']['value'] > self['calibratedValue']['stopValue']['value']:
            self['calibratedValue']['valueStep']['value']  = -abs(self['calibratedValue']['valueStep']['value'])
        
    def getAmplitude(self, channel):
        if isinstance(self['newValue'],dict):
            self['amplitude'] = channel.getAmplitude(self['newValue']['startValue'])
        else:
            self['amplitude'] = channel.getAmplitude(self['newValue'])
                
    def unPack(self, channel=None):
        steps = abs( int( (self['calibratedValue']['startValue']['value'] \
                        - self['calibratedValue']['stopValue']['value']) \
                            / self['calibratedValue']['valueStep']['value'] ) )
        self.newTime = self['time']
        self.rampValue = self['calibratedValue']['startValue']['value']
        self.newAmp = channel.getAmplitude(self['newValue']['startValue'])
        events = [self._createRampEvent() for i in range(steps)]
        return EventList(events)

    def _createRampEvent(self):
            self.newTime += self['additional_data']['timeStep']
            self.rampValue += self['calibratedValue']['valueStep']['value']
            self.newAmp +=  self['additional_data']['valueStep']
            eventData = {'time':self.newTime, 
                         'time_difference':self['additional_data']['timeStep'],
                         'name':self['name'], 'newValue':self.newAmp, 'stage':self['stage'],
                         'comment':self['comment'], 'action':self['action'],
                         'calibratedValue':{'value':self.rampValue} }
            return Event.createEventFromDict(eventData)
        
class RfRamp(Rf):
    """Rf ramps can ramp all three values, amplitude, freq, and phase,
    at the same time. I.e. there is a start and stop value for each,
    and a number of steps."""
        
    def _loadValue(self, eventXml):
        self['newValue'] = {'startValue': xmlHelper.search(eventXml, 'startValue').text,
                            'stopValue': xmlHelper.search(eventXml, 'stopValue').text }
                            
    def _convertFloatValue(self):
        """Check is startValue and stopValues are strings or numbers, and converts them 
        accordingly."""
        try:
            self['newValue']['startValue'] = float(self['newValue']['startValue'])
        except (ValueError, TypeError):
            pass
        try:
            self['newValue']['stopValue'] = float(self['newValue']['stopValue'])
        except (ValueError, TypeError):
            pass
            
    def _loadAction(self, eventXml):
        self['additional_data'] = {'rampTime':float(xmlHelper.search(eventXml, 'ramp_time').text),
                                   'numberOfSteps':int(xmlHelper.search(eventXml, 'number_of_steps').text),
                                   'start':{'frequency':float(xmlHelper.search(xmlHelper.search(eventXml, 'start'), 'frequency').text),
                                            'phase':float(xmlHelper.search(xmlHelper.search(eventXml, 'start'), 'phase').text)},
                                   'stop':{'frequency':float(xmlHelper.search(xmlHelper.search(eventXml, 'stop'), 'frequency').text),
                                            'phase':float(xmlHelper.search(xmlHelper.search(eventXml, 'stop'), 'phase').text)}
                                    }
        self['action'] = xmlHelper.search(eventXml, 'action').text
        
    def calibrate(self, channel):
        """Calibrate the rf ramp. Start and Stop values for frequency phase and amplitude.
        The values could be a state."""
        startValue = {'amplitude':self['newValue']['startValue'],
                      'frequency':self['additional_data']['start']['frequency'],
                      'phase':self['additional_data']['start']['phase']}
        stopValue = {'amplitude':self['newValue']['stopValue'],
                     'frequency':self['additional_data']['stop']['frequency'],
                     'phase':self['additional_data']['stop']['phase']}
        #The StartValue could be a state, i.e. a string
        if isinstance(self['newValue']['startValue'], str):
            self['calibratedValue'] = {'startValue': channel.calibrate(self['newValue']['startValue'])}
        else:
            self['calibratedValue'] = {'startValue': channel.calibrate(startValue)}
        #The stopValue could be a state, i.e a string
        if isinstance(self['newValue']['stopValue'], str):
            self['calibratedValue']['stopValue'] = channel.calibrate(self['newValue']['stopValue'])
        else:
            self['calibratedValue']['stopValue'] = channel.calibrate(stopValue)
                                   
    def unPack(self, channel=None):
        self.steps = self['additional_data']['numberOfSteps']
        self.timeStep = self['additional_data']['rampTime'] / self.steps
        self.newTime = self['time']
        self.rampAmplitude = self['calibratedValue']['startValue']['value']['amplitude']
        self.rampFrequency = self['calibratedValue']['startValue']['value']['frequency']
        self.rampPhase = self['calibratedValue']['startValue']['value']['phase']
        self.amplitudeStep = (self['calibratedValue']['stopValue']['value']['amplitude'] - self['calibratedValue']['startValue']['value']['amplitude']) \
                                / self.steps
        self.frequencyStep = (self['calibratedValue']['stopValue']['value']['frequency'] - self['calibratedValue']['startValue']['value']['frequency']) \
                                / self.steps
        self.phaseStep = (self['calibratedValue']['stopValue']['value']['phase'] - self['calibratedValue']['startValue']['value']['phase']) \
                                / self.steps
        events = [self._createRampEvent() for i in range(self.steps)]
        return EventList(events)

    def _createRampEvent(self):
        """Make all events in the ramp"""
        #New Values
        self.newTime += self.timeStep
        self.rampAmplitude += self.amplitudeStep
        self.rampFrequency += self.frequencyStep
        self.rampPhase += self.phaseStep
        #Create Event
        eventData = {'time':self.newTime, 
                        'time_difference':self.timeStep,
                        'name':self['name'], 'newValue':None, 'stage':self['stage'],
                        'comment':self['comment'], 'action':self['action'],
                        'calibratedValue':{'value':{'amplitude':self.rampAmplitude, 'frequency':self.rampFrequency, 'phase':self.rampPhase}} }
        return Event.createEventFromDict(eventData)

if __name__ == '__main__':
    import xml.etree.cElementTree as ET
    #Load a script
    #scriptPath = '/Users/paul/Data/University stuff/CQT/Data/AIN Chip Data/140122 ChipMOT Loading/140122/Scripts/140122_1107_22 MOT U-wire_Dp.xml'
    scriptPath = '/Users/paul/Data/University stuff/CQT/Data/ScriptRunFolder/testingPythonRfRamp.xml'
    #Read Database into ElementTree
    scriptTree = ET.ElementTree(file=scriptPath) 
    eventList = EventList(scriptTree)
    print eventList.info
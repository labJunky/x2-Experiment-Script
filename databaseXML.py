"Import the XML database and compile a script"
import time
st = time.time()
   

import xml.etree.cElementTree as ET
import itertools
import devices
reload(devices)
from devices import Devices
from databaseHelpers import XmlHelper
import warnings
import datapointScripts
reload(datapointScripts)
from datapointScripts import EventList, Pulse, Ramp
        
#File Path to the database
#dbPath = '/Users/paul/Data/University stuff/CQT/Data/DeviceSettingsAtomChip.xml'
dbPath = '/Users/paul/Data/University stuff/CQT/Data/Settings Database/DeviceSettingsAtomChip.xml'
#Read Database into ElementTree
dbTree = ET.ElementTree(file=dbPath) 

class Labels(list):
    def __init__(self, dbTree):
        super(Labels, self).__init__([label.text for label in dbTree.iterfind('.//label')])

class Stages(dict):
    def __init__(self, dbTree):
        dbHelper = XmlHelper()
        super(Stages, self).__init__({dbHelper.search(stage, 'name').text:dbHelper.search(stage, 'colour').text
                                     for stage in dbTree.iterfind('.//stage')})
devices = Devices(dbTree)
labels = Labels(dbTree)
stages = Stages(dbTree)

databaseLoadTime = time.time() - st

#Load a script
#scriptPath = '/Users/paul/Data/University stuff/CQT/Data/AIN Chip Data/140122 ChipMOT Loading/140122/Scripts/140122_1107_22 MOT U-wire_Dp.xml'
#scriptPath = '/Users/paul/Data/University stuff/CQT/Data/RampFailScript.xml'
scriptPath = '/Users/paul/Data/University stuff/CQT/Data/ScriptRunFolder/06U-MT-v1.xml'
#Read Database into ElementTree
scriptTree = ET.ElementTree(file=scriptPath) 
eventList = EventList(scriptTree)
print eventList.info

#Get the values for events which are not delays
#scriptValues = {event['name']:event['newValue'] for event in eventList if event['action'] != 'delay'}
#Making a dictionary will overwrite values. A list of tuples may be better
scriptValues = [[event['name'],event['time'],event['newValue']] for event in eventList if event['action'] != 'delay']
         
def calibrateEvent(event):
    channel = devices.search(event['name'])
    if channel != None:
        event.calibrate(channel)

#Calibrate the values for which the channel exists in the database                                                                       if devices.search(event['name']) != None}
[calibrateEvent(event) for event in eventList]

#Channel doesn't exit
noChannelList = [event['name'] for event in eventList if devices.search(event['name']) == None and event['action'] != 'delay']
[warnings.warn('The channel ' + '"'+channel_name+'"' +' is not defined within the database.') for channel_name in noChannelList]
    
#Compiler steps:
#Get the channels and sort into their respective devices (?)
#Add the ramp data
[eventList.extend(event.unPack(devices.search(event['name']))) for event in eventList]
eventList.sort(key = lambda event: (event['time'], -event['time_difference']))

#Add additional pulse events due to the triggering
#Get the device trigger for each event
#add a trigger pulse to start device or clock pulse for each sample to output.
startedAlreadyList = []
def createTimingPulses(event):
    device = devices.searchForDevice(event['name'])
    #Remember the device name for later use
    event['device'] = device['name']
    #We only need to provide one start trigger per device
    #If the device has no external clock. 
    #Create a list to remember which devices has already been provided a trigger
    if device['triggering']['clock'] != 'internal' and device['triggering']['clock'] != 'none':
        #The device uses an external clock
        channel = devices.search(device['triggering']['clock'])
        if channel != None:
            #The channel exists - create clock tick
            eventData = {'time':event['time'], 
                    'time_difference':event['time_difference'],
                    'name':device['triggering']['clock'], 'newValue':'high', 'stage':event['stage'],
                    'comment':event['comment'], 'action':'pulse',
                    'calibratedValue':None }
            pulse = Pulse.createEventFromDict(eventData)
            pulse.calibrate(channel)
            eventList.extend([pulse])
            eventList.extend(pulse.unPack(devices.search(pulse['name'])))
    elif device['triggering']['startTrigger'] != 'internal':
        #The device uses a start trigger
        channel = devices.search(device['triggering']['startTrigger'])
        if channel != None and device['name'] not in startedAlreadyList:
            #The channel exists, and the device needs a start trigger - create device start trigger
            #Add device name to the list of already started devices, so we don't provide 
            #more than one start trigger per device.
            startedAlreadyList.extend([device['name']])
            eventData = {'time':event['time'], 
                    'time_difference':event['time_difference'],
                    'name':device['triggering']['startTrigger'], 'newValue':'high', 'stage':event['stage'],
                    'comment':event['comment'], 'action':'pulse',
                    'calibratedValue':None }
            pulse = Pulse.createEventFromDict(eventData)
            pulse.calibrate(channel)
            eventList.extend([pulse])
            eventList.extend(pulse.unPack(devices.search(pulse['name'])))
            
[createTimingPulses(event) for event in eventList if event['action'] != 'delay' and event['name'] not in noChannelList]

#Remove Duplicates and order
eventList = EventList(list(set(eventList)))

#Account for delays in trigger pulses
#i.e. some pulses are delayed to syncronize the device responce times
[event.delayEvent(devices.search(event['name'])) for event in eventList \
        if event['action'] != 'delay' and event['name'] not in noChannelList]
eventList.sort(key=lambda event: (event['time'], -event['time_difference'], event['name']))

#Adjust for the new time differences
#Function to get the current and next event in a loop
def pairwise(iterable):
    event, nextEvent = itertools.tee(iterable)
    next(nextEvent, None)
    return itertools.izip(event, nextEvent)
    
#Loop over pairs and adjust time delays 
#If the first event has been delayed to a negative time, 
#lets set it to time zero and add the difference  
if eventList[0] < 0:
    difference = eventList[1]['time'] - eventList[0]['time']
    eventList[0]['time'] = 0;
    eventList[1]['time'] += difference 
for event, nextEvent in pairwise(eventList):
    nextEvent['time_difference'] = nextEvent['time'] - event['time']

#Seperate eventlists per device
deviceNames=set([event['device'] for event in eventList if event['action'] != 'delay' and event['name'] not in noChannelList])
deviceEventList = {device:EventList(eventList.search(('device', device))) for device in deviceNames}

#Manipulate the data into the require format

#For first time, search all channels for that time and fill in data
#set the other channels to there defaults.
def concurrency(event, device):
    concurrentEvents = [concurrentEvents for concurrentEvents in deviceEventList[device].search(('time',event['time']))]
    tmplist = []
    for concurrentEvent in concurrentEvents:
        if isinstance(concurrentEvent, Ramp):
            value = concurrentEvent['calibratedValue']['startValue']['value']
        else:
            value = concurrentEvent['calibratedValue']['value']
        tmplist.extend([{concurrentEvent['name']:value}])
    return {event['time']:tmplist}

def timeDataList(device):
    timeData = {}
    previousValues = []
    #Per device get the active channels (no duplicates)
    activeChannels = set([e['name'] for e in deviceEventList[device]])
    #Create a dictionary of { Time:[{channel:value] }
    for i, e in enumerate(deviceEventList[device]):
        clist = concurrency(e, device)
        #Times
        key = clist.keys()[0]
        #[{Channel:Values}]
        value = clist.values()[0]
        channels = [channel.keys()[0] for channel in value]
        if i == 0:
           newValues = [{channel:devices.search(channel).calibratedSafeState()['value']} \
                for channel in activeChannels if channel not in channels]
        else:
            newValues = [{channel:next((elem[channel] for elem in previousValues if elem.keys()[0] == channel), None) }\
                for channel in activeChannels if channel not in channels]
        #{ Time:[{channel:value] } 
        value.extend(newValues)
        previousValues = value
        timeData[key] = value 
        allChannels = [channel.keys()[0] for channel in value]
        timeData['channel_map'] = {channel:devices.search(channel)['channel'] for channel in allChannels}
    return timeData

deviceData = {device:timeDataList(device) for device in deviceNames}

#Compile finished... Do something, like run the devices.

##Print the script
#for event in eventList:
#    if devices.search(event['name']) != None or event['action'] == 'delay':
#        print (event['time'], event['time_difference'], event['name'], event['action'], event['calibratedValue']) 

print 'Database took %.6f seconds to load' % (databaseLoadTime)
print 'Script took %.6f seconds to compile' % (time.time() - st - databaseLoadTime)
print 'Total time = %.6f' % (time.time() - st)
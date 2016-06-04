"Compile a script"
   
import xml.etree.cElementTree as ET
import itertools
import warnings
import datapointScripts
reload(datapointScripts)
from datapointScripts import EventList, Pulse, Ramp, RfRamp
from collections import OrderedDict
from environs import Environs, FolderCreator
import os
import csv

class Compiler():

    def compileScript(self, scriptPath, db):
        self.db = db
        #Load a script
        #Read Database into ElementTree
        scriptTree = ET.ElementTree(file=scriptPath) 
        self.eventList = EventList(scriptTree)
        #Calibrate the values for which the channel exists in the database if devices.search(event['name']) != None}
        
        [self.calibrateEvent(event) for event in self.eventList]
        
        #Channel doesn't exit
        self.noChannelList = [event['name'] for event in self.eventList if self.db.devices.search(event['name']) == None and event['action'] != 'delay']
        #[warnings.warn('The channel ' + '"'+channel_name+'"' +' is not defined within the database.') for channel_name in self.noChannelList]
     
        #Compiler steps:
        #Get the channels and sort into their respective devices (?)
        #Add the ramp data
        [self.eventList.extend(event.unPack(self.db.devices.search(event['name']))) for event in self.eventList]
        self.eventList.sort(key = lambda event: (event['time'], -event['time_difference']))
        
        self.startedAlreadyList = []
        
        [self.createTimingPulses(event) for event in self.eventList if event['action'] != 'delay' and event['name'] not in self.noChannelList]
    
        #Remove Duplicates and order
        self.eventList = EventList(list(set(self.eventList)))
        
        #Account for delays in trigger pulses
        #i.e. some pulses are delayed to syncronize the device responce times
        [event.delayEvent(self.db.devices.search(event['name'])) for event in self.eventList \
                if event['action'] != 'delay' and event['name'] not in self.noChannelList]
        self.eventList.sort(key=lambda event: (event['time'], -event['time_difference'], event['name']))
    
        #Loop over pairs and adjust time delays 
        #If the first event has been delayed to a negative time, 
        #lets set it to time zero and add the difference  
        if self.eventList[0] < 0:
            difference = self.eventList[1]['time'] - self.eventList[0]['time']
            self.eventList[0]['time'] = 0;
            self.eventList[1]['time'] += difference 
        for event, nextEvent in self.pairwise(self.eventList):
            nextEvent['time_difference'] = nextEvent['time'] - event['time']
        
        #Work out all the amplitudes for the script, for ploting purposes.
        [self.getAmplitude(event) for event in self.eventList if event['action'] != 'delay' and event['name'] not in self.noChannelList]
        
        #Seperate eventlists per device
        deviceNames=set([event['device'] for event in self.eventList if event['action'] != 'delay' and event['name'] not in self.noChannelList])
        self.deviceEventList = {device:EventList(self.eventList.search(('device', device))) for device in deviceNames}
    
        debugEventList = self.deviceEventList    
        
        #Manipulate the data into the require format
        self.deviceData = {device:self.timeDataList(device) for device in deviceNames}
        self.configureImaging()
        return (self.deviceData,debugEventList)
    
    def calibrateEvent(self, event):
        channel = self.db.devices.search(event['name'])
        if channel != None:
            event.calibrate(channel)
    
    def getAmplitude(self, event):
        channel = self.db.devices.search(event['name'])
        if channel != None:
            event.getAmplitude(channel)
    
    #Add additional pulse events due to the triggering
    #Get the device trigger for each event
    #add a trigger pulse to start device or clock pulse for each sample to output.
    def createTimingPulses(self, event):
        device = self.db.devices.searchForDevice(event['name'])
        #Remember the device name for later use
        event['device'] = device['name']
        #We only need to provide one start trigger per device
        #If the device has no external clock. 
        #Create a list to remember which devices has already been provided a trigger
        try:
            clock = device['triggering']['clock']
            startTrigger = device['triggering']['startTrigger']
        except (KeyError):
            # Keithley supplies look like device['triggering']['channel_zero']['clock']
            if self.db.devices.search(event['name'])['channel'].split('_')[-1] == '00':
                clock = device['triggering']['channel_zero']['clock']
                startTrigger = device['triggering']['channel_zero']['startTrigger']
            elif self.db.devices.search(event['name'])['channel'].split('_')[-1] == '01':
                clock = device['triggering']['channel_one']['clock']
                startTrigger = device['triggering']['channel_one']['startTrigger']
        if clock != 'internal' and clock != 'none':
            #The device uses an external clock
            channel = self.db.devices.search(clock)
            if channel != None:
                #The channel exists - create clock tick
                eventData = {'time':event['time'], 
                        'time_difference':event['time_difference'],
                        'name':clock, 'newValue':'high', 'stage':event['stage'],
                        'comment':event['comment'], 'action':'pulse',
                        'calibratedValue':None }
                pulse = Pulse.createEventFromDict(eventData)
                pulse.calibrate(channel)
                self.eventList.extend([pulse])
                self.eventList.extend(pulse.unPack(self.db.devices.search(pulse['name'])))
        elif startTrigger != 'internal':
            #The device uses a start trigger
            channel = self.db.devices.search(startTrigger)
            if channel != None and device['name'] not in self.startedAlreadyList:
                #The channel exists, and the device needs a start trigger - create device start trigger
                #Add device name to the list of already started devices, so we don't provide 
                #more than one start trigger per device.
                self.startedAlreadyList.extend([device['name']])
                eventData = {'time':event['time'], 
                        'time_difference':event['time_difference'],
                        'name':startTrigger, 'newValue':'high', 'stage':event['stage'],
                        #Note action may not be a pulse for a trigger in the database
                        #We call it a pulse here, but we check later if its a changeValue trigger (ie a latch)
                        #and compile accordingly
                        'comment':event['comment'], 'action':'pulse',
                        'calibratedValue':None }
                pulse = Pulse.createEventFromDict(eventData)
                pulse.calibrate(channel)
                self.eventList.extend([pulse])
                self.eventList.extend(pulse.unPack(self.db.devices.search(pulse['name'])))
                
    
    #Adjust for the new time differences
    #Function to get the current and next event in a loop
    def pairwise(self, iterable):
        event, nextEvent = itertools.tee(iterable)
        next(nextEvent, None)
        return itertools.izip(event, nextEvent)
        
    #For first time, search all channels for that time and fill in data
    #set the other channels to there defaults.
    def concurrency(self, event, device, idx,sortedEvents):
        index=idx+1
        concurrentEvents=[]
        #Add the event to the list to begin with.
        concurrentEvents.append(event)
        #Find all events that occur at the same time
        if index == len(self.deviceEventList[device]): 
            pass
        else: 
            while event['time']==self.deviceEventList[device][index]['time']:
                concurrentEvents.append(self.deviceEventList[device][index])
                index+=1
                if index == len(self.deviceEventList[device]):
                    break
        tmplist = []
        for concurrentEvent in concurrentEvents:
            if isinstance(concurrentEvent, Ramp):
                value = concurrentEvent['calibratedValue']['startValue']['value']
            elif isinstance(concurrentEvent, RfRamp):
                value = concurrentEvent['calibratedValue']['startValue']['value']
            else:
                value = concurrentEvent['calibratedValue']['value']
            tmplist.extend([{concurrentEvent['name']:value}])
        return {event['time']:tmplist}
           
    def timeDataList(self, device):
        previousValues = []
        #Per device get the active channels (no duplicates)
        activeChannels = set([e['name'] for e in self.deviceEventList[device]])
        #Create a dictionary of { Time:[{channel:value] }
        d=[]
        oldTime=0
        #print device
        self.deviceEventList[device].sort(key = lambda event: (event['time'], -event['time_difference']))
        for i, e in enumerate(self.deviceEventList[device]):
            clist = self.concurrency(e, device,i,self.deviceEventList[device])
            #Times
            key = clist.keys()[0]
            #[{Channel:Values}]
            value = clist.values()[0]
            channels = [channel.keys()[0] for channel in value]
            if i == 0:
                newValues = [{channel:self.db.devices.search(channel).calibratedSafeState()['value']} \
                            for channel in activeChannels if channel not in channels]
            else:
                newValues = [{channel:next((elem[channel] for elem in previousValues if elem.keys()[0] == channel), None) }\
                    for channel in activeChannels if channel not in channels]
            value.extend(newValues)
            previousValues = value
            new = {self.db.devices.search(key)['channel']:val for v in value for key, val in v.items()} 
            if i==0 or oldTime!=key:
                d.append([key,sorted(new.items())])
            allChannels = [channel.keys()[0] for channel in value]
            oldTime=key
        tD={'events':d, 'channel_map':{channel:self.db.devices.search(channel)['channel'] for channel in allChannels}}
        return tD
    
    def _csv_writer(self,header,data,path):
        with open(path,"wb") as csv_file:
            writer = csv.writer(csv_file,delimiter=',')
            for line in header:
                writer.writerow(line)
            for line in data:
                writer.writerow(line)

    def dataToFile(self):
        '''Write deviceData into a csv file'''
        #Make sure data folder exists
        FolderCreator().createDataFolders()
        paths = Environs.factory()
        base = paths.todaysScriptFolder()['Instrument Scripts']
        path = os.path.join(base, 'Output.csv')
        #Prepare the Device Configuration
        for device in self.deviceData.keys(): 
            if device in ['Dio64','Ao8a','Ao8b','SpinCoreDDS0','SpinCoreDDS1', 'k3390']:
                triggering = ['triggering'] + [self.db.devices[device]['triggering']['clock']]
                triggering = triggering + [self.db.devices[device]['triggering']['startTrigger']]
                limit = ['limit']
                if device != 'Dio64':
                    rangeI = ['range'] + [self.db.devices[device]['range']['min']] + [self.db.devices[device]['range']['max']]
                else:
                    #No range information for digital card
                    rangeI = ['range']
            else:
                #Keithleys and HMP2030
                triggering = ['triggering']
                rangeI = ['range']
                limit = ['limit']
                if device != 'HMP2030':
                    #Keithley power supplies
                    for channel in self.db.devices[device]['triggering'].keys():
                        triggering = triggering + [channel]
                        triggering = triggering + [self.db.devices[device]['triggering'][channel]['clock']]
                        triggering = triggering + [self.db.devices[device]['triggering'][channel]['startTrigger']]
                        rangeI = rangeI + [channel]
                        rangeI = rangeI + [self.db.devices[device]['range'][channel]['current']] + [self.db.devices[device]['range'][channel]['voltage']]
                        limit = limit + [channel]
                        limit = limit + [self.db.devices[device]['limits'][channel]['current_limit']]
                        limit = limit + [self.db.devices[device]['limits'][channel]['voltage_limit']]
                else:
                    #HMP2030
                    triggering = ['triggering'] + [self.db.devices[device]['triggering']['clock']]
                    triggering = triggering + [self.db.devices[device]['triggering']['startTrigger']]
                    rangeI = ['range'] + [self.db.devices[device]['range']['min']] + [self.db.devices[device]['range']['max']]
                    for channel in self.db.devices[device]['triggering'].keys():
                        limit = limit + [channel]
                        limit = limit + [self.db.devices[device]['limits'][channel]['current_limit']]
                        limit = limit + [self.db.devices[device]['limits'][channel]['voltage_limit']]
            #header = ['time']+[item[0] for item in self.deviceData[device]['events'][0][1]]
            usedChannels = [item[0] for item in self.deviceData[device]['events'][0][1]]
            chans = [[x for (x,y) in self.deviceData[device]['channel_map'].items() if y == channel][0] for channel in usedChannels]
            safety=[(self.db.devices[device]['channels'][channel]['channel'],
                        self.db.devices[device]['channels'][channel].calibrate(self.db.devices[device]['channels'][channel]['safe_state'])['value'])
                        for channel in chans]
            safety.sort()
            if device in ['SpinCoreDDS0', 'SpinCoreDDS1']:
                safeValues = ['SafeValues'] + [[value[1]['amplitude'],value[1]['frequency'],value[1]['phase']] for value in safety]
            else:
                safeValues = ['SafeValues'] + [value[1] for value in safety]
            time = ['time']+usedChannels
            header = [triggering, rangeI, limit, time, safeValues]
            times = [data[0] for data in self.deviceData[device]['events']]
            values = [[item[1] for item in data[1]] for data in self.deviceData[device]['events']]
            if device in ['SpinCoreDDS0', 'SpinCoreDDS1']:
                rfValues = [[[value['amplitude'],value['frequency'],value['phase']] for value in valueSet] for valueSet in values]
                data = [[times[i]]+rfValues[i] for i in range(0,len(times))]
            else:
                data=[[times[i]]+values[i] for i in range(0,len(times))]
            #Write data to output file
            path = os.path.join(base,device+'.csv')
            self._csv_writer(header,data,path)
            #write imaging information into file
            path = os.path.join(base, 'Imaging.csv')
            headers = ['']+self.cameras.keys()
            data = ['images']+[self.cameras[key]['images'] for key in self.cameras.keys()]
            self._csv_writer([headers], [data], path)
                
                
    def configureImaging(self):
        #Find the cameras in use
        pixisCount = len(self.eventList.search(('name', 'Pixis_trigger')))/2
        proEMCount = len(self.eventList.search(('name', 'ProEM_trigger')))/2
        pixelflyCount = len(self.eventList.search(('name','Pixelfly_trigger')))/2
        self.cameras = {'pixis':{'images':pixisCount}, 'proEm':{'images':proEMCount}, 'pixelfly':{'images':pixelflyCount}}
        #ToDo
        #How many images they each take
        #What is the exposure times for each

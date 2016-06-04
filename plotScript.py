"Import the XML database and compile a script, then plot the amplitude for all channels and times."
import time
import database
reload(database)
from database import Database
import compile
reload(compile)
from compile import Compiler
import matplotlib.pyplot as plt
import numpy as np
import re
import sys, os

st = time.time() #What's the time? We will find out how long certain processes take to run
        
#File Path to the database
#Find the path to the current working directory (where this code is located)
#And append the database.xml filename
dirname = os.path.dirname('__file__')
dbPath = os.path.join(dirname, 'DeviceSettingsAtomChip.xml')
 
#load the database
db = Database(dbPath)
databaseLoadTime = time.time() - st

#scriptPath = sys.argv[1]
#scriptPath = '/Users/paul/Data/University stuff/CQT/Data/ScriptRunFolder/Long/141203_1409_19 03Amp-Dimple-CB3-LR_Dp.xml'

#Path to the xml experiment script
scriptPath = os.path.join(dirname, '141203_1409_19 03Amp-Dimple-CB3-LR_Dp.xml')


#Load a script and compile
compiler = Compiler()
(deviceData,debug) = compiler.compileScript(scriptPath, db)
#compiler.dataToFile()

print 'Database took %.6f seconds to load' % (databaseLoadTime)
print 'Script took %.6f seconds to compile' % (time.time() - st - databaseLoadTime)
print 'Total time = %.6f' % (time.time() - st)
print 'Channels missing from database: %s' % compiler.noChannelList

eventAmp = [(event['time']/1000000,event['name'],event['amplitude'],event['stage']) for event in compiler.eventList if event['action']!='delay' and event['name'] not in compiler.noChannelList]

def getValue(index,data):
    value = [item[index] for item in data]
    return value
    
def getValueByStage(index,stage,data):
    value = [item[index] for item in data if item[2]==stage]
    return value
    
def getEvent(events,channel):
    value = [(item[0],item[2],item[3]) for item in events if item[1]==channel]
    return value
    
    
channels = list(set([item[1] for item in eventAmp]))

eventDict = {channel:getEvent(eventAmp,channel) for channel in channels}

for channel in channels:
    extra=[(eventDict[channel][index+1][0]-1E-6,event[1],event[2]) for (index,event) in enumerate(eventDict[channel][0:-1])]
    eventDict[channel] = eventDict[channel]+extra
    eventDict[channel].sort(key=lambda e:(e[0]))

plotChannels = ['Cooling_Detuning','U_Wire','Optical_Pumping','keithleyA','keithleyB','keithleyC','keithleyD','UpDown_Coil','Bias_Coil','Ioffe_Coil','Imaging_Aom']
j=0
# These are the "Tableau 20" colors as RGB.  
tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),  
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),  
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),  
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),  
             (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]  
  
# Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.  
for i in range(len(tableau20)):  
    r, g, b = tableau20[i]  
    tableau20[i] = (r / 255., g / 255., b / 255.) 
f, ax = plt.subplots(len(plotChannels),sharex=True) 
for (i,channel) in enumerate(plotChannels):
    if getValue(0,eventDict[channel])!=[]:
        if channel == 'U_Wire':
            channelName = 'Big U'
        elif channel == 'keithleyA':
            channelName = 'U Wire'
        elif channel == 'keithleyB':
            channelName = 'Z Wire'
        elif channel == 'keithleyC':
            channelName = 'I Wire'
        elif channel == 'keithleyD':
            channelName = 'CB3'
        elif channel == 'keithleyE':
            channelName = 'CB2'
        elif channel == 'keithleyF':
            channelName = 'CB1'
        elif channel == 'keithleyG':
            channelName = 'CB4'
        else:
            channelName = re.sub('_',' ',channel)
        ax[j].plot(getValue(0,eventDict[channel]),getValue(1,eventDict[channel]),'r',color=tableau20[j],lw=1.5)
        start, end = ax[j].get_ylim()
        ax[j].set_autoscalex_on(False)
        ax[j].yaxis.set_ticks(np.arange(start, 1.5*end, (1.5*end-start)/4))
        ax[j].xaxis.set_ticks(np.arange(10,10.5, 0.1))
        plt.xlim(10,10.55)
        ax[j].spines['top'].set_visible(False)
        ax[j].spines['right'].set_visible(False)
        ax[j].spines['bottom'].set_visible(False)
        ax[j].get_xaxis().set_visible(False)
        ax[j].text(10.01, start+(end-start)/2, channelName, fontsize=12, color=tableau20[j])
        ax[j].set_axis_bgcolor('white')
        ax[j].tick_params(axis='x', colors='green')
        ax[j].tick_params(axis='y', colors='green')
        j+=1
    
fig = plt.gcf()
size = fig.get_size_inches()
fig.set_size_inches(size[0]*2, size[1]*2, forward=True)
plt.tight_layout()
fig.set_facecolor('white')
ax[j-1].get_xaxis().set_visible(True)
ax[j-1].spines['bottom'].set_visible(True)
plt.show()

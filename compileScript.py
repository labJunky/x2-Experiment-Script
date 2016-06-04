"Import the XML database and compile a script"
import time
st = time.time()
import database
reload(database)
from database import Database
import compile
reload(compile)
from compile import Compiler
import sys
        
#File Path to the database
dbPath = '/Users/paul/Data/University stuff/CQT/Data/Settings Database/DeviceSettingsAtomChip.xml'
#dbPath = 'C:\\Users\\Administrator\\Desktop\\Crete\\Data\\Scripts\\Settings Database\\DeviceSettingsAtomChip.xml'
 
#load the database
db = Database(dbPath)
#scriptPath = sys.argv[1]
#scriptPath = 'C:\\Users\\Administrator\\Desktop\\Crete\\Data\\Scripts\\ScriptRunFolder\\141114_0031_03 06Amp-Dimple-CB3-CB2-CB1-CB4-LR_Dp.xml'
scriptPath = '/Users/paul/Data/University stuff/CQT/Data/ScriptRunFolder/new/06Amp-Dimple-CB3-CB2-CB1-CB4-LR.xml'

databaseLoadTime = time.time() - st

#Load a script and compile
compiler = Compiler()
(deviceData,debug) = compiler.compileScript(scriptPath, db)
compiler.dataToFile()
#Write into the file the safe state for all the channels in use.

print 'Database took %.6f seconds to load' % (databaseLoadTime)
print 'Script took %.6f seconds to compile' % (time.time() - st - databaseLoadTime)
print 'Total time = %.6f' % (time.time() - st)
print 'Channels missing from database: %s' % compiler.noChannelList
#TODO: devices.py:Device._prepareChannelDetails() need to add 'restricted' channel label
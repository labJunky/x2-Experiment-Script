"Import the XML database and compile a script"
import time
st = time.time()
import database
reload(database)
from database import Database
import compile
reload(compile)
from compile import Compiler
import profile
        
#File Path to the database
dbPath = '/Users/paul/Data/University stuff/CQT/Data/Settings Database/DeviceSettingsAtomChip.xml'
 
#load the database
db = Database(dbPath)
#scriptPath = sys.argv[1]
scriptPath = '/Users/paul/Data/University stuff/CQT/Data/ScriptRunFolder/new/06Amp-Dimple-CB3-CB2-CB1-CB4-LR.xml'
databaseLoadTime = time.time() - st

#Load a script and compile
compiler = Compiler()
profile.run('compiler.compileScript(scriptPath, db)')



#The result say that compiler.timeDataList takes up most of the time, particularly because of the
#ordereddict that I use. This is a pure python implementation, not written in C like the normal Dict.
#It is taking a lot of time to set new items and update itself. 

#I suggest I find a way to replace it.

#Also datapointScripts.py:22(search) is called 6164 times! Surely there is a better way that to call it
#so many times! Total time is 8 seconds!

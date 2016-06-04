class UndefinedState(Exception):
    def __init__(self, state):
        self.state = state
    def __str__(self):
        return 'This state ' + '"'+self.state+'"' + ' is not defined within the database.'
    
class UndefinedLevel(Exception):
    def __init__(self, level):
        self.level = level
    def __str__(self):
        return 'This digital level or state ' + '"'+self.level+'"' + ' is not defined within the database.'
        
class UndefinedChannel(Exception):
    def __init__(self, channel_name):
        self.channel_name = channel_name
    def __str__(self):
        return 'The channel ' + '"'+self.channel_name+'"' +' is not defined within the database.'
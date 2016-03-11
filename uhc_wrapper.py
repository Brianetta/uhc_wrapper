######################
# UHC Wrapper
# Copyright © Brian Ronald, 2016
# Wrapper script for Minecraft server 1.9
# Implements UHC game rules via console
######################

import pexpect
import codecs
import re
import yaml
import time

# Name of server jar
server_jar = 'minecraft_server.1.9.jar'

# Config file
configfile = 'uhc_wrapper.yml'

# Command line builder
commandline = 'java -jar ' + server_jar + ' nogui'

uhcprefix = '{"text":"[UHC] ","color":"yellow"}'

# read the config
config = yaml.load(open(configfile,'r'))
x = int(config['x'])
z = int(config['z'])
minuteMarker = int(config['minutemarker'])
teamsize = int(config['playersperteam'])

# Internal variables
players = set()
timeStart = None
targetTime = 0
worldborderAnnounce = set()
teams = {}
playerteams = {}

######################
# Compile some regular expressions. Things we look for in the minecraft server output.
regexp = {}
# Just to add colour, and so that we can strip them out.
regexp['info'] = re.compile('^\[[0-9]+:[0-9]+:[0-9]+.*INFO\]: ')
regexp['warn'] = re.compile('^\[[0-9]+:[0-9]+:[0-9]+.*WARN\]: ')
# This lets us know that the server is up and ready
regexp['done'] = re.compile('^Done \([0-p].[0-9]+s\)! For help, type "help" or "?"')
# This matches a player connecting to the server
regexp['connect'] = re.compile('^\w+\[/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+\] logged in')
# This matches a player diconnecting from the server
regexp['disconnect'] = re.compile('\w+ lost connection: ')
# A command typed by a player
regexp['command'] = re.compile('^<\w+> !\w+')
# The world border's current width
regexp['border'] = re.compile('^World border is currently [0-9]+ blocks wide')

def announce(name,json_message):
    minecraft.sendline('tellraw ' + name + ' [' + uhcprefix + ','+json_message+']')

def announceAll(json_message):
    announce('@a',json_message)

def announceGold(name,message):
    announce(name,'{"text":"'+message+'","color":"gold"}')

def announceAllGold(message):
    announceGold('@a',message)

def buildLobby():
    # Build a lobby
    minecraft.sendline('fill '+ str(x-9)+' 251 '+ str(z-9)+' '+ str(x+8)+' 255 '+ str(z+8)+' minecraft:barrier\n')
    minecraft.sendline('fill '+ str(x-9)+' 255 '+ str(z-9)+' '+ str(x+8)+' 255 '+ str(z+8)+' minecraft:stained_glass 15\n')
    minecraft.sendline('fill '+ str(x-8)+' 253 '+ str(z-8)+' '+ str(x+7)+' 255 '+ str(z+7)+' minecraft:air\n');
    minecraft.sendline('setblock '+str(x)+' 252 '+str(z)+' minecraft:end_portal_frame 4\n')
    minecraft.sendline('setblock '+str(x)+' 253 '+str(z)+' minecraft:stained_glass_pane 3\n')
    # Decorate it and set the spawn
    minecraft.sendline('kill @e[tag=Origin]\n')
    minecraft.sendline('summon ArmorStand '+str(x)+' 252 '+str(x)+' {Invisible:1,CustomName:"UHC Lobby",CustomNameVisible:1,HandItems:[{id:iron_sword},{id:iron_sword}],ArmorItems:[{},{},{},{id:diamond_block,Count:1,tag:{ench:[{id:0,lvl:1}]}}],CustomNameVisible:1,Invulnerable:1}\n')
    minecraft.sendline('scoreboard players tag @e[type=ArmorStand,x='+str(x)+',y=252,z='+str(z)+',c=1] add Origin\n')
    minecraft.sendline('entitydata @e[tag=Origin] {Pose:{LeftArm:[0f,-90f,-60f],RightArm:[0f,90f,60f],Head:[0f,45f,0f]}}\n')
    # Build the command blocks
    minecraft.sendline('fill '+str(x)+' 0 '+str(z)+' '+str(x+15)+' 2 '+str(z+15)+' minecraft:bedrock\n')
    minecraft.sendline('setblock '+str(x+1)+' 1 '+str(z+1)+' minecraft:repeating_command_block 3 replace {auto:1b,Command:"effect @a minecraft:regeneration 1 20 true"}\n')
    minecraft.sendline('setblock '+str(x+1)+' 1 '+str(z+2)+' minecraft:chain_command_block 3 replace {auto:1b,Command:"effect @a minecraft:saturation 1 20 true"}\n')
    minecraft.sendline('setblock '+str(x+1)+' 1 '+str(z+3)+' minecraft:chain_command_block 3 replace {auto:1b,Command:"effect @a minecraft:weakness 1 20 true"}\n')
    minecraft.sendline('setblock '+str(x+3)+' 1 '+str(z+1)+' minecraft:repeating_command_block 3 replace {auto:1b,Command:"tp @e[tag=Origin] ~ ~ ~ ~10 ~"}\n')
    minecraft.sendline('setblock '+str(x+3)+' 1 '+str(z+2)+' minecraft:chain_command_block 3 replace {auto:1b,Command:"weather clear"}\n')
    # Put everybody in the lobby
    minecraft.sendline('spreadplayers '+str(x)+' '+str(z)+' 0 8 true @a')
    announceAllGold('Welcome to the Ultra Hardcore lobby')

def destroyLobby():
    minecraft.sendline('kill @e[tag=Origin]\n')
    minecraft.sendline('fill '+ str(x-9)+' 251 '+ str(z-9)+' '+ str(x+8)+' 255 '+ str(z+8)+' minecraft:air\n')
    minecraft.sendline('fill '+str(x)+' 0 '+str(z)+' '+str(x+15)+' 2 '+str(z+15)+' minecraft:bedrock\n')
    announceAllGold('Lobby has been removed.')

def prepareGame():
    # Set some game rules
    minecraft.sendline('gamerule doDaylightCycle false\n')
    minecraft.sendline('gamerule commandBlockOutput false\n')
    minecraft.sendline('gamerule logAdminCommands false\n')
    minecraft.sendline('gamerule naturalRegeneration false\n')
    minecraft.sendline('time set 6000\n')
    minecraft.sendline('worldborder center '+str(x)+' '+str(z)+'\n')

def playerJoins(name,ip):
    announceGold(name,'Welcome, ' + name + '. For UHC command help, say !help in chat.')
    players.add(name)

def playerLeaves(name):
    players.remove(name)

def saveConfig(name):
    config['x'] = x
    config['z'] = z
    config['minutemarker'] = minuteMarker
    config['playersperteam'] = teamsize
    handle = open(configfile,'w')
    handle.write(yaml.dump(config,default_flow_style=False))
    handle.close()
    announceGold(name,'Configuration saved to '+configfile)

def nonOpHelp():
    announce(name,'{"text":"========== ","color":"gold"},{"text":"[","color":"yellow"},{"text":"UHC Help","color":"dark_red"},{"text":"]","color":"yellow"},{"text":" ==========","color":"gold"}')
    announce(name,'{"text":"!help","color":"white"},{"text":" Show this help","color":"gold"}')
    announce(name,'{"text":"!utc","color":"white"},{"text":" Show current time (UTC)","color":"gold"}')
    announce(name,'{"text":"!time","color":"white"},{"text":" Show elapsed game time","color":"gold"}')
    announce(name,'{"text":"!border","color":"white"},{"text":" Show the world border width","color":"gold"}')

def opHelp():
    # Continuation of non-op, but for staff/hosts
    announce(name,'{"text":"!buildlobby","color":"white"},{"text":" Build and initialise the lobby","color":"gold"}')
    announce(name,'{"text":"!destroylobby","color":"white"},{"text":" Destroy and de-activate the lobby","color":"gold"}')
    announce(name,'{"text":"!x","color":"white"},{"text":" Set X coordinate of map centre","color":"gold"}')
    announce(name,'{"text":"!z","color":"white"},{"text":" Set Z coordinate of map centre","color":"gold"}')
    announce(name,'{"text":"!save","color":"white"},{"text":" Save configuration","color":"gold"}')
    announce(name,'{"text":"!minutes","color":"white"},{"text":" Set the time between minute markers","color":"gold"}')
    announce(name,'{"text":"!teamsize","color":"white"},{"text":" Set number of players per team","color":"gold"}')
    announce(name,'{"text":"!eternal","color":"white"},{"text":" Set eternal day/night/off (after minutes)","color":"gold"}')
    #announce(name,'{"text":"!","color":"white"},{"text":" ","color":"gold"}')

def handleCommand(name,command,args):
    command = command.lower() # Make commands case insensitive
    if command=='help':
        nonOpHelp()
    if command=='utc':
        announceGold(name,'Current UTC time: '+time.strftime('%H:%M (%A)',time.gmtime()))
    if command=='time':
        if timeStart==None:
            announceGold(name,'Game has not started yet')
        else:
            announceGold(name,'Elapsed time: ' + str(int((time.time() - timeStart)/60)) + ' minutes')
    if command=='border':
        worldborderAnnounce.add(name)
        minecraft.sendline('worldborder get\n')
    # Operator commands
    if name in config['ops']:
        if command=='help':
            opHelp()
        if command=='buildlobby':
            prepareGame()
            buildLobby()
        if command=='destroylobby':
            destroyLobby()
        if command=='x':
            if args.isnumeric():
                global x
                x = int(args)
                announceGold(name,'X set to '+str(x))
                minecraft.sendline('worldborder center '+str(x)+' '+str(z)+'\n')
            else:
                announceGold(name,'Centre X is currently '+str(x))
        if command=='z':
            if args.isnumeric():
                global z
                z = int(args)
                announceGold(name,'Z set to '+str(z))
                minecraft.sendline('worldborder center '+str(x)+' '+str(z)+'\n')
            else:
                announceGold(name,'Centre Z is currently '+str(z))
        if command=='minutes':
            if args.isnumeric():
                global minuteMarker
                minuteMarker = int(args)
                announceGold(name,'Minute marker set to every '+str(minuteMarker)+' minutes')
            else:
                announceGold(name,'Minute marker is currently every '+str(minuteMarker)+' minutes')
        if command=='teamsize':
            if args.isnumeric():
                global teamsize
                teamsize = int(args)
                announceGold(name,'Auto-assigned teams will have '+str(teamsize)+' players')
            else:
                announceGold(name,'Team size is set to '+str(teamsize)+' players')
        if command=='eternal':
            subc,suba='',''
            if args!='':
                subc = args.split()[0]
                if args != subc:
                    suba = args.split()[1]
            if subc in {'day','night','off'}:
                global config
                config['eternal']['mode'] = subc
                announceGold(name,'Sun stops at permanent state: ' + subc.capitalize())
                if suba.isnumeric():
                    config['eternal']['timebegin'] = int(suba)
                    announceGold(name,'This takes place after ' + suba + ' minutes')
                else:
                    announceGold(name,'This takes place after ' + str(config['eternal']['timebegin']) + ' minutes')
            elif subc.isnumeric():
                announceGold(name,'Sun stops at permanent state: ' + config['eternal']['mode'].capitalize())
                config['eternal']['timebegin'] = int(subc)
                announceGold(name,'This takes place after ' + subc + ' minutes')
            else:
                announceGold(name,'Sun stops at permanent state: ' + config['eternal']['mode'].capitalize())
                announceGold(name,'This takes place after ' + str(config['eternal']['timebegin']) + ' minutes')
        if command=='save':
            saveConfig(name)

######################
# Action begins here #
######################

# Spawn the server
minecraft = pexpect.spawn(commandline,timeout=None,encoding=None)
running = minecraft.isalive()

while(running):

    # Read Minecraft console.
    result = minecraft.expect([
        # result == 0
        pexpect.EOF,
        # result == 1
        pexpect.TIMEOUT,
        # result == 2
        # If pexpect was non-greedy (as documented) this would match one line.
        # spoiler: It can match several.
        '^.*\r\n' 
        ],timeout=10) # The timeout stops this thing blocking, lets us do other things
    
    # Show all unmatched output
    print(minecraft.before.replace(b'\r',b'').decode(),end='')

    if result == 0:
        running = False
    elif result == 1:
        # expect was blocking, so just do nothing here. No-op.
        None
    elif result == 2:
        # To remove in production; assert that '^.*\r\n' left nothing out in front
        assert(minecraft.before==b'')

        # pexpect docs insist that its regex matching is 100% non-greedy.
        # This is not true at all. It'll randomly be greedy.
        # So, we cannot assume that we only got one line. Decode and split.
        lines = minecraft.after.replace(b'\r',b'').decode().split('\n')

        # Now we can examine each line of output in turn.
        for line in lines:
            # First, strip out the prefix (time, thread, info/warn) and
            # separate it, with ANSI colour codes
            m = regexp['info'].match(line)
            if m != None:
                line = line.replace(m.group(),'')
                prefix='\033[32m'+m.group()+'\033[m'
            else:
                m = regexp['warn'].match(line)
                if m != None:
                    line = line.replace(m.group(),'')
                    prefix='\033[33m'+m.group()+'\033[m'
                else:
                    prefix=''

            # If the world/spawn was just prepared, then prepare it for UHC
            #m = regexp['done'].match(line)
            #if m != None:
            #    prepareGame()

            # Check if a player has logged in
            m = regexp['connect'].match(line)
            if m != None:
                nameip = m.group().split(' ')[0]
                name = nameip.split('[')[0]
                ip = nameip.split('/')[1].split(':')[0]
                playerJoins(name,ip)

            # Check if a player has left the game
            m = regexp['disconnect'].match(line)
            if m != None:
                name=m.group().split()[0]
                playerLeaves(name)

            # Look for a command
            m = regexp['command'].match(line)
            if m != None:
                # First word, chop off the < and >
                name = m.group().split()[0][1:-1]
                # Everything right of the bang
                command = m.group().split('!')[1]
                # Any arguments
                args = line.replace(m.group(),'').lstrip()
                handleCommand(name,command,args)

            # Look for a world border announcement
            m = regexp['border'].match(line)
            if m!=None:
                for name in worldborderAnnounce:
                    announceGold(name,line)
                worldborderAnnounce.clear()

            # Output the line, complete with prefix, for console watchers
            if len(line)>0:
                if line[-1] == '\n':
                    print(prefix + line,end='')
                else:
                    print(prefix + line,end='\n')

    if timeStart != None:
        # Show the minute marker
        t = time.time()
        if targetTime < timeStart:
            targetTime = timeStart + minuteMarker * 60
        if t > targetTime:
            minutesElapsed = int((t - timeStart)/60)
            minecraft.sendline('playsound minecraft:entity.firework.launch ambient Brianetta\n')
            announceAllGold('Minute marker: '+ str(minutesElapsed)+' minutes')
            targetTime = targetTime + minuteMarker * 60

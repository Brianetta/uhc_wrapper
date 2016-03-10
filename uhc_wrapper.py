######################
# UHC Wrapper
# Copyright © Brian Ronald, 2016
# Wrapper script for Minecraft server 1.9
# Implements UHC game rules via console
######################

import pexpect
import pexpect.replwrap
import codecs
import re

# Name of server jar
server_jar = 'minecraft_server.1.9.jar'

# Command line builder
commandline = 'java -jar ' + server_jar + ' nogui'

uhcprefix = '{"text":"[UHC] ","color":"yellow"}'

players = set()

######################
# Compile some regular expressions. Things we look for in the minecraft server output.
regexp = {}
# Just to add colour, and so that we can strip them out.
regexp['info'] = re.compile('^\[[0-9]+:[0-9]+:[0-9]+.*INFO\]: ')
regexp['warn'] = re.compile('^\[[0-9]+:[0-9]+:[0-9]+.*WARN\]: ')
# This lets us know that the server is up and ready
regexp['done'] = re.compile('Done \([0-p].[0-9]+s\)! For help, type "help" or "?"')
# This matches a player connecting to the server
regexp['connect'] = re.compile('\w+\[/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+\] logged in')
# This matches a player diconnecting from the server
regexp['disconnect'] = re.compile('\w+ lost connection: ')

def announce(name,json_message):
    minecraft.sendline('tellraw ' + name + ' [' + uhcprefix + ','+json_message+']')

def announceAll(json_message):
    announce('@a',json_message)

def prepareGame():
    minecraft.sendline('gamerule doDaylightCycle false')
    minecraft.sendline('gamerule commandBlockOutput false')
    minecraft.sendline('gamerule logAdminCommands false')
    minecraft.sendline('time set 6000')

#announceAll('{"text","This server is being controlled by the UHC wrapper","color","aqua"}')

def playerJoins(name,ip):
    announce(name,'{"text":"Welcome, ' + name + '","color":"gold"}')
    players.add(name)

def playerLeaves(name):
    players.remove(name)

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
            m = regexp['done'].match(line)
            if m != None:
                prepareGame()

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

            # Output the line, complete with prefix, for console watchers
            if len(line)>0:
                if line[-1] == '\n':
                    print(prefix + line,end='')
                else:
                    print(prefix + line,end='\n')

    print('Players known: ',end='')
    print(players)

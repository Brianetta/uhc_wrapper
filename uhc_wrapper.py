######################
# UHC Wrapper
# Copyright © Brian Ronald, 2016
# Wrapper script for Minecraft server 1.9
# Implements UHC game rules via console
# Please excuse British spellings
######################

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
import re
import time
import math

import pexpect
import yaml

# Config file
configfile = 'uhc_wrapper.yml'

uhc_prefix = '{"text":"[UHC] ","color":"yellow"}'

# read the config
config = yaml.load(open(configfile, 'r'))

# Command line builder
commandline = str(config['java']) + ' -jar ' + config['jar'] + ' nogui'

# Set variables defined in config
x = int(config['x'])
z = int(config['z'])
minute_marker = int(config['minutemarker'])
teamsize = int(config['playersperteam'])
reveal_names = int(config['revealnames'])
timeout = int(config['timeout'])

spectators = set(config['ops'])  # Default value only

# Internal variables
players = set()
time_start = None
target_time = 0
worldborder_announce = set()
teams = {}
playerteams = {}
dead_players = set()
teamcolours = {
    0: 'red',
    1: 'blue',
    2: 'yellow',
    3: 'green',
    4: 'aqua',
    5: 'gold',
    6: 'light_purple',
    7: 'dark_red',
    8: 'dark_blue',
    9: 'dark_green',
    10: 'dark_aqua',
    11: 'dark_purple',
    12: 'gray',
    13: 'dark_grey',
    14: 'black'
}
flag_border = True
flag_visibility = True
flag_eternal = True
disconnected_players = {}

######################
# Compile some regular expressions. Things we look for in the minecraft server output.
regexp = {}
# Just to add colour, and so that we can strip them out.
regexp['info'] = re.compile('^>*\[[0-9]+:[0-9]+:[0-9]+.*INFO\]: ')
regexp['warn'] = re.compile('^>*\[[0-9]+:[0-9]+:[0-9]+.*WARN\]: ')
# This lets us know that the server is up and ready
regexp['done'] = re.compile('^Done \([0-p].[0-9]+s\)! For help, type "help" or "?"')
# This matches a player connecting to the server
regexp['connect'] = re.compile('^\w+\[/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+\] logged in')
# This matches a player diconnecting from the server
regexp['disconnect'] = re.compile('\w+ lost connection: ')
# A command typed by a player
regexp['command'] = re.compile('^<.+> !\w+')
# The world border's current width
regexp['border'] = re.compile('^World border is currently [0-9]+ blocks wide')
# For technical reasons...
regexp['unknown'] = re.compile('^Unknown command. Try /help for a list of commands')
# List of players
regexp['playerlist'] = re.compile('^(\w+, )*(\w+)$')
# Death messages. Why can't this be simple?
regexp['death'] = re.compile('.+ was shot by arrow|' +
                             '.+ was shot by .+|' +
                             '.+ was shot by .+ using .+|' +
                             '.+ was pricked to death|' +
                             '.+ walked into a cactus while trying to escape .+|' +
                             '.+ was stabbed to death|' +
                             '.+ drowned|' +
                             '.+ drowned whilst trying to escape .+|' +
                             '.+ experienced kinetic energy|' +
                             '.+ blew up|' +
                             '.+ was blown up by .+|' +
                             '.+ hit the ground too hard|' +
                             '.+ fell from a high place|' +
                             '.+ fell off a ladder|' +
                             '.+ fell off some vines|' +
                             '.+ fell out of the water|' +
                             '.+ fell into a patch of fire|' +
                             '.+ fell into a patch of cacti|' +
                             '.+ was doomed to fall by .+|' +
                             '.+ was shot off some vines by .+|' +
                             '.+ was shot off a ladder by .+|' +
                             '.+ was blown from a high place by .+|' +
                             '.+ was squashed by a falling anvil|' +
                             '.+ was squashed by a falling block|' +
                             '.+ went up in flames|' +
                             '.+ burned to death|' +
                             '.+ was burnt to a crisp whilst fighting .+|' +
                             '.+ walked into a fire whilst fighting .+|' +
                             '.+ tried to swim in lava|' +
                             '.+ tried to swim in lava while trying to escape .+|' +
                             '.+ was struck by lightning|' +
                             '.+ was slain by .+|' +
                             '.+ was slain by .+ using .+|' +
                             '.+ got finished off by .+|' +
                             '.+ got finished off by .+ using .+|' +
                             '.+ was fireballed by .+|' +
                             '.+ was killed by magic|' +
                             '.+ was killed by .+ using magic|' +
                             '.+ starved to death|' +
                             '.+ suffocated in a wall|' +
                             '.+ was killed while trying to hurt .+|' +
                             '.+ fell out of the world|' +
                             '.+ fell from a high place and fell out of the world|' +
                             '.+ withered away|' +
                             '.+ was pummeled by .+')


def announce(name, json_message):
    minecraft.sendline('tellraw ' + name + ' [' + uhc_prefix + ',' + json_message + ']')


def announce_all(json_message):
    announce('@a', json_message)


def announce_gold(name, message):
    announce(name, '{"text":"' + message + '","color":"gold"}')


def announce_all_gold(message):
    announce_gold('@a', message)


def destroy_teams():
    # Scoreboard
    for teamnumber in range(0, 15):
        minecraft.sendline('scoreboard teams remove ' + str(teamnumber) + '\n')
    # Internal
    playerteams.clear()
    teams.clear()


def show_team(name):
    if name in playerteams:
        team = playerteams[name]
        minecraft.sendline(
            'tellraw ' + name + ' [' + uhc_prefix + ',{"text":"Your team is ' + teams[team] + '",' +
            '"color":"' + teamcolours[team] + '"}]\n')
        minecraft.sendline(
            'tellraw ' + name + ' [' + uhc_prefix + ',{"text":"Your team members are ","color":"gold"},' +
            '{"selector":"@a[team=' + str(team) + ']"}]\n')
    else:
        announce_gold(name, 'You have not yet been assigned to a team')


def show_teams():
    for team in teams:
        minecraft.sendline('tellraw @a[team=' + str(team) + '] [' + uhc_prefix + ',{"text":"Your team is ' + teams[
            team] + '","color":"' + teamcolours[team] + '"}]\n')
        minecraft.sendline('tellraw @a[team=' + str(
            team) + '] [' + uhc_prefix + ',{"text":"Your team members are ","color":"gold"},' +
                           '{"selector":"@a[team=' + str(team) + ']"}]\n')
    for spectator in spectators:
        announce_gold(spectator, 'You are a spectator')


def create_teams():
    destroy_teams()
    teampool = list(players - spectators)
    if len(teampool) == 0:
        announce_all_gold('Cannot assign teams, because everybody is spectating')
        return
    number_of_teams = min(math.ceil(len(teampool) / teamsize), 15)  # hard-coded max of 15 teams
    teamnames = config['teamnames'].copy()
    global teams
    global playerteams
    # Create actual teams
    random.shuffle(teamnames)
    for teamnumber in range(0, number_of_teams):
        if teamnumber < number_of_teams:  # teamnumber is indexed from zero
            # Internal
            teams[teamnumber] = teamnames.pop()
            # Scoreboard
            minecraft.sendline('scoreboard teams add ' + str(teamnumber) + ' ' + teams[teamnumber] + '\n')
            minecraft.sendline(
                'scoreboard teams option ' + str(teamnumber) + ' color ' + teamcolours[teamnumber] + '\n')
            minecraft.sendline('scoreboard teams option ' + str(teamnumber) + ' nametagVisibility hideForOtherTeams\n')
    # Randomly assign players to those teams
    random.shuffle(teampool)
    # Internal
    while len(teampool) > 0:
        for teamnumber in teams:
            if len(teampool) > 0:
                playerteams[teampool.pop()] = teamnumber
    # Scoreboard
    for player in playerteams:
        minecraft.sendline('scoreboard teams join ' + str(playerteams[player]) + ' ' + player + '\n')
    show_teams()
    minecraft.sendline('effect @a minecraft:glowing 3 1 true')


def swap_team_member(player1, player2):
    if set(playerteams.keys()) & {player1, player2} == {player1, player2}:
        # Internal
        playerteams[player1], playerteams[player2] = playerteams[player2], playerteams[player1]
        # Scoreboard
        minecraft.sendline('scoreboard teams leave ' + player1 + '\r')
        minecraft.sendline('scoreboard teams leave ' + player2 + '\r')
        minecraft.sendline('scoreboard teams join ' + str(playerteams[player1]) + ' ' + player1 + '\r')
        minecraft.sendline('scoreboard teams join ' + str(playerteams[player2]) + ' ' + player2 + '\r')
        minecraft.sendline('effect @a[team=' + str(playerteams[player1]) + '] minecraft:glowing 3 1 true')
        minecraft.sendline('effect @a[team=' + str(playerteams[player2]) + '] minecraft:glowing 3 1 true')


def spectate(name, args):
    if args == '':
        announce_gold(name, 'Toggle spectators by providing their names (case sensitive)')
    else:
        for spectator in args.split():
            if spectator in spectators:
                spectators.remove(spectator)
                if time_start is not None:
                    minecraft.sendline('scoreboard players set ' + spectator + ' spectating 0\n')
            else:
                spectators.add(spectator)
                if time_start is not None:
                    minecraft.sendline('scoreboard players set ' + spectator + ' spectating 1\n')
                    minecraft.sendline('gamemode 3 ' + spectator + '\n')
    spectator_output = list()
    for spectator in spectators:
        spectator_output.append(', ')
        spectator_output.append(spectator)
    spectator_output.pop(0)
    if len(spectator_output) > 2:
        spectator_output[1] = ' and '
    spectator_output.reverse()
    output = ''
    for w in spectator_output:
        output = output + w
    announce_gold(name, 'Spectators: ' + output)


def build_lobby():
    # Refresh players
    minecraft.sendline('list\n')
    dead_players.clear()
    # Build a lobby
    minecraft.sendline(
        'fill ' + str(x - 9) + ' 251 ' + str(z - 9) + ' ' + str(x + 8) + ' 255 ' + str(z + 8) + ' minecraft:barrier\n')
    minecraft.sendline('fill ' + str(x - 9) + ' 255 ' + str(z - 9) + ' ' + str(x + 8) + ' 255 ' + str(
        z + 8) + ' minecraft:stained_glass 15\n')
    minecraft.sendline(
        'fill ' + str(x - 8) + ' 253 ' + str(z - 8) + ' ' + str(x + 7) + ' 255 ' + str(z + 7) + ' minecraft:air\n')
    minecraft.sendline('setblock ' + str(x) + ' 252 ' + str(z) + ' minecraft:end_portal_frame 4\n')
    minecraft.sendline('setblock ' + str(x) + ' 253 ' + str(z) + ' minecraft:stained_glass_pane 3\n')
    minecraft.sendline('setworldspawn ' + str(x) + ' 253 ' + str(z))
    # Decorate it and set the spawn
    minecraft.sendline('kill @e[tag=Origin]\n')
    minecraft.sendline('summon ArmorStand ' + str(x) + ' 252 ' + str(
        z) + ' {DisabledSlots:2039567,Invisible:1,CustomName:"UHC Lobby",CustomNameVisible:1,' +
                       'HandItems:[{id:iron_sword},{id:iron_sword}],' +
                       'ArmorItems:[{},{},{},{id:diamond_block,Count:1,tag:{ench:[{id:0,lvl:1}]}}],' +
                       'CustomNameVisible:1,Invulnerable:1}\n')
    minecraft.sendline(
        'scoreboard players tag @e[type=ArmorStand,x=' + str(x) + ',y=252,z=' + str(z) + ',c=1] add Origin\n')
    minecraft.sendline(
        'entitydata @e[tag=Origin] {Pose:{LeftArm:[0f,-90f,-60f],RightArm:[0f,90f,60f],Head:[0f,45f,0f]}}\n')
    # Build the command blocks
    minecraft.sendline(
        'fill ' + str(x) + ' 0 ' + str(z) + ' ' + str(x + 15) + ' 2 ' + str(z + 15) + ' minecraft:bedrock\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 1) + ' minecraft:repeating_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a minecraft:regeneration 5 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 2) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a minecraft:saturation 5 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 3) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a minecraft:weakness 1 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 3) + ' 1 ' + str(
        z + 1) + ' minecraft:repeating_command_block 3 replace {auto:1b,' +
                       'Command:"tp @e[tag=Origin] ~ ~ ~ ~10 ~"}\n')
    minecraft.sendline('setblock ' + str(x + 3) + ' 1 ' + str(
        z + 2) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"weather clear"}\n')
    # Put everybody in the lobby
    minecraft.sendline('gamemode 2 @a')
    minecraft.sendline('spreadplayers ' + str(x) + ' ' + str(z) + ' 0 6 true @a')
    announce_all_gold('Welcome to the Ultra Hardcore lobby')


def destroy_lobby():
    minecraft.sendline('kill @e[tag=Origin]\n')
    minecraft.sendline(
        'fill ' + str(x - 9) + ' 251 ' + str(z - 9) + ' ' + str(x + 8) + ' 255 ' + str(z + 8) + ' minecraft:air\n')
    minecraft.sendline(
        'fill ' + str(x) + ' 0 ' + str(z) + ' ' + str(x + 15) + ' 2 ' + str(z + 15) + ' minecraft:bedrock\n')


def prepare_game():
    # Set some game rules
    minecraft.sendline('gamerule doDaylightCycle false\n')
    minecraft.sendline('gamerule commandBlockOutput false\n')
    minecraft.sendline('gamerule logAdminCommands false\n')
    minecraft.sendline('gamerule naturalRegeneration false\n')
    minecraft.sendline('time set 6000\n')
    minecraft.sendline('worldborder center ' + str(x) + ' ' + str(z) + '\n')
    # Clear in-play objectives
    minecraft.sendline('scoreboard objectives remove dead\n')
    minecraft.sendline('scoreboard objectives remove spectating\n')
    minecraft.sendline('scoreboard objectives remove indeathroom\n')
    # Create basic objective
    minecraft.sendline('scoreboard objectives add health health\n')
    minecraft.sendline('scoreboard objectives setdisplay list health\n')
    minecraft.sendline('scoreboard objectives add spectating dummy\n')
    global time_start
    time_start = None


def begin_game():
    # Create a room for dead players
    minecraft.sendline(
        'fill ' + str(x) + ' 3 ' + str(z) + ' ' + str(x + 15) + ' 7 ' + str(z + 15) + ' minecraft:bedrock\n')
    minecraft.sendline(
        'fill ' + str(x + 1) + ' 5 ' + str(z + 1) + ' ' + str(x + 14) + ' 6 ' + str(z + 14) + ' minecraft:air\n')
    minecraft.sendline(
        'fill ' + str(x + 1) + ' 4 ' + str(z + 1) + ' ' + str(x + 14) + ' 4 ' + str(z + 14) + ' minecraft:carpet\n')
    minecraft.sendline(
        'fill ' + str(x + 1) + ' 3 ' + str(z + 1) + ' ' + str(x + 14) + ' 3 ' + str(z + 14) + ' minecraft:glowstone\n')
    # Move players from the lobby, clear their inventories
    minecraft.sendline('tp @a ' + str(x + 8) + ' 4 ' + str(z + 8) + '\n')
    minecraft.sendline('clear @a\n')
    # Lose the lobby
    destroy_lobby()
    # Decorate it
    minecraft.sendline('kill @e[tag=DeathRoom]')
    minecraft.sendline('summon ArmorStand ' + str(x + 8) + ' 3 ' + str(
        z + 8) + ' {DisabledSlots:2039567,Invisible:1,CustomName:"Death Room",CustomNameVisible:1,' +
                       'ArmorItems:[{},{},{},{id:redstone_block,Count:1,tag:{ench:[{id:0,lvl:1}]}}],' +
                       'CustomNameVisible:1,Invulnerable:1}\n')
    minecraft.sendline(
        'scoreboard players tag @e[type=ArmorStand,x=' + str(x + 8) + ',y=3,z=' + str(z + 8) + ',c=1] add DeathRoom\n')
    global time_start
    time_start = time.time()
    # Scoreboard to control it all
    minecraft.sendline('scoreboard objectives add dead stat.deaths\n')
    minecraft.sendline('scoreboard objectives add indeathroom dummy\n')
    # Blocks to update the scoreboards
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 1) + ' minecraft:repeating_command_block 3 replace {auto:1b,' +
                       'Command:"scoreboard players set @a indeathroom 0"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 2) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"scoreboard players set @e[type=Player,x=' + str(
        x + 1) + ',y=4,z=' + str(z + 1) + ',dx=14,dy=3,dz=14] indeathroom 1"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 3) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"tp @e[type=Player,score_indeathroom=0,score_dead_min=1] ' + str(
        x + 8) + ' 4 ' + str(z + 8) + '"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 4) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a[score_indeathroom_min=1] minecraft:regeneration 5 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 5) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a[score_indeathroom_min=1] minecraft:saturation 5 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 6) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a[score_indeathroom_min=1] minecraft:weakness 1 20 true"}\n')
    minecraft.sendline('setblock ' + str(x + 1) + ' 1 ' + str(
        z + 7) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"gamemode 2 @a[score_dead_min=1,m=!2]"}\n')
    minecraft.sendline('setblock ' + str(x + 3) + ' 1 ' + str(
        z + 1) + ' minecraft:repeating_command_block 3 replace {auto:1b,' +
                       'Command:"tp @e[tag=DeathRoom] ~ ~ ~ ~5 ~"}\n')
    minecraft.sendline('setblock ' + str(x + 3) + ' 1 ' + str(
        z + 2) + ' minecraft:chain_command_block 3 replace {auto:1b,' +
                       'Command:"execute @e[tag=DeathRoom] ~ ~ ~ spawnpoint @a ~ ~1 ~"}\n')
    minecraft.sendline('setblock ' + str(x + 5) + ' 1 ' + str(
        z + 1) + ' minecraft:repeating_command_block 3 replace {auto:1b,' +
                       'Command:"effect @a[score_spectating_min=1] minecraft:night_vision 20 20 true"}\n')
    # Set the border
    minecraft.send('worldborder set ' + str(config['worldborder']['start']) + '\n')
    # Deal with spectators
    minecraft.sendline('scoreboard players set @a spectating 0\n')
    for spectator in players & spectators:
        minecraft.sendline('scoreboard players set ' + spectator + ' spectating 1\n')
    # Spread the players
    minecraft.sendline(
        'spreadplayers ' + str(x) + ' ' + str(z) + ' ' + str(int(config['worldborder']['start'] - 1) * 0.4) + ' ' + str(
            int(config['worldborder']['start'] - 1) / 2) + ' true @a[score_spectating=0]\n')
    # Start the sun
    minecraft.sendline('gamerule doDaylightCycle true\n')
    # Set the appropriate game modes
    minecraft.sendline('gamemode 0 @a[score_spectating=0]\n')
    minecraft.sendline('gamemode 3 @a[score_spectating_min=1]\n')
    minecraft.sendline('tp @a[score_spectating_min=1] ~ 200 ~\n')
    announce_all('{"text":"The game has begun!","color":"green"}')


def victorious(team):
    destroy_lobby()
    minecraft.sendline('gamemode 3 @a[m=2]\n')
    minecraft.sendline(
        'title @a subtitle {"text":"' + teams[team] + ' have won","color":"' + teamcolours[team] + '"}\n')
    minecraft.sendline('title @a title {"text":"Victorious!","color":"gold"}\n')
    announce_all('{"text":"' + teams[team] + ' have won UHC","color":"' + teamcolours[team] + '"}')
    minecraft.sendline(
        'tellraw @a [{"text":"Congratulations to ","color":"gold"},{"selector":"@a[team=' + str(team) + ']"}]\n')


def all_dead(name):
    destroy_lobby()
    minecraft.sendline('gamemode 3 @a[m=2]\n')
    minecraft.sendline('title @a subtitle {"text":"All players are dead.","color":"white"}\n')
    minecraft.sendline('title @a title {"text":"Game Over","color":"gold"}\n')
    announce_all_gold(name + ' was the last player standing')


def death(name):
    if name in dead_players:
        return
    dead_players.add(name)
    team = playerteams.pop(name, None)
    minecraft.sendline('execute @a ~ ~ ~ playsound minecraft:entity.lightning.impact ambient @a[c=1]\n')
    if team is None:
        return
    if name in players:
        players.remove(name)
    survivors = 0
    for member in playerteams:
        if playerteams[member] == team:
            survivors += 1
    if survivors == 0:
        announce_all('{"text":"' + teams[team] + ' have been eliminated","color":"' + teamcolours[team] + '"}')
    if len(set(playerteams.values())) == 1:
        for player in playerteams:
            victorious(playerteams[player])
    if len(set(playerteams.values())) == 0:
        all_dead(name)


def player_joins(name):
    if name not in players:
        announce_gold(name, 'Welcome, ' + name + '. For UHC command help, say !help in chat.')
        players.add(name)
    # New joiners (after game start) treated as dead
    if name not in players | spectators and time_start is not None:
        minecraft.sendline('scoreboard players set ' + name + ' dead 1\n')
    # Players rejoining after the timeout are made dead
    if time_start is not None and name in disconnected_players:
        if time.time() > disconnected_players[name] + timeout:
            announce_all_gold(name + ' has been declared dead.')
            death(name)
        del disconnected_players[name]


def player_leaves(name):
    # Make a note of when a player left (ignoring spectators)
    if name in players - spectators:
        disconnected_players[name] = time.time()


def save_config(name):
    config['x'] = x
    config['z'] = z
    config['minutemarker'] = minute_marker
    config['playersperteam'] = teamsize
    config['revealnames'] = reveal_names
    config['timeout'] = timeout
    handle = open(configfile, 'w')
    handle.write(yaml.dump(config, default_flow_style=False))
    handle.close()
    announce_gold(name, 'Configuration saved to ' + configfile)


def non_op_help():
    announce(name,
             '{"text":"========== ","color":"gold"},{"text":"[","color":"yellow"},' +
             '{"text":"UHC Help","color":"dark_red"},{"text":"]","color":"yellow"},' +
             '{"text":" ==========","color":"gold"}')
    announce(name, '{"text":"!help","color":"white"},{"text":" Show this help","color":"gold"}')
    announce(name, '{"text":"!utc","color":"white"},{"text":" Show current time (UTC)","color":"gold"}')
    announce(name, '{"text":"!time","color":"white"},{"text":" Show elapsed game time","color":"gold"}')
    announce(name, '{"text":"!team","color":"white"},{"text":" Show your team information","color":"gold"}')
    announce(name, '{"text":"!border","color":"white"},{"text":" Show the world border width","color":"gold"}')


def op_help():
    # Continuation of non-op, but for staff/hosts
    announce(name, '{"text":"!border","color":"white"},' +
             '{"text":" (admin) set start, finish, timebegin, duration","color":"gold"}')
    announce(name, '{"text":"!buildlobby","color":"white"},{"text":" Build and initialise the lobby","color":"gold"}')
    announce(name, '{"text":"!destroylobby","color":"white"},' +
             '{"text":" Destroy and de-activate the lobby","color":"gold"}')
    announce(name, '{"text":"!x","color":"white"},{"text":" Set X coordinate of map centre","color":"gold"}')
    announce(name, '{"text":"!z","color":"white"},{"text":" Set Z coordinate of map centre","color":"gold"}')
    announce(name, '{"text":"!save","color":"white"},{"text":" Save configuration","color":"gold"}')
    announce(name, '{"text":"!minutes","color":"white"},{"text":" Set the time between minute markers","color":"gold"}')
    announce(name, '{"text":"!teamsize","color":"white"},{"text":" Set number of players per team","color":"gold"}')
    announce(name, '{"text":"!timeout","color":"white"},' +
             '{"text":" Set number of seconds that players can be disconnected","color":"gold"}')
    announce(name, '{"text":"!eternal","color":"white"},' +
             '{"text":" Set eternal day/night/off (after minutes)","color":"gold"}')
    announce(name, '{"text":"!revealnames","color":"white"},' +
             '{"text":" Set delay before players can see enemy name tags","color":"gold"}')
    announce(name, '{"text":"!spectate","color":"white"},{"text":" View or toggle spectators","color":"gold"}')
    announce(name, '{"text":"!teamswap","color":"white"},{"text":" Swap two players between teams","color":"gold"}')
    announce(name, '{"text":"!teamup","color":"white"},{"text":" Generate and assign teams","color":"gold"}')
    announce(name, '{"text":"!refreshplayers","color":"white"},{"text":" Attempt to redetect players","color":"gold"}')
    announce(name, '{"text":"!begin","color":"white"},{"text":" Start the game","color":"gold"}')
    announce(name, '{"text":"!op","color":"white"},{"text":" Get op on server itself","color":"gold"}')


def handle_command(name, command, args):
    global x
    global z
    command = command.lower()  # Make commands case insensitive
    if command == 'help':
        non_op_help()
    if command == 'utc':
        announce_gold(name, 'Current UTC time: ' + time.strftime('%H:%M (%A)', time.gmtime()))
    if command == 'time':
        if time_start is None:
            announce_gold(name, 'Game has not started yet')
        else:
            announce_gold(name, 'Elapsed time: ' + str(int((time.time() - time_start) / 60)) + ' minutes')
    if command == 'team':
        show_team(name)
    if command == 'border':
        worldborder_announce.add(name)
        minecraft.sendline('worldborder get\n')
    # Operator commands
    if name in config['ops']:
        if command == 'help':
            op_help()
        if command == 'buildlobby':
            prepare_game()
            build_lobby()
        if command == 'destroylobby':
            destroy_lobby()
        if command == 'x':
            if args.isnumeric():
                x = int(args)
                announce_gold(name, 'X set to ' + str(x))
                minecraft.sendline('worldborder center ' + str(x) + ' ' + str(z) + '\n')
            else:
                announce_gold(name, 'Centre X is currently ' + str(x))
        if command == 'z':
            if args.isnumeric():
                z = int(args)
                announce_gold(name, 'Z set to ' + str(z))
                minecraft.sendline('worldborder center ' + str(x) + ' ' + str(z) + '\n')
            else:
                announce_gold(name, 'Centre Z is currently ' + str(z))
        if command == 'minutes':
            if args.isnumeric():
                global minute_marker
                minute_marker = int(args)
            announce_gold(name, 'Minute marker set to every ' + str(minute_marker) + ' minutes')
        if command == 'revealnames':
            if args.isnumeric():
                global reveal_names
                reveal_names = int(args)
            announce_gold(name, 'Enemy name tags visible after ' + str(reveal_names) + ' minutes')
        if command == 'teamsize':
            if args.isnumeric():
                global teamsize
                teamsize = int(args)
            announce_gold(name, 'Team size is set to ' + str(teamsize) + ' players')
        if command == 'timeout':
            if args.isnumeric():
                global timeout
                timeout = int(args)
            announce_gold(name, 'Death on disconnect timeout is set to ' + str(timeout) + ' seconds')
        if command == 'eternal':
            subc, suba = '', ''
            if args != '':
                subc = args.split()[0]
                if args != subc:
                    suba = args.split()[1]
            if subc in {'day', 'night', 'off'}:
                config['eternal']['mode'] = subc
                announce_gold(name, 'Sun stops at permanent state: ' + subc.capitalize())
                if suba.isnumeric():
                    config['eternal']['timebegin'] = int(suba)
                    announce_gold(name, 'This takes place after ' + suba + ' minutes')
                else:
                    announce_gold(name, 'This takes place after ' + str(config['eternal']['timebegin']) + ' minutes')
            elif subc.isnumeric():
                announce_gold(name, 'Sun stops at permanent state: ' + config['eternal']['mode'].capitalize())
                config['eternal']['timebegin'] = int(subc)
                announce_gold(name, 'This takes place after ' + subc + ' minutes')
            else:
                announce_gold(name, 'Sun stops at permanent state: ' + config['eternal']['mode'].capitalize())
                announce_gold(name, 'This takes place after ' + str(config['eternal']['timebegin']) + ' minutes')
        if command == 'save':
            save_config(name)
        if command == 'begin':
            begin_game()
        if command == 'border' and time_start is None:
            subc, suba = '', ''
            if args != '':
                subc = args.split()[0]
                if args != subc:
                    suba = args.split()[1]
            if subc in {'duration', 'finish', 'start', 'timebegin'}:
                if suba.isnumeric():
                    config['worldborder'][subc] = int(suba)
            announce_gold(name, 'World border starting width (start): ' + str(config['worldborder']['start']))
            announce_gold(name, 'World border final width (finish): ' + str(config['worldborder']['finish']))
            announce_gold(name, 'Minutes until border moves (timebegin): ' + str(config['worldborder']['timebegin']))
            announce_gold(name, 'Time taken in minutes to shrink (duration): ' + str(config['worldborder']['duration']))
        if command == 'teamup':
            create_teams()
        if command == 'teamswap':
            if args != '':
                player1 = args.split()[0]
                if args != player1:
                    player2 = args.split()[1]
                    swap_team_member(player1, player2)
                    announce_gold(name, 'Swapped ' + player1 + ' and ' + player2)
                else:
                    announce_gold(name, '!teamswap player1 player2')
            else:
                announce_gold(name, '!teamswap player1 player2')
        if command == 'spectate':
            spectate(name, args)
        if command == 'refreshplayers':
            minecraft.sendline('list\n')
        if command == 'op':
            minecraft.sendline('op ' + name + '\n')


def fix_name(name):
    # Spigot, with team colours
    if name[0] == '?':
        return name[2:-2]
    # Vanilla, with team colours
    if name[0] == '§':
        return name[2:-2]
    # No colours
    else:
        return name


######################
# Action begins here #
######################

# Spawn the server
minecraft = pexpect.spawn(commandline, timeout=None, encoding=None, env={"TERM": "dumb"})
running = minecraft.isalive()

while running:

    # I'll mention it here. All my sendline() commands send an extra '\n' at the end. This is
    # so that the command as typed by pexpect doesn't interfere with the pattern
    # matching in this section, which is heavily dependent on line endings.
    # This does result in one "Unknown command" per command, because Minecraft does not
    # ignore empty commands. So, they're filtered after the regex matching, toward the end.

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
    ], timeout=10)  # The timeout stops this thing blocking, lets us do other things

    # Show all unmatched output
    print(minecraft.before.replace(b'\r', b'').decode(), end='')

    if result == 0:
        running = False
    elif result == 1:
        # expect was blocking, so just do nothing here. No-op.
        None
    elif result == 2:
        # To remove in production; assert that '^.*\r\n' left nothing out in front
        assert (minecraft.before == b'')

        # pexpect docs insist that its regex matching is 100% non-greedy.
        # This is not true at all. It'll randomly be greedy.
        # So, we cannot assume that we only got one line. Decode and split.
        lines = minecraft.after.replace(b'\r', b'').decode().split('\n')

        # Now we can examine each line of output in turn.
        for line in lines:
            # First, strip out the prefix (time, thread, info/warn) and
            # separate it, with ANSI colour codes
            m = regexp['info'].match(line)
            if m is not None:
                line = line.replace(m.group(), '')
                prefix = '\033[32m' + m.group() + '\033[m'
            else:
                m = regexp['warn'].match(line)
                if m is not None:
                    line = line.replace(m.group(), '')
                    prefix = '\033[33m' + m.group() + '\033[m'
                else:
                    prefix = ''

            # If the world/spawn was just prepared, then prepare it for UHC
            # m = regexp['done'].match(line)
            # if m != None:
            #    prepareGame()

            # Check if a player has logged in
            m = regexp['connect'].match(line)
            if m is not None:
                nameip = m.group().split(' ')[0]
                name = nameip.split('[')[0]
                ip = nameip.split('/')[1].split(':')[0]
                player_joins(name)

            # Check if a player has left the game
            m = regexp['disconnect'].match(line)
            if m is not None:
                name = m.group().split()[0]
                player_leaves(name)

            # Look for a command
            m = regexp['command'].match(line)
            if m is not None:
                # First word, chop off the < and >, and run through the team colour stripper
                name = fix_name(m.group().split()[0][1:-1])
                # Everything right of the bang
                command = m.group().split('!')[1]
                # Any arguments
                args = line.replace(m.group(), '').lstrip()
                handle_command(name, command, args)

            # Look for a world border announcement
            m = regexp['border'].match(line)
            if m is not None:
                for name in worldborder_announce:
                    announce_gold(name, line)
                worldborder_announce.clear()

            # Look for missed players (respond to /list)
            m = regexp['playerlist'].match(line)
            if m is not None and line != 'list':  # 'list' matches a command we use, and isn't likely to be a player )-:
                for name in m.group().split(', '):
                    if name not in players:
                        player_joins(name)
                print('Players detected: ', players)

            # Look for player deaths
            m = regexp['death'].match(line)
            if m is not None:
                death(fix_name(m.group().split()[0]))

            # Output the line, complete with prefix, for console watchers
            if len(line) > 0 and regexp['unknown'].match(line) is None:
                # Ignore the "Unknown command" warnings from our empty lines
                if line[-1] == '\n':
                    print(prefix + line, end='')
                else:
                    print(prefix + line, end='\n')

    # Scheduled tasks!
    if time_start is not None:
        t = time.time()
        minutes_elapsed = int((t - time_start) / 60)
        # Show the minute marker
        if target_time < time_start:
            target_time = time_start + minute_marker * 60
        if t > target_time:
            minecraft.sendline('execute @a ~ ~ ~ playsound minecraft:entity.firework.launch ambient @a[c=1]\n')
            announce_all_gold('Minute marker: ' + str(minutes_elapsed) + ' minutes')
            target_time += minute_marker * 60
        # Make nametags visible
        if flag_visibility and minutes_elapsed >= reveal_names:
            for team in playerteams:
                minecraft.sendline('scoreboard teams option ' + str(playerteams[team]) + ' nametagVisibility always\n')
            announce_all_gold('Your nametags are now visible to the enemy.')
            flag_visibility = False
        # Eternal day/night
        if flag_eternal and minutes_elapsed >= config['eternal']['timebegin']:
            if config['eternal']['mode'] == 'day':
                minecraft.sendline('gamerule doDaylightCycle false\n')
                minecraft.sendline('time set 6000\n')
                announce_all_gold('Eternal day has begun.')
            if config['eternal']['mode'] == 'night':
                minecraft.sendline('gamerule doDaylightCycle false\n')
                minecraft.sendline('time set 18000\n')
                announce_all_gold('Eternal night has begun.')
            flag_eternal = False
        # Worldborder
        if flag_border and minutes_elapsed >= config['worldborder']['timebegin']:
            minecraft.send('worldborder set ' + str(config['worldborder']['finish']) + ' ' + str(
                config['worldborder']['duration'] * 60) + '\n')
            announce_all_gold('The world border has started shrinking.')
            flag_border = False
        # Players who've been disconnected too long
        deleted = set()
        for name in disconnected_players:
            if time.time() > disconnected_players[name] + timeout:
                announce_all_gold(name + ' has been declared dead.')
                deleted.add(name)
                death(name)
                minecraft.sendline('scoreboard players set ' + name + ' dead 1\n')
        for name in deleted:
            del disconnected_players[name]

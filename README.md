# uhc_wrapper
UHC game mode wrapper for vanilla Minecraft or Spigot

This script runs a Minecraft server, reading its output and entering commands, in order to deliver an [Ultra Hardcore](http://minecraft.gamepedia.com/Tutorials/Ultra_hardcore_survival) PVP match.

### Features:
  - A safe lobby allowing players to gather and be assigned teams before the match begins
  - In-game commands to configure and start the match
  - Configurable spectators list
  - Disabling of natural regeneration (healing from food)
  - Configurable world border size, with shrinking border feature to move players to the centre after a configurable delay
  - Option for eternal day or night, after a configurable delay
  - Configurable grace period at beginning of match where enemy team name tags are hidden
  - Minute markers, with configurable interval, for synchronised video episodes
  - "Death Room" for players who have been killed to wait out the match
    - This room also captures latecomers joining the server
  - Announcement of winning team, ending the match and releasing dead players as spectators

## Pre-requisites:
  - [Python 3](https://www.python.org/), including the [**pexpect** module](http://pexpect.readthedocs.org/en/stable/install.html)
  - Minecraft [server 1.9](https://s3.amazonaws.com/Minecraft.Download/versions/1.9/minecraft_server.1.9.jar) or later, or equivalent Spigot build
  - Java is required for the Minecraft server

## To prepare the UHC game:
  1. Run the Minecraft server at least once to generate its config files, and populate `eula.txt`
  2. Add the line `enable-command-block=true` to the end of the file `server.properties`
  3. (*optional*) Choose a seed and put it into `server.properties`
  4. Set `spawn-protection=0` in `server.properties`
  5. Set `gamemode=2` in `server.properties`
  6. Modify the map as required for your game. Some hosts like to add chests, etc
  7. It's a very good idea to generate your map in advance. This can be done by flying over the map, or by using a [map generator](https://github.com/Morlok8k/MinecraftLandGenerator)
    - Spigot server operators might prefer a plugin, such as WorldBorder, to generate their map.

## To run the UHC game:
  1. Copy the two files `uhc_wrapper.py` and `uhc_wrapper.yml` into the same directory as your Minecraft server
  2. Edit `uhc_wrapper.yml` and remove the example operator names in `ops`. Add your own, and of anybody you wish to be able to control the game.
    - You must make sure that the name of your Minecraft server jar is correct.
    - You can edit any of the options here, but apart from the `ops` list and team names everything can be modified in-game.
  3. Start the minecraft server using `python3 uhc_wrapper.py` (Linux or other command line) or by double-clicking the uhc_wrapper.py file (Windows/Mac)

## In-game commands
All commands are typed into the in-game chat, and begin with an exclamation mark (**!**).

### Commands that all players can use
  - **!help** - Shows help to the player. Shows additional help to those listed as ops.
  - **!utc** - Shows the current UTC time, as understood by the game server. Useful for pre-arranged start times.
  - **!time** - Shows the number of minutes elapsed since the match began.
  - **!team** - Shows the name and colour of the player's team, and the names of their team mates.
  - **!border** - Shows the current diameter of the world border

### Commands that ops (game controllers) can use
  - **!border** - Continuation command; allows ops to configure the border parameters (see below)
  - **!buildlobby** - Builds the UHC game lobby, and decorates it with a spinning enchanted diamond block and a pair of swords
    - Players are switched to adventure mode
    - The decoration is launched
    - Players are given weakness, saturation and regeneration
  - **!destroylobby** - Destroys the lobby and deactivates its effects. Should be used if the lobby has been built, but the map needs to be re-centred (see **!x** and **!z**, below)
  - **!x** - Sets the centre of the map in the X direction
  - **!z** - Sets the centre of the map in the Z direction
  - **!save** - Saves any configuration changes to `uhc_wrapper.yml`
  - **!minutes** - Changes the interval between minute markers. Set to a very high number to effectively disable it.
  - **!teamsize** - Change the number of players on each team. There can be at most 15 teams. The number of teams required will be calculated.
  - **!eternal** - Change the eternal day/night setting. Can be `day`, `night` or `off`, and can be given a number of minutes after the match begins. Off disables the feature.
  - **!revealnames** - The number of minutes after which enemy nametags can be seen by players. Set to 0 to make them always visible.
  - **!spectate** - List / toggle a player's status as a spectator. Begins by default with all ops as spectators. Spectators are given gamemode 3 (spectator mode) and continuous night vision, but do not join a team.
    - This works after the match begins, too, but care should be taken not to turn active players into spectators
  - **!teamswap** - Switches two players between their teams, then gives the affected teams a brief spectral glow. Should only be used before the match begins to balance teams out, after using **!teamup**
  - **!teamup** - Generates teams (randomly named from the list in `uhc_wrapper.yml`) and assigns players at random, trying to keep the number of player in each team at the correct level. If numbers are uneven, teams could be smaller. If there are too many players, teams will be bigger (there is a maximum of 15 teams). After players are allocated to teams, they are briefly given the spectral glow effect.
  - **!refreshplayers** - The script can sometimes miss players joining the server, especially if they all join at once. This will attempt to redetect players in the event that some are not assigned a team by **!teamup**. It will be necessary to run **!teamup** again.
  - **!begin** - This launches the match. The lobby is destroyed, the death room is created, the game clock is started and all triggers are put in place.
  - **!op** - Gives actual server op privileges to the player. Since there is no access to the console while this script is running, this can be necessary.

## UHC match concepts

### Regeneration
Natural regeneration is disabled. Players who suffer inujury will need to use golden apples or potions in order to gain health.

### Name tag visibility
Effectively a grace period at the beginning of the match, name tags are only visible to members of the same team (and to spectators, who are not given a team). After the given delay has elapsed, nametags become universally visible, and players are told in chat. They should then be careful to crouch if they want to avoid being seen.

### World border
A small match area can make games very short and uninteresting, while a large match area can reduce player interaction. To avoid these drawbacks, the world will begin at the diameter given in **!border start**, giving the teams time and space to gather materials, craft weapons, etc. After the number of minutes given in **!border timebegin**, the border will begin to shrink. It will shrink to the diameter specified in **!border finish**, and will take the amount of time in minutes specified in **!border duration** to do so. This will force players to congregate in the middle of the map, making conflict much more likely.

### Eternal day / night
After a configurable delay, the sun can be stopped at midday or midnight. This means that the final fight can take place without fear of spawning mobs, or *with* it, depending on requirements. By default, eternal day begins after 40 minutes, which is two in-game day/night cycles. The match always begins at midday.

### Minute markers
If several players are recording the match for posterity, and wish to release episodes of a consistent length to a schedule, minute markers help the recording players to know when to break episodes.

### Dead players
Once players are killed, they are no longer part of the match. They are placed in adventure mode in a specially constructed Death Room, which is deep in the bedrock at the centre of the match area. Players there are given weakness, regeneration and saturation to prevent further deaths/fighting, and can participate in chat but cannot see the game (unless active players are mining nearby). Dead players cannot leave the Death Room until the game is over. Any successful attempt will result in their being teleported back.

### Winners
Once all the remaining players are in the same team, the winners will be congratulated both in a screen title and in the chat. At this point, players in the Death Room will be released as spectators.

# Thanks

Many thanks go to players and staff on [SimplyCrafted](http://www.simplycrafted.net) for their assistance in testing this script. The testers there have all been very patient and bug-tolerant. They're responsible for the good parts of this script, I am responsible for the poor parts.

I would also like to thank the folks behind [UHC Blox](http://www.planetminecraft.com/project/minecraft-uhc-box/), who inspired me to write this wrapper when I couldn't get their commands running on an oddly configured server. The design of the lobby is inspired by UHC Blox, as is the feature list. That is an excellent product, and I'd recommend it as a superb alternative to uhc_wrapper. Please do respect their licensing terms.

# License

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

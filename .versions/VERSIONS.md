### Version 2.0.1

###### New stuff
 - The bot changes its profile picture with guild count
###### Changes
 - Improved `/elevatorinfo` command
 - Add missing exception catchers
 - Internal clean up
###### Known issues
 - Disconnect by user is not handled correctly

### Version 2.0.0
###### New stuff
 - Bot does stay in VC when disconnected by hand
###### Breaking Changes
 - Complete rework of the way the bot plays music
 - Move to discord.py v2, the bot now supports only slash commands
###### Changes
 - Rework of guild count update
 - Background improvements

### Version 1.2.4
###### New stuff
 - pauses music playing if no one is in the channel
 - force disconnect after multiple errors, not to do so caused issues
###### Changes
 - fixed slash commands in DMs
 - removed Discord Boats
 - soft removed Abstract Discord List from `elevatorreview`
 - fix discords.com wrong server count
 - changed string formatting
 - typos :)
 - background improvements

### Version 1.2.3
###### New stuff
 - The bot is now self deafend
 - After multiple music errors in a specific channel in a short period of time the bot stops playing (in hope to fix the error)
###### Changes
 - Code improvements :)

### Version 1.2.2
###### New stuff
 - Added good error logging
###### Changes
 - Removed the function to stop playing when disconnected by user
 - Updated grammar of 'elevatorinfo'

### Version 1.2.1
###### New stuff
 - Stops playing music when the bot gets disconnected from user
 - If the bot does not have permission to a channel, he stop playing music or he switches back to the previous channel
###### Changes
 - Code improvements
 - Background changes

### Version 1.2.0
###### New stuff
 - Statistics!
 - Added slash commands support, all commands are now usable with slash commands
 - The bot is now also listed on https://botsfordiscord.com/
###### Changes
 - Improved spelling
 - Code improvements
 - Bug fixes
 - Handling to play music
 - Again changed error handling
 - Removed the join message
 - The does not listen anymore on `fuckoff`

### Version 1.1.4
###### Changes
 - Background improvements
 - Even more changes in error handling
 - Music play handling
 - Joining message optimized

### Version 1.1.3
###### New stuff
 - The color of embeds depends now on the highest role color of the bot in a guild
 - If the bot can't answer you in a guild channel, it will tell you via DMs
###### Changes
 - `fuckoff` command is now `elevatorshutdown`
 - Language improvements
 - Background improvements (message sending, error sending and code improvements)

### Version 1.1.2
###### Changes
 - Background optimization and bugfixing.

### Version 1.1.1
###### New stuff
 - The bot reacts now on mentioning and response with the help command

### Version 1.1.0
###### New stuff
 - Added `elevatorreview` command, you can now vote and review the bot on different sites

### Version 1.0.1
###### Changes
- Fixed bugs regarding joining and leaving commands
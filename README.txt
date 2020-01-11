Edit the config.txt file with your info

oauth: "oauth:1234567890abcdefg" <- Your twitch bot oauth (not sure if your streamer oauth is sufficient *have not tested without a bot account*)
streamer_name: "your_twitch_username"
bot_name: "your_bot_name"
relay_bot_name: "restreambot" (shouldn't change this unless restream changes their bot name)
admins: []
mods: []
debug_mode: "true"

admins and mods variables should be comma separated values within the array brackets following the format username:platform,username:platform
debug_mode enables the streamer to pose as the restream bot by typing in [Platform: Username] !command
ex: [YouTube: Dennis08] !add TST-TST-TST
It is helpful to have this enabled in case the relay bot acts funky, you can always pose as that user that is trying to add their level.

-------------------------------
ignore_list.txt
all entries in this file should be line separated:
username:platform
username:platform

ie:
streamlabs:twitch
streamlabs:mixer

------------------------------

queue.txt should not be manually modified, as the script will not catch external changes made and could mess things up quite badly.
Use the bot commands to make modifications to this file, unless you are not streaming. The bot will reload the txt upon running again.
Never modify manually while running the bot and streaming however.

------------------------------
commands.txt is fairly self-explanatory and self documented
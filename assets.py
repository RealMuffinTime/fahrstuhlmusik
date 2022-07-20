list_names = ["Tog.gg", "Bots on Discord", "Discord Bot List", "Abstract List", "Discord Bots", "Discords"]
list_names_short = ["Tgg", "BoD", "DBL", "AL", "DB", "Ds"]
list_reviews = [
    "[View](https://top.gg/bot/669888310507995136) --- "
    "[Vote](https://top.gg/bot/669888310507995136/vote) --- "
    "[Review](https://top.gg/bot/669888310507995136reviews)",
    "[View](https://bots.ondiscord.xyz/bots/669888310507995136) --- "
    "[Review](https://bots.ondiscord.xyz/bots/669888310507995136/review)",
    "[View](https://discordbotlist.com/bots/fahrstuhlmusik) --- "
    "[Vote](https://discordbotlist.com/bots/fahrstuhlmusik/upvote)",
    "[View](https://abstractlist.com/bot/669888310507995136) --- "
    "[Vote](https://abstractlist.com/bot/669888310507995136/vote)",
    "[View](https://discord.bots.gg/bots/669888310507995136)",
    "[View](https://discords.com/bots/bot/669888310507995136) --- "
    "[Vote](https://discords.com/bots/bot/669888310507995136/vote)",
]
list_update_url = [
    "https://top.gg/api/bots/%s/stats",
    "https://bots.ondiscord.xyz/bot-api/bots/%s/guilds",
    "https://discordbotlist.com/api/v1/bots/%s/stats",
    "https://abstractlist.tombeijner.com/api/bots/%s/stats",
    "https://discord.bots.gg/api/v1/bots/%s/stats",
    "https://discords.com/bots/api/bot/%s"
]
list_update_json = ["server_count", "guildCount", "guilds", "servers", "guildCount", "server_count"]
list_update_code = [200, 204, 200, 200, 200, 200]
list_update_temp = ["", "", "", "", "", ""]

info_message = "A bot that plays **elevator music** for hours and hours.\n" \
               "For a support channel or even if you just like to listen to elevator music.\n" \
               "```python\n" \
               "elevatorinfo         'Shows this info.'\n" \
               "elevatormusic        'Starts playing elevator music in your channel.'\n" \
               "fahrstuhlmusik       'Also starts playing elevator music in your channel. :)'\n" \
               "elevatorreview       'You can rate and review the bot on different sites.'\n" \
               "elevatorshutdown     'The bot leaves the current channel.'```" \
               "Hope you have fun... with this bot.\n" \
               "Currently serving on **%s** guilds.\n" \
               "Support & Bugs: <https://discord.gg/Da9haye/>\n" \
               "Current version: %s\n\n" \
               "by **MuffinTime#4484**\n\n"

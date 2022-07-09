import asyncio
import aiohttp
import datetime
import textwrap
import discord
import utils
from discord.ext import commands
from discord.utils import get
from discord_slash import SlashCommand

# TODO tests for performance improvements ???
# TODO find a fix for task was destroyed but was pending
# TODO find a fix for cannot write to closing transport
#
# TODO licensed track
# TODO website and statistics
# TODO move command - own channel which moves down and up (this one moves users form one to another channel, plays fitting sounds (door closes/opens, moving, elevator music) at the end it moves to its saved channel)
# TODO settings command
#
# TODO special events at special days
# TODO open sauce?
#
# TODO donate command
# TODO (implement shards)


# Version 1.2.4 -> 2.0.0
#
# New stuff
#  -
# Breaking Changes
#  - Complete rework of the way the bot plays music
# Changes
#  - Rework of guild count update
#  - Background improvements


bot = None
db_connection = None
slash = None
start_timestamp = None
version = None


def get_bot():
    global bot
    if bot is None:
        bot = commands.Bot(
            command_prefix=None,
            description='Plays hours and hours elevator music.',
            owner_id=412235309204635649,
            case_insensitive=True
        )
    return bot


def get_version():
    global version
    if version is None:
        version = "1.2.4"
    return version


def get_slash():
    global slash
    if slash is None:
        slash = SlashCommand(get_bot())
    return slash


@get_bot().event
async def on_ready():
    utils.get_start_timestamp()
    utils.log("info", f"Logged in as {str(get_bot().user)}.")
    await get_bot().change_presence(activity=discord.Activity(name="elevatorinfo", type=discord.ActivityType.listening))

    for guild in get_bot().guilds:
        await utils.execute_sql(f"INSERT IGNORE INTO set_guilds VALUES ('{guild.id}', '0', NULL, NULL, NULL)", False)
    await update_guild_count()

    playing_guilds = await utils.execute_sql("SELECT guild_id FROM set_guilds WHERE playing = 1;", True)
    for row in playing_guilds:
        await resume_music(row[0], still_playing=False)


@get_bot().event
async def on_guild_join(guild):
    await utils.execute_sql(
        f"INSERT INTO set_guilds VALUES ('{guild.id}', '0', NULL, NULL, NULL) ON DUPLICATE KEY UPDATE playing = '0', channel_id = NULL",
        False)
    await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('add');", False)
    utils.log("info", f"Guild join '{str(guild.id)}'.")
    await update_guild_count()


@get_bot().event
async def on_guild_remove(guild):
    for guild_id in utils.secret.error_guilds:
        if guild.id == guild_id:
            return
    await utils.execute_sql(f"UPDATE set_guilds SET playing = '0', channel_id = NULL WHERE guild_id = '{guild.id}';",
                            False)
    await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('remove');", False)
    utils.log("info", f"Guild leave '{str(guild.id)}'.")
    await update_guild_count()


@get_bot().event
async def on_message(message):
    await on_message_check(message)


@get_bot().event
async def on_message_edit(before, after):
    await on_message_check(after)


async def on_message_check(ctx):
    if not ctx.author.bot or ctx.author == get_bot().user and ctx.content.startswith("<@!"):
        if ctx.author == get_bot().user and ctx.content.startswith("<@!"):
            if str(ctx.channel.type) == "private":
                ctx.author = await get_bot().fetch_user(int(ctx.content[3:21]))
            else:
                ctx.author = await ctx.guild.fetch_member(int(ctx.content[3:21]))

        if '<@!' + str(get_bot().user.id) + '>' in ctx.content or '<@!' + str(get_bot().user.id) + '>' in ctx.content:
            await elevator_info(ctx)
            return

        if 'elevatorinfo' in ctx.content.lower():
            await elevator_info(ctx)
            return

        if 'elevatorreview' in ctx.content.lower():
            await elevator_review(ctx)
            return

        if 'elevatormusic' in ctx.content.lower() or 'fahrstuhlmusik' in ctx.content.lower():
            await elevator_music(ctx)
            return

        if 'elevatorshutdown' in ctx.content.lower():
            await elevator_shutdown(ctx)
            return


@get_bot().event
async def on_voice_state_update(member, before, after):
    if member.id == get_bot().user.id:
        if before.channel is None:
            return
        if after.channel is not None:
            if after.channel.permissions_for(member).connect is False:
                await utils.execute_sql(
                    f"UPDATE set_guilds SET playing = '1', channel_id = '{before.channel.id}' WHERE guild_id = '{member.guild.id}';",
                    False)
                await resume_music(member.guild.id)
                return
        else:
            await utils.execute_sql(
                f"UPDATE set_guilds SET playing = '0', channel_id = NULL WHERE guild_id = '{member.guild.id}';",
                False)
            await stop_music(member.guild.id)
            return
        if after.channel.id != before.channel.id:
            await utils.execute_sql(
                f"UPDATE set_guilds SET playing = '1', channel_id = '{after.channel.id}' WHERE guild_id = '{member.guild.id}';",
                False)
            await resume_music(member.guild.id)

    voice = get(get_bot().voice_clients, guild=member.guild)
    if voice is not None:
        if voice.is_paused() and (len(voice.channel.voice_states.keys()) > 1):
            await resume_music(member.guild.id)
        if voice.is_playing() and (len(voice.channel.voice_states.keys()) <= 1):
            await pause_music(member.guild.id)


@get_slash().slash(name="elevatorinfo")
async def on_slash_command(ctx):
    await on_slash_command_check(ctx)


@get_slash().slash(name="elevatormusic")
async def on_slash_command(ctx):
    await on_slash_command_check(ctx)


@get_slash().slash(name="elevatorreview")
async def on_slash_command(ctx):
    await on_slash_command_check(ctx)


@get_slash().slash(name="elevatorshutdown")
async def on_slash_command(ctx):
    await on_slash_command_check(ctx)


@get_slash().slash(name="fahrstuhlmusik")
async def on_slash_command(ctx):
    await on_slash_command_check(ctx)


async def on_slash_command_check(ctx):
    await ctx.send(content="<@!" + str(ctx.author.id) + "> wants `" + ctx.name + "`? Got it.", delete_after=3)


async def elevator_info(ctx):
    try:
        message = "A bot that plays **elevator music** for hours and hours.\n" \
                  "For a support channel or even if you just like to listen to elevator music.\n" \
                  "```python\n" \
                  "elevatorinfo         'Shows this info.'\n" \
                  "elevatormusic        'Starts playing elevator music in your channel.'\n" \
                  "fahrstuhlmusik       'Also starts playing elevator music in your channel. :)'\n" \
                  "elevatorreview       'You can rate and review the bot on different sites.'\n" \
                  "elevatorshutdown     'The bot leaves the current channel.'```" \
                  "Hope you have fun... with this bot.\n" \
                  f"Currently serving on **{str(len(get_bot().guilds))}** guilds.\n" \
                  "Support & Bugs: <https://discord.gg/Da9haye/>\n" \
                  f"Current version: {get_version()}\n\n" \
                  "by **MuffinTime4484**\n\n"
        await send_message(channel=ctx.channel, author=ctx.author, message=message)
        await utils.execute_sql("INSERT INTO stat_command_info (action) VALUES ('executed');", False)
    except Exception as e:
        await send_message(channel=ctx.channel, author=ctx.author,
                           message="There has been a error.\n"
                                   "For further information contact the support.\n"
                                   "https://discord.gg/Da9haye\n"
                                   f"Your error code is **{utils.on_error('elevator_info()', str(e).strip('.'))}**.",
                           delete=30)
        await utils.execute_sql("INSERT INTO stat_command_info (action) VALUES ('error');", False)


async def elevator_review(ctx):
    try:
        if str(ctx.channel.type) == "private":
            color = discord.Colour.random()
        else:
            if ctx.channel.permissions_for(ctx.author.guild.me).embed_links is False:
                await send_message(channel=ctx.channel, author=ctx.author,
                                   message="Can't answer:\nI don't have permission to embed links.", delete=10)
                return
            color = ctx.channel.guild.me.color.value

        embed = discord.Embed(title="Here you can review this bot and vote for it",
                              description='Below you will find pages where the bot is listed.', colour=color)
        embed.set_author(name=str(get_bot().user), url="https://bots.muffintime.tk/fahrstuhlmusik/")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/707514263077388320/730372388130258964/fahrstuhlmusik_logo.png")

        sites = utils.secret.lists
        for site in sites:
            if sites.index(site) != sites.index(sites[2]):
                embed.add_field(name=site[0], value=site[1], inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=True)

        await send_message(channel=ctx.channel, author=ctx.author, embed=embed)
        await utils.execute_sql("INSERT INTO stat_command_review (action) VALUES ('executed');", False)
    except Exception as e:
        await send_message(channel=ctx.channel, author=ctx.author,
                           message="There has been a error.\n"
                                   "For further information contact the support.\n"
                                   "https://discord.gg/Da9haye\n"
                                   f"Your error code is **{utils.on_error('elevator_review()', str(e).strip('.'))}**.",
                           delete=30)
        await utils.execute_sql("INSERT INTO stat_command_review (action) VALUES ('error');", False)


async def elevator_music(ctx):
    try:
        if str(ctx.channel.type) == "private":
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't play music:\nThis command doesn't work in DMs.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('fault');", False)
            return

        if ctx.author.voice is None:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't play music:\nYou are not in a voice channel.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('fault');", False)
            return

        if ctx.author.voice.channel.permissions_for(ctx.author.guild.me).connect is False:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't play music:\nCan't access your voice channel.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('fault');", False)
            return

        guild = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {ctx.guild.id};", True)
        if guild[0][1] == 1:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't play music:\nAlready playing music.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('fault');", False)
            return

        await send_message(channel=ctx.channel, author=ctx.author, message="On command:\nPure relaxation.", delete=10)
        await utils.execute_sql(
            f"UPDATE set_guilds SET playing = '1', channel_id = '{ctx.author.voice.channel.id}' WHERE guild_id = '{ctx.guild.id}';",
            False)
        await resume_music(ctx.guild.id, still_playing=False)
        await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('executed');", False)

    except Exception as e:
        await send_message(channel=ctx.channel, author=ctx.author,
                           message="There has been a error.\n"
                                   "For further information contact the support.\n"
                                   "https://discord.gg/Da9haye\n"
                                   f"Your error code is **{utils.on_error('elevator_music()', str(e).strip('.'))}**.",
                           delete=30)
        await utils.execute_sql("INSERT INTO stat_command_music (action) VALUES ('error');", False)


async def elevator_shutdown(ctx):
    try:
        if str(ctx.channel.type) == "private":
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't shutdown:\nThis command doesn't work in DMs.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('fault');", False)
            return

        guild = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {ctx.guild.id};", True)
        if guild[0][1] == 0:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't shutdown:\nI am not playing music.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('fault');", False)
            return

        if ctx.author.voice is None:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't shutdown:\nYou are not in a voice channel.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('fault');", False)
            return

        if ctx.author.voice.channel.id != guild[0][2]:
            await send_message(channel=ctx.channel, author=ctx.author,
                               message="Can't shutdown:\nYou are not in my voice channel.", delete=10)
            await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('fault');", False)
            return

        await send_message(channel=ctx.channel, author=ctx.author, message=":( but ok,\n I am going to stop.",
                           delete=10)
        await utils.execute_sql(
            f"UPDATE set_guilds SET playing = '0', channel_id = NULL WHERE guild_id = '{ctx.guild.id}';", False)
        await stop_music(ctx.guild.id)
        await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('executed');", False)

    except Exception as e:
        await send_message(channel=ctx.channel, author=ctx.author,
                           message="There has been a error.\n"
                                   "For further information contact the support.\n"
                                   "https://discord.gg/Da9haye\n"
                                   f"Your error code is **{utils.on_error('elevator_shutdown()', str(e).strip('.'))}**.",
                           delete=30)
        await utils.execute_sql("INSERT INTO stat_command_shutdown (action) VALUES ('error');", False)


def after_music(error, guild_id):
    if error is not None:
        utils.on_error("after_music()", f"Error on guild '{str(guild_id)}', {str(error).strip('.')}.")
    asyncio.run_coroutine_threadsafe(resume_music(guild_id), get_bot().loop).result()


async def resume_music(guild_id, still_playing=True):
    row = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {guild_id};", True)
    guild = get_bot().get_guild(row[0][0])
    channel = get_bot().get_channel(row[0][2])

    try:
        if guild is None or channel is None or channel.permissions_for(guild.me).connect is False:
            await utils.execute_sql(
                f"UPDATE set_guilds SET playing = '0', channel_id = NULL WHERE guild_id = '{guild.id}';", False)
            await stop_music(guild_id)
            return
        else:
            voice = get(get_bot().voice_clients, guild=guild)
            if voice is None or voice.channel != channel:
                await channel.connect()
                voice = get(get_bot().voice_clients, guild=guild)
            if guild.me.voice.self_deaf is False:
                await guild.change_voice_state(channel=channel, self_deaf=True)
            if voice.is_paused():
                voice.resume()
                utils.log("info", f"Resumed playing on guild '{str(guild.id)}' in channel '{str(channel.id)}'.")
                return
            elif not voice.is_playing():
                # ffmpeg_options = {'before_options': '-stream_loop -1'}
                # audio_source = discord.FFmpegPCMAudio(utils.secret.audio_name, **ffmpeg_options)
                audio_source = discord.FFmpegPCMAudio(utils.secret.audio_name)
                voice.play(audio_source, after=lambda error: after_music(error, guild_id))
                voice.source.volume = 0.3
                if still_playing is False:
                    utils.log("info", f"Started playing on guild '{str(guild.id)}' in channel '{str(channel.id)}'.")
                if len(voice.channel.voice_states.keys()) <= 1 and not voice.is_paused():
                    await pause_music(guild_id)

    except Exception as e:
        utils.on_error("resume_music()", f"Error on guild '{str(guild_id)}', {str(e).strip('.')}.")
        return Exception
        # last_error = await utils.execute_sql(
        #     f"SELECT error, last_error FROM set_guilds WHERE guild_id = '{guild.id}';", True)
        # if last_error[0][0] is None:
        #     error_count = 0
        #     error_time = datetime.datetime.min
        # else:
        #     error_count = last_error[0][0]
        #     error_time = last_error[0][1]
        # if int(error_count) > 5:
        #     await utils.execute_sql(
        #         f"UPDATE set_guilds SET playing = '0', channel_id = NULL, error = NULL, last_error = NUll WHERE guild_id = '{guild.id}';",
        #         False)
        #     voice = get(get_bot().voice_clients, guild=guild)
        #     if voice is not None:
        #         await voice.disconnect(force=True)
        #     utils.log("info",
        #               f"Reset playing status of '{str(guild.id)}', after multiple errors.")
        # else:
        #     if (datetime.datetime.now() - error_time) < datetime.timedelta(seconds=120):
        #         await utils.execute_sql(
        #             f"UPDATE set_guilds SET error = {int(error_count + 1)}, last_error = '{utils.get_curr_timestamp()}' WHERE guild_id = '{guild.id}';",
        #             False)
        #     else:
        #         await utils.execute_sql(
        #             f"UPDATE set_guilds SET error = {0}, last_error = '{utils.get_curr_timestamp()}' WHERE guild_id = '{guild.id}';",
        #             False)


async def pause_music(guild_id):
    row = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {guild_id};", True)
    guild = get_bot().get_guild(row[0][0])
    channel = get_bot().get_channel(row[0][2])

    try:
        voice = get(get_bot().voice_clients, guild=guild)
        if voice is None or not voice.is_playing() or voice.is_paused():
            return
        voice.pause()
        utils.log("info", f"Paused playing on guild '{str(guild.id)}' in channel '{str(channel.id)}'.")
    except Exception as e:
        utils.on_error("pause_music()", f"Error on guild '{str(guild_id)}', {str(e).strip('.')}.")
        return Exception


async def stop_music(guild_id):
    row = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {guild_id};", True)
    guild = get_bot().get_guild(row[0][0])
    channel = get_bot().get_channel(row[0][2])

    try:
        voice = get(get_bot().voice_clients, guild=guild)
        if voice is not None:
            if voice.is_playing():
                voice.stop()
            await voice.disconnect(force=True)
            utils.log("info", f"Stopped playing on guild '{str(guild.id)}'.")
    except Exception as e:
        utils.on_error("stop_music()", f"Error on guild '{str(guild_id)}', {str(e).strip('.')}.")
        return Exception


async def update_guild_count():
    guild_count = len(get_bot().guilds)
    guild_count_db = len(
        await utils.execute_sql("SELECT * FROM stat_bot_guilds WHERE action = 'add';", True)) - len(
        await utils.execute_sql("SELECT * FROM stat_bot_guilds WHERE action = 'remove';", True))
    if guild_count < guild_count_db:
        diff = guild_count_db - guild_count
        for count in range(diff):
            await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('remove');", False)
    elif guild_count > guild_count_db:
        diff = guild_count - guild_count_db
        for count in range(diff):
            await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('add');", False)

    if utils.secret.secret == "master":
        sites = utils.secret.lists

        async def request(site, session):
            try:
                async with session.post(url=site[3] % str(get_bot().user.id),
                                        headers={'Authorization': site[4], 'Content-Type': 'application/json'},
                                        json={site[5]: len(get_bot().guilds)}) as response:
                    if response is None:
                        site[7] = "Error"
                    elif response.status == site[6]:
                        if str(await response.text()).startswith('{"error":true,'):
                            site[7] = textwrap.shorten(str(await response.text()), width=50)
                        else:
                            site[7] = "Ok"
                    else:
                        site[7] = textwrap.shorten(str(response.status), width=50)

            except Exception as e:
                site[7] = "Error"
                utils.on_error("update_guild_count()", str(e).strip('.'))

        async with aiohttp.ClientSession() as session1:
            await asyncio.gather(*[asyncio.ensure_future(request(site, session1)) for site in sites])

        status = ""
        for site in sites:
            status += site[2] + ": " + site[7]
            if sites.index(site) != sites.index(sites[-1]):
                status += ", "
            else:
                status += "."

        utils.log("info", f"Currently serving {str(guild_count)} guilds.", f"Updated " + status)


async def send_message(channel, author=None, message=None, embed=None, delete=None):
    try:
        if not str(channel.type) == "private":
            if channel.permissions_for(channel.guild.me).send_messages is False:
                if author is not None:
                    try:
                        await author.send(
                            content="Can't sent to text channel '" + str(
                                channel) + "', so I am telling you here...\n" + message,
                            delete_after=delete)
                    except Exception as e:
                        utils.on_error("send_message(), send", f"Error to user '{str(author)}', {str(e).strip('.')}.")
                return
        await channel.trigger_typing()
        await asyncio.sleep(1)
        await channel.send(content=message, embed=embed, delete_after=delete)
    except Exception as e:
        utils.on_error("send_message(), outer", str(e).strip('.'))


try:
    get_bot().run(utils.secret.bot_token, bot=True, reconnect=False)
except Exception as e:
    utils.on_error("run()", str(e).strip('.'))

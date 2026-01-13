import asyncio
import logging
import aiohttp
import assets
import datetime
import discord
import io
import os
import textwrap
import threading
import traceback
import utils
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

# TODO fix cant start new thread -> shards?
#
# TODO move to using only one music process
# TODO use different music files, pick random, licensed, easter eggs
#
# TODO website, statistics wip and leaderboard
# TODO move command - own channel which moves down and up (this one moves users form one to another channel, plays fitting sounds (door closes/opens, moving, elevator music) at the end it moves to its saved channel)
#
# TODO donate command

version = "v2.0.3"

activity = discord.Activity(name="/elevatorinfo", type=discord.ActivityType.listening)

bot = discord.Client(
    activity=activity,
    intents=discord.Intents.default()
)

# TODO integrate discord.py logging
discord.utils.setup_logging(level=logging.INFO, root=False)

bot.tree = app_commands.CommandTree(bot)

last_profile_update = datetime.datetime.min


async def main():
    async with bot:
        await bot.start(os.environ['BOT_TOKEN'])


@bot.event
async def on_ready():
    utils.log("info", f"Logged in as {str(bot.user)}, on version {version}, in session {str(utils.session_id)}.")

    await bot.change_presence(activity=activity)

    for guild in bot.guilds:
        await utils.execute_sql(f"INSERT IGNORE INTO set_guilds VALUES ('{guild.id}', '0', NULL, NULL)", False)
    await update_guild_count()

    playing_guilds = await utils.execute_sql("SELECT guild_id FROM set_guilds WHERE playing = 1;", True)
    for row in playing_guilds:
        guild = bot.get_guild(row[0])
        if guild is None:
            guild = discord.Object(id=row[0], type=discord.Guild)
            await stop_music(guild)
        else:
            await play_music(guild, still_playing=False)
    while True:
        await utils.execute_sql("", False)
        await asyncio.sleep(60)


@bot.event
async def on_guild_join(guild):
    await utils.execute_sql(
        f"INSERT INTO set_guilds VALUES ('{guild.id}', '0', NULL, NULL) ON DUPLICATE KEY UPDATE playing = '0', channel_id = NULL, playing_since = NULL",
        False)
    await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('add');", False)
    utils.log("info", f"Guild join {str(guild.id)}.")
    await update_guild_count()
    await bot.change_presence(activity=activity)


@bot.event
async def on_guild_remove(guild):
    error_guilds = [814476583347814430]
    if guild.id in error_guilds:
        utils.log("info", f"Guild leave skipped for {str(guild.id)}.")
        return
    await stop_music(guild)
    await utils.execute_sql("INSERT INTO stat_bot_guilds (action) VALUES ('remove');", False)
    utils.log("info", f"Guild leave {str(guild.id)}.")
    await update_guild_count()
    await bot.change_presence(activity=activity)


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if member.id == bot.user.id:
            utils.log("info", f"Active threads: {threading.active_count()}.")
            if before.channel is None:
                if member.guild.me.voice is not None and not member.guild.me.voice.self_deaf:
                    await member.guild.change_voice_state(channel=after.channel, self_deaf=True)
                await resume_music(member.guild)
                utils.log("info", f"Connect on guild {str(member.guild.id)}.")
                return
            if after.channel is None:
                await stop_music(member.guild)
                utils.log("info", f"Disconnect on guild {str(member.guild.id)}.")
                return
            else:
                if after.channel.permissions_for(member).connect is False:
                    await play_music(member.guild, before.channel)
                    return
            if after.channel.id != before.channel.id:
                await utils.execute_sql(f"UPDATE set_guilds SET channel_id = '{after.channel.id}' WHERE guild_id = '{member.guild.id}';", False)
                await pause_music(member.guild)

        voice = member.guild.voice_client
        if voice is not None:
            if voice.is_paused() and (len(voice.channel.voice_states.keys()) > 1):
                await resume_music(member.guild)
            if voice.is_playing() and (len(voice.channel.voice_states.keys()) <= 1):
                await pause_music(member.guild)
    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        utils.on_error("on_voice_state_update()", *trace)


@bot.tree.command(name="elevatorinfo", description="Shows infos and help regarding the bot fahrstuhlmusik.")
async def elevator_info(interaction: discord.Interaction):
    status = "ongoing"
    try:
        if str(interaction.channel.type) == "private":
            color = discord.Colour.random()
        else:
            color = interaction.channel.guild.me.color.value

        embed = discord.Embed(colour=color)
        embed.set_thumbnail(url=bot.user.avatar.url)
        commands = await bot.tree.fetch_commands()
        embed.add_field(name="", value=assets.info_message[0], inline=False)
        for command in range(len(assets.info_message) - 2):
            embed.add_field(name=commands[command].mention, value=assets.info_message[command + 1])
        guilds = str(len(bot.guilds))
        start = str(int(utils.get_start_timestamp(raw=True).timestamp()))
        session = str(utils.session_id)
        embed.add_field(name="", value=assets.info_message[-1] % (guilds, version, start, session), inline=False)
        embed.add_field(name="", value=f"[{bot.user.display_name} in the web](https://bots.muffintime.tk/{bot.user.display_name.replace(' ', '%20')}/)", inline=False)

        await send_message(interaction, embed=embed)
        utils.log("info", f"Successfully executed elevatorinfo() on {interaction.guild.id if interaction.guild else 0}.")
        status = "success"
    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        await send_error(interaction, error=utils.on_error('elevator_info()', *trace))
        utils.log("info", f"Thrown an error while executing elevatorinfo() on {interaction.guild.id if interaction.guild else 0}.")
        status = "error"

    await utils.stat_bot_commands("elevatorinfo", status, interaction.user.id, interaction.guild.id if interaction.guild else 0)


@bot.tree.command(name="elevatorreview", description="You can rate and review the bot on different sites.")
async def elevator_review(interaction: discord.Interaction):
    status = "ongoing"
    try:
        if str(interaction.channel.type) == "private":
            color = discord.Colour.random()
        else:
            color = interaction.channel.guild.me.color.value

        embed = discord.Embed(description="Here you can review this bot and vote for it", colour=color)
        embed.set_thumbnail(url=bot.user.avatar.url)
        for site in assets.list_sites:
            embed.add_field(name=site[0], value=site[1], inline=False)
        embed.add_field(name="", value=f"[{bot.user.display_name} in the web](https://bots.muffintime.tk/{bot.user.display_name}/)", inline=False)

        await send_message(interaction, embed=embed)
        utils.log("info", f"Successfully executed elevatorreview() on {interaction.guild.id if interaction.guild else 0}.")
        status = "success"
    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        await send_error(interaction, error=utils.on_error('elevator_review()', *trace))
        utils.log("info", f"Thrown an error while executing elevatorreview() on {interaction.guild.id if interaction.guild else 0}.")
        status = "error"

    await utils.stat_bot_commands("elevatorreview", status, interaction.user.id, interaction.guild.id if interaction.guild else 0)


@bot.tree.command(name="elevatormusic", description="Starts playing elevator music in your channel.")
async def elevator_music_command(interaction: discord.Interaction):
    status = await elevator_music(interaction)
    await utils.stat_bot_commands("elevatormusic", status, interaction.user.id, interaction.guild.id if interaction.guild else 0)


@bot.tree.command(name="fahrstuhlmusik", description="Also starts playing elevator music in your channel. :)")
async def fahrstuhlmusik_command(interaction: discord.Interaction):
    status = await elevator_music(interaction)
    await utils.stat_bot_commands("fahrstuhlmusik", status, interaction.user.id, interaction.guild.id if interaction.guild else 0)


async def elevator_music(interaction: discord.Interaction):
    try:
        if str(interaction.channel.type) == "private":
            await send_message(interaction, message=f"**Can't play music** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nThis command doesn't work in DMs.", delete=10)
            return "fault"

        if interaction.user.voice is None:
            await send_message(interaction, message=f"**Can't play music** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nYou are not in a voice channel.", delete=10)
            return "fault"

        if interaction.user.voice.channel.permissions_for(interaction.user.guild.me).connect is False:
            await send_message(interaction, message=f"**Can't play music** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nCan't access your voice channel.", delete=10)
            return "fault"

        guild = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {interaction.guild.id if interaction.guild else 0};", True)
        if guild[0][1] == 1:
            if interaction.guild.voice_client is None or not interaction.guild.voice_client.is_connected() or not interaction.guild.voice_client.is_playing():
                await send_message(interaction, message=f"**On command** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nPure relaxation.", delete=10)
                await play_music(interaction.guild)
                utils.log("info", f"Successfully executed elevatormusic() on {interaction.guild.id if interaction.guild else 0}.")
                return "success"
            else:
                await send_message(interaction, message=f"**Can't play music** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nAlready playing music.", delete=10)
                return "fault"

        await send_message(interaction, message=f"**On command** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nPure relaxation.", delete=10)
        await play_music(interaction.guild, interaction.user.voice.channel, still_playing=False)
        utils.log("info", f"Successfully executed elevatormusic() on {interaction.guild.id if interaction.guild else 0}.")
        return "success"

    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        await send_error(interaction, error=utils.on_error('elevator_music()', *trace))
        utils.log("info", f"Thrown an error while executing elevatormusic() on {interaction.guild.id if interaction.guild else 0}.")
        return "error"


@bot.tree.command(name="elevatorshutdown", description="The bot stops playing music.")
async def elevator_shutdown(interaction: discord.Interaction):
    status = "ongoing"
    try:
        if str(interaction.channel.type) == "private":
            await send_message(interaction, message=f"**Can't shutdown** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nThis command doesn't work in DMs.", delete=10)
            status = "fault"

        guild = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {interaction.guild.id if interaction.guild else 0};", True)
        if status != "fault" and guild[0][1] == 0:
            await send_message(interaction, message=f"**Can't shutdown** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nI am not playing music.", delete=10)
            status = "fault"

        if status != "fault" and interaction.user.voice is None:
            await send_message(interaction, message=f"**Can't shutdown** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nYou are not in a voice channel.", delete=10)
            status = "fault"

        if status != "fault" and interaction.user.voice.channel.id != guild[0][2]:
            await send_message(interaction, message=f"**Can't shutdown** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nYou are not in my voice channel.", delete=10)
            status = "fault"

        if status != "fault":
            await send_message(interaction, message=f"**On command** - Dismissed <t:{int(datetime.datetime.now().timestamp()) + 10}:R>\nNo more relaxation for you.", delete=10)
            await stop_music(interaction.guild)
            utils.log("info", f"Successfully executed elevatorshutdown() on {interaction.guild.id if interaction.guild else 0}.")
            status = "success"

    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        await send_error(interaction, error=utils.on_error('elevator_shutdown()', *trace))
        utils.log("info", f"Thrown an error while executing elevatorshutdown() on {interaction.guild.id if interaction.guild else 0}.")
        status = "fault"

    await utils.stat_bot_commands("elevatorshutdown", status, interaction.user.id, interaction.guild.id if interaction.guild else 0)


def after_music(error, guild):
    if error is not None:
        utils.on_error("after_music()", f"Error on {str(guild.id)}, {str(error).strip('.')}.")
    asyncio.run_coroutine_threadsafe(play_music(guild), bot.loop).result()


async def play_music(guild, channel=None, still_playing=True):
    if channel:
        if still_playing:
            await utils.execute_sql(f"UPDATE set_guilds SET playing = '1', channel_id = '{channel.id}' WHERE guild_id = '{guild.id}';",
                                    False)
        else:
            await utils.execute_sql(f"UPDATE set_guilds SET playing = '1', channel_id = '{channel.id}', playing_since = '{datetime.datetime.now().replace(microsecond=0)}' WHERE guild_id = '{guild.id}';", False)
    else:
        row = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {guild.id};", True)
        channel = bot.get_channel(row[0][2])

    utils.log("info", f"Active threads: {threading.active_count()}.")

    if channel is None or channel.permissions_for(guild.me).connect is False:
        await stop_music(guild)
        return
    voice = guild.voice_client
    if voice is None:
        voice = await channel.connect(self_deaf=True)
    # voice could be currently trying to connect, because of a prior disconnect
    if not voice.is_connected():
        await voice.disconnect(force=True)
        voice = await channel.connect(self_deaf=True)
    if voice.channel != channel:
        await voice.move_to(channel)
    if voice.is_connected() and not voice.is_playing():
        # ffmpeg_options = {'before_options': '-stream_loop -1'}
        # audio_source = discord.FFmpegPCMAudio(f"audio_{os.environ['BOT_ENVIR']}.mp3", **ffmpeg_options)
        audio_source = discord.FFmpegPCMAudio(f"audio_{os.environ['BOT_ENVIR']}.mp3")
        voice.play(audio_source, after=lambda error: after_music(error, guild))
        utils.log("info", f"Playing file on guild {guild.id}, active threads: {threading.active_count()}.")
        voice.source.volume = 0.3
        if not still_playing:
            utils.log("info", f"Started playing on guild {str(guild.id)} in channel {str(channel.id)}.")
        if len(channel.voice_states.keys()) <= 1 and not voice.is_paused():
            await pause_music(guild)


async def resume_music(guild):
    voice = guild.voice_client
    if voice is not None and voice.is_paused():
        voice.resume()
        utils.log("info", f"Resumed playing on guild {str(guild.id)} in channel {str(voice.channel.id)}.")


async def pause_music(guild):
    voice = guild.voice_client
    if voice is not None and not voice.is_paused():
        voice.pause()
        utils.log("info", f"Paused playing on guild {str(guild.id)} in channel {str(voice.channel.id)}.")


async def stop_music(guild):
    row = await utils.execute_sql(f"SELECT * FROM set_guilds WHERE guild_id = {guild.id};", True)
    channel = bot.get_channel(row[0][2])

    await utils.execute_sql(f"UPDATE set_guilds SET playing = '0', channel_id = NULL, playing_since = NULL WHERE guild_id = '{guild.id}';", False)
    voice = guild.voice_client
    if voice is not None:
        if voice.is_playing():
            voice.stop()
        await voice.disconnect(force=True)
        voice.cleanup()
    if channel is not None:
        utils.log("info", f"Stopped playing on guild {str(guild.id)}.")


async def update_profile_picture():
    global last_profile_update
    if datetime.datetime.now() - last_profile_update > datetime.timedelta(days=1):
        img = Image.open(f"fahrstuhlmusik_{os.environ['BOT_ENVIR']}.png")

        # TODO Download don't distribute
        font = ImageFont.truetype("bahnschrift.ttf", size=80)

        font.set_variation_by_name("Bold SemiCondensed")

        draw_img = ImageDraw.Draw(img)

        if os.environ['BOT_ENVIR'] == "production":
            fill = (255, 34, 65)
        else:
            fill = (150, 150, 150)

        draw_img.text(xy=(565, 92), font=font, text=str(len(bot.guilds)), anchor="mm", fill=fill)

        last_profile_update = datetime.datetime.now()

        io_img = io.BytesIO()
        img.save(io_img, format='PNG')

        await bot.user.edit(avatar=io_img.getvalue())

        utils.log("info", "Updated profile picture.")


async def update_guild_count():
    try:
        guild_count = len(bot.guilds)
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

        if os.environ['BOT_ENVIR'] == "production":
            sites = assets.list_sites

            i = 0
            while i < len(assets.list_sites):
                sites[i].append(os.environ['BOT_LIST_TOKENS'].split("|")[i])
                i += 1

            async def request(site, session):
                try:
                    async with session.post(url=site[2] % str(bot.user.id),
                                            headers={'Authorization': site[4], 'Content-Type': 'application/json'},
                                            json={site[3]: len(bot.guilds)}) as response:
                        if response is None:
                            site.append("request failed: No response")
                        elif str(response.status).startswith("20"):
                            if str(await response.text()).startswith('{"error":true,'):
                                site.append("request failed: " + textwrap.shorten(str(await response.text()), width=50))
                            else:
                                site.append("request success")
                        else:
                            site.append("request failed: " + textwrap.shorten(str(response.status), width=50))

                except Exception:
                    site.append("request failed: Exception")
                    trace = traceback.format_exc().rstrip("\n").split("\n")
                    utils.on_error("request()", *trace)

            async with aiohttp.ClientSession() as session1:
                await asyncio.gather(*[asyncio.ensure_future(request(site, session1)) for site in sites], return_exceptions=True)

            status = []
            for site in sites:
                if site[-1].startswith("request failed"):
                    status.append(site[0] + " " + site[-1].strip(".") + ".")

            status.insert(0, f"Updated {len(sites) - len(status)}/{len(sites)} sites.")

            utils.log("info", f"Currently serving {str(guild_count)} guilds.", *status)

        await update_profile_picture()

    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        utils.on_error("update_guild_count()", *trace)


async def send_message(interaction, message=None, embed=None, delete=None):
    if not interaction.response.is_done():
        await interaction.response.send_message(content=message, embed=embed, delete_after=delete)
    else:
        await interaction.channel.send(content=message, embed=embed, delete_after=delete)


async def send_error(interaction, error, delete=None):
    message = "There has been a error.\n"\
              "For further information contact the support.\n"\
              "https://discord.gg/Da9haye\n"\
              f"Your error code is **{error}**."
    await send_message(interaction, message=message, delete=delete)

asyncio.run(main())

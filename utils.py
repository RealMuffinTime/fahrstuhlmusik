import asyncio
import datetime
import mariadb
import os
import shortuuid
import traceback


db_connection = None
start_timestamp = None
session_id = None


def get_start_timestamp(raw=False):
    global start_timestamp
    if start_timestamp is None:
        start_timestamp = datetime.datetime.now().replace(microsecond=0)
    if raw:
        return start_timestamp
    return str(start_timestamp)


def get_curr_timestamp(raw=False):
    if raw:
        return datetime.datetime.now()
    return str(datetime.datetime.now().replace(microsecond=0))


def on_error(error_type, *messages):
    error_uuid = str(shortuuid.uuid())
    log("error", error_type + ", " + error_uuid + ":", *messages)
    return error_uuid


async def stat_bot_commands(command, status, user_id, guild_id):
    await execute_sql(f"INSERT INTO stat_bot_commands (command, status, user_id, guild_id) VALUES ('{command}', '{status}', '{user_id}', '{guild_id}')", False)


def log(status, *messages):
    for message in messages:
        try:
            status_prefix = None
            if status == "error":
                status_prefix = "[%s ERROR] "
            if status == "info":
                status_prefix = "[%s INFO] "
            print(status_prefix % get_curr_timestamp() + message)
            log_file = open(f"log/{os.environ['BOT_ENVIR']}_{get_start_timestamp().replace(' ', '_').replace(':', '-')}.txt",
                            "a", encoding="utf8")
            log_file.write(status_prefix % get_curr_timestamp() + message + "\n")
            log_file.close()
        except Exception:
            status_prefix = "[%s ERROR] " % get_curr_timestamp()
            print(f"{status_prefix}There is an error in an error reporter, HAHA, how ironic.")
            for trace in traceback.format_exc().rstrip("\n").split("\n"):
                print(f"{status_prefix}{trace}")


def get_db_connection():
    global db_connection
    if db_connection is None:
        try:
            db_connection = mariadb.connect(
                user=os.environ['BOT_DATABASE_USER'],
                password=os.environ['BOT_DATABASE_PASS'],
                host=os.environ['BOT_DATABASE_HOST'],
                port=int(os.environ['BOT_DATABASE_PORT'])
            )
            db_connection.auto_reconnect = True
        except Exception:
            trace = traceback.format_exc().rstrip("\n").split("\n")
            on_error("get_db_connection()", *trace)
    return db_connection


async def execute_sql(sql_term, fetch):
    try:
        cursor = get_db_connection().cursor(buffered=True)
        cursor.execute(f"USE `{os.environ['BOT_DATABASE_NAME']}`")
        if session_id is not None:
            cursor.execute(f"SELECT last_heartbeat FROM stat_bot_online WHERE id = '{session_id}'")
            last_heartbeat = cursor.fetchall()[0][0]

            if (get_curr_timestamp(True) - last_heartbeat).seconds >= 60:
                cursor.execute(f"UPDATE stat_bot_online SET last_heartbeat = '{get_curr_timestamp()}' WHERE id = '{session_id}'")

        if sql_term != "":
            cursor.execute(sql_term)
        get_db_connection().commit()
        if sql_term != "":
            if cursor.rowcount > 0 and fetch is True:
                return cursor.fetchall()
            if cursor.rowcount == 0 and fetch is True:
                return []
    except Exception:
        trace = traceback.format_exc().rstrip("\n").split("\n")
        on_error(f"execute_sql(), fetch: {fetch}", f"{sql_term}", *trace)
        return []


async def startup():
    global session_id
    await execute_sql(f"INSERT INTO stat_bot_online (startup, last_heartbeat) VALUES ('{get_start_timestamp()}', '{get_curr_timestamp()}')", False)
    session_id = (await execute_sql("SELECT * FROM stat_bot_online ORDER BY id DESC LIMIT 1", True))[0][0]

if not os.path.exists("log"):
    os.makedirs("log")

asyncio.run(startup())

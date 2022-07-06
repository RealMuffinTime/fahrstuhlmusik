import datetime
import mariadb
import shortuuid
import secret_dev as secret

start_timestamp = None
db_connection = None

# TODO scan for secret file, select available


def get_start_timestamp():
    global start_timestamp
    if start_timestamp is None:
        start_timestamp = str(datetime.datetime.now().replace(microsecond=0))
    return start_timestamp


def get_curr_timestamp(raw=False):
    if raw:
        return datetime.datetime.now()
    return str(datetime.datetime.now().replace(microsecond=0))


def on_error(error_type, *messages):
    error_uuid = str(shortuuid.uuid())
    log("error", error_type + ", " + error_uuid + ":", *messages)
    return error_uuid


def log(status, *messages):
    for message in messages:
        try:
            status_prefix = None
            if status == "error":
                status_prefix = "[%s ERROR] "
            if status == "info":
                status_prefix = "[%s INFO] "
            print(status_prefix % get_curr_timestamp() + message)
            log_file = open(f"log/{secret.secret}_{get_start_timestamp().replace(' ', '_').replace(':', '-')}.txt",
                            "a", encoding="utf8")
            log_file.write(status_prefix % get_curr_timestamp() + message + "\n")
            log_file.close()
        except Exception as e:
            status_prefix = "[%s ERROR] " % get_curr_timestamp()
            print(f"{status_prefix}There is an error in an error reporter, HAHA, how ironic, {str(e).strip('.')}")


def get_db_connection():
    global db_connection
    if db_connection is None:
        try:
            db_connection = mariadb.connect(
                user=secret.database_user,
                password=secret.database_pass,
                host=secret.database_host,
                port=secret.database_port
            )
        except Exception as e:
            on_error("get_db_connection()", str(e).strip('.'))
    return db_connection


async def execute_sql(sql_term, fetch):
    try:
        cursor = get_db_connection().cursor(buffered=True)
        cursor.execute(f"USE `{secret.database_name}`")
        cursor.execute("SELECT * FROM stat_bot_online ORDER BY id DESC LIMIT 1")
        temp_fetch = cursor.fetchall()

        def restart():
            cursor.execute("INSERT INTO stat_bot_online (action) VALUES ('startup');")
            cursor.execute("INSERT INTO stat_bot_online (action) VALUES ('last seen');")

        if temp_fetch:
            if temp_fetch[0][1] == 'last seen' and (get_curr_timestamp(True) - temp_fetch[0][2]).seconds < 60:
                cursor.execute(
                    f"UPDATE stat_bot_online SET timestamp = '{get_curr_timestamp()}' WHERE id = '{temp_fetch[0][0]}';")
            else:
                restart()
        else:
            restart()

        cursor.execute(sql_term)
        get_db_connection().commit()
        if cursor.rowcount > 0 and fetch is True:
            return cursor.fetchall()
        if cursor.rowcount == 0 and fetch is True:
            return []
    except Exception as e:
        on_error(f"execute_sql(), fetch: {fetch}", f"{sql_term}", str(e).strip('.'))
        return []

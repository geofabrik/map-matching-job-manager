#! /usr/bin/env python3

import os
import logging
import psycopg2
import argparse
import time
import json


def delete_database_entries():
    with psycopg2.connect(configuration["postgres_connect"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM jobs WHERE
                             created_at < current_timestamp - interval '%s hours'
                             OR started_at < current_timestamp - interval '%s hours'
                             OR finished_at < current_timestamp - interval '%s hours'""",
                        (args.max_age, args.max_age, args.max_age)
            )
            logging.info("{} entries deleted from database".format(cur.rowcount))


def delete_old_files(directory):
    now = time.time()
    count = 0
    file_list = os.listdir(directory)
    for f in file_list:
        fullpath = os.path.join(directory, f)
        if not os.path.isfile(fullpath):
            continue
        if os.stat(fullpath).st_mtime < (now - args.max_age * 3600):
            os.remove(fullpath)
            logging.debug("deleted file {}".format(fullpath))
            count += 1
    logging.info("deleted {} of {} files in {}".format(count, len(file_list), directory))


parser = argparse.ArgumentParser(description="Delete old jobs")
parser.add_argument("-c", "--configuration", help="configuration file")
parser.add_argument("-m", "--max-age", help="maximum age for jobs (hours)", default=48, type=int)
parser.add_argument("-l", "--log-level", help="log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)", default="DEBUG", type=str)
args = parser.parse_args()

# log level
numeric_log_level = getattr(logging, args.log_level.upper())
if not isinstance(numeric_log_level, int):
    raise ValueError("Invalid log level {}".format(args.log_level.upper()))
logging.basicConfig(level=numeric_log_level)
logger = logging.getLogger("job_cleanup")

with open(args.configuration, "r") as config_file:
    configuration = json.load(config_file)

delete_database_entries()
delete_old_files(configuration["input_directory"])
delete_old_files(configuration["output_directory"])

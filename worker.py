#! /usr/bin/env python3

import sys
import os.path
import time
import argparse
import json
import psycopg2
import psycopg2.extras
import logging
import urllib.parse
import requests
import shapefile
import csv
import zipfile
from io import StringIO, BytesIO
from job_manager.job_list import JobList
from job_manager.job import Job
from job_manager.job_manager_api import JobManagerAPI


def build_shapefile(job, text, output_path):
    logger.debug("building shape file")
    # parse csv
    f = StringIO(text)
    reader = csv.reader(f, delimiter=';')
    row_count = 0
    lat_col = -1
    lon_col = -1
    col_count = 0
    points = []
    for row in reader:
        if row_count == 0:
            col_count = len(row)
            for i in range(0, len(row)):
                if row[i] == "latitude":
                    lat_col = i
                elif row[i] == "longitude":
                    lon_col = i
            row_count += 1
            continue
        if lat_col < 0 or lon_col < 0:
            logger.error("Job {}: Failed to read CSV response, some or all column headings not found".format(job.id))
            return False
        if len(row) < max(lat_col, lon_col) + 1:
            continue
        lat = row[int(lat_col)]
        lon = row[(lon_col)]
        points.append([float(lon), float(lat)])
    if len(points) < 2:
        logger.error("Job {}: too few points for polyline".format(job.id))
        return False
    w = shapefile.Writer(shapeType=shapefile.POLYLINE)
    w.line(parts=[points])
    w.field("ID", "N")
    w.record(1)
    # write shape file
    shp_buffer = BytesIO()
    shx_buffer = BytesIO()
    dbf_buffer = BytesIO()
    prj_str = """GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]"""
    cpg_str = "UTF-8"
    w.save(None, shp_buffer, shx_buffer, dbf_buffer)
    # build ZIP file
    filename_wo_suffix = "{}_{}".format(job.id, job.name)
    logger.debug("writing ZIP file to {}".format(output_path))
    zip_file = zipfile.ZipFile(output_path, "w")
    zip_file.writestr("{}.shp".format(filename_wo_suffix), shp_buffer.getvalue())
    zip_file.writestr("{}.shx".format(filename_wo_suffix), shx_buffer.getvalue())
    zip_file.writestr("{}.dbf".format(filename_wo_suffix), dbf_buffer.getvalue())
    zip_file.writestr("{}.prj".format(filename_wo_suffix), prj_str.encode("ascii"))
    zip_file.writestr("{}.cpg".format(filename_wo_suffix), cpg_str.encode("ascii"))
    zip_file.close()
    return True


def process_response(job, params, r):
    output_format = params.get("type", ["gpx"])[0]
    if output_format == "shp":
        output_format = "zip"
    # save file
    output_file = "{}_{}.{}".format(job.id, JobManagerAPI.sanatize_name(job.name), output_format)
    output_path = os.path.join(configuration["output_directory"], output_file)
    if output_format == "zip":
        build_shapefile(job, r.text, output_path)
    else: 
        with open(output_path, "wb") as outfile:
            outfile.write(r.content)
    job.download_path = "{}/{}".format(configuration["download_path_prefix"], output_file)
    return True


def build_query_string(params_dict):
    items = []
    for k, v in params_dict.items():
        if k == "type" and v[0] == "shp":
            items.append("type=csv")
        items.append("{}={}".format(k, v[0]))
    return "&".join(items)


def run_job(job):
    logger.debug("Start processing of job {}".format(job.id))
    params = urllib.parse.parse_qs(job.query_params)
    headers = {}
    try:
        input_type = params["input_type"][0]
    except KeyError:
        logger.error("Processing of job {} failed, missing parameter 'input_type'.".format(job.id))
        return False
    if input_type == "csv":
        headers["Content-type"] = "text/csv"
    elif input_type == "gpx":
        headers["Content-type"] = "application/gpx+xml"
    # read data
    input_path = os.path.join(configuration["input_directory"], "job_{}_{}.{}".format(job.id, job.name, input_type))
    try:
        with open(input_path, "rb") as infile:
            data = infile.read()
    except:
        return False
    try:
        url = "{}?{}".format(configuration["api_url"], build_query_string(params))
        r = requests.post(url, data=data, headers=headers, timeout=300)
        logger.debug("Processing response of job {}".format(job.id))
        if r.status_code == 200:
            return process_response(job, params, r)
        else:
            logger.error("Job {} failed with status code {} and error message {}".format(job.id, r.status_code, r.text))
            save_error(job, r.text)
            return False
    except requests.exceptions.Timeout as err:
        logger.error("Job {} failed: {}".format(job.id, err))
    return False
    


def process_jobs(tasks):
    logger.info("{} jobs to be processed".format(len(tasks)))
    for job in tasks:
        # set start time
        with psycopg2.connect(configuration["postgres_connect"]) as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE jobs SET started_at = current_timestamp, status = 'running' WHERE id = %s", (job.id,))
        reason = None
        try:
            success = run_job(job)
        except Exception as err:
            logger.exception(err)
            success = False
            reason = err
        with psycopg2.connect(configuration["postgres_connect"]) as connection:
            with connection.cursor() as cursor:
                if success and job.download_path is not None:
                    cursor.execute("UPDATE jobs SET finished_at = current_timestamp, status = 'finished', download_path = %s WHERE id = %s", (job.download_path, job.id))
                    logger.debug("Processing of job {} successfully completed.".format(job.id))
                else:
                    cursor.execute("UPDATE jobs SET finished_at = current_timestamp, status = 'failed' WHERE id = %s", (job.id,))
                    logger.error("Processing of job {} successfully failed: {}".format(job.id, reason))


def query_jobs():
    logger.debug("querying jobs database")
    try:
        pg_connect_str = configuration["postgres_connect"]
    except KeyError as err:
        logger.error("Could not find \"postgres_connect\" in the configuration file {}".format(args.configuration))
        exit(1)
    results = []
    with psycopg2.connect(pg_connect_str) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT id, name, query_params, input_file FROM jobs WHERE status = 'queued' ORDER BY id")
            results = cursor.fetchall()
    return JobList.create_from_dict_list(results)


parser = argparse.ArgumentParser(description="Process the jobs in the queue.")
parser.add_argument("-c", "--configuration", help="configuration file")
parser.add_argument("-e", "--exit", action="store_true", help="exit after all jobs have been processed", default=False)
parser.add_argument("-l", "--log-level", help="log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)", default="DEBUG", type=str)
args = parser.parse_args()

# log level
numeric_log_level = getattr(logging, args.log_level.upper())
if not isinstance(numeric_log_level, int):
    raise ValueError("Invalid log level {}".format(args.log_level.upper()))
logging.basicConfig(level=numeric_log_level)
logger = logging.getLogger(__name__)

with open(args.configuration, "r") as config_file:
    configuration = json.load(config_file)

while True:
    jobs = query_jobs()
    if len(jobs) > 0:
        process_jobs(jobs)
        continue
    elif args.exit:
        logger.info("All jobs processed, nothing to do, exiting.")
        exit(0)
    else:
        logger.info("All jobs processed. Next check in 60 seconds.")
        time.sleep(60)

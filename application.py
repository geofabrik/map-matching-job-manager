#! /usr/bin/env python3

import urllib.parse
from job_manager.job_manager_api import JobManagerAPI

job_manager = JobManagerAPI("config.json")

def parse_path(path):
    if path.endswith("/"):
        return path.split("/")[-2]
    return path.split("/")[-1]

def application(environ, start_response):
    path = environ["SCRIPT_NAME"]
    resource = parse_path(path)
    request_method = environ["REQUEST_METHOD"]
    query_params = {}
    if "QUERY_STRING" in environ:
        query_string = environ["QUERY_STRING"]
        query_params = urllib.parse.parse_qs(query_string)

    if "HTTP_X_HTTP_METHOD_OVERRIDE" in environ:
        request_method = environ["HTTP_X_HTTP_METHOD_OVERRIDE"]
    if resource == "job" and request_method == "POST":
        return job_manager.create(environ, start_response, query_string, **query_params)
    if resource == "job" and request_method == "DELETE":
        return job_manager.cancel(environ, start_response, **query_params)
    if resource == "job":
        return job_manager.respond_error("405 Method Not Allowed", "This HTTP method is not supported for this API call.", start_response)
    if resource == "status" and request_method == "GET":
        return job_manager.status(environ, start_response, **query_params)
    if resource == "status":
        return job_manager.respond_error("405 Method Not Allowed", "This HTTP method is not supported for this API call.", start_response)
    response_headers = []
    start_response("404 Not found", response_headers)
    return []

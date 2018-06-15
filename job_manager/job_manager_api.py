import json
import os.path
import urllib.parse
import psycopg2
import psycopg2.extras
from job_manager.job import Job
from job_manager.job_list import JobList
import atexit


class JobManagerAPI:
    def __init__(self):
        self.connection = psycopg2.connect("dbname=jobs")
        self.input_directory = "/tmp/jobs/input"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()

    def create(self, environ, start_response, **kwargs):
        # check necessary parameters
        request_body_size = int(environ.get("CONTENT_LENGTH", 0))
        if request_body_size <= 0:
            return respond_error(400, "request body missing", environ, start_response)
        input_type = kwargs.get("input_type", environ.get("HTTP_Content-type", "csv")).split("/")[-1]
        max_id = -1
        infile = None
        with self.connection.cursor() as cur:
            cur.execute("SELECT max(id) AS max_id FROM jobs")
            max_id = cur.fetchone()[0]
            new_id = max_id + 1
            name = kwargs.get("name", "job_{}".format(new_id))
            infile = "{}.{}".format(os.path.join(self.input_directory, name), input_type)
            query_params = urllib.parse.urlencode(kwargs)
            cur.execute("""INSERT INTO jobs (id, name, status, input_file, query_params) VALUES (%s, %s, 'incomplete', %s, %s);""", (new_id, name, infile, query_params))
            self.connection.commit()
        if infile is not None:
            with open(infile, "wb") as f:
                f.write(environ["wsgi.input"].read(request_body_size))
                cur = self.connection.cursor()
                cur.execute("""UPDATE jobs SET status = 'queued' WHERE id = %s""", (new_id,))
                self.connection.commit()
                cur.close()
        job = Job(**{"id": new_id, "name": name, "status": "queued", "query_params": query_params})
        job_list = JobList.create_from_job(job)
        response = json.dumps(job_list, default=JobList.json_serialize).encode("utf-8")

        response_headers = [("Content-type", "application/json, charset=utf-8"),
                            ("Content-length", str(len(response)))]
        start_response("200 OK", response_headers)
        return [response]

    def _job_query_result(self, start_response, results, **kwargs):
        if len(results) == 0 and "id" in kwargs and len(kwargs["id"]) > 0:
            return respond_error("400 Bad Request", "job {} not found".format(kwargs["id"][0]), start_response)
        elif len(results) == 0:
            return respond_error("400 Bad Request", "no jobs found", start_response)
        job_list = JobList.create_from_dict_list(results)
        response = json.dumps(job_list, default=JobList.json_serialize).encode("utf-8")
        response_headers = [("Content-type", "application/json, charset=utf-8"),
                            ("Content-length", str(len(response)))]
        start_response("200 OK", response_headers)
        return [response]

    def status(self, environ, start_response, **kwargs):
        results = []
        try:
            cur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            if "id" in kwargs:
                cur.execute("SELECT id, name, status, query_params FROM jobs WHERE id = %s", (int(kwargs["id"][0]),))
            else:
                cur.execute("SELECT id, name, status, query_params FROM jobs")
            results = cur.fetchall()
        except ValueError:
            return respond_error("400 Bad Request", "ValueError", start_response)
        finally:
            if cur is not None:
                self.connection.commit()
                cur.close()
        return self._job_query_result(start_response, results, **kwargs)

    def delete(self, environ, start_response, **kwargs):
        if "id" not in kwargs or len(kwargs["id"]) != 1:
            return respond_error("400 Bad Request", "The query string must have exactly one occurrence of the 'id' parameter.", start_response)
        results = []
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.excute("UPDATE jobs SET status = 'cancelled' WHERE id = %s", (int(kwargs["id"][0]),))
                cur.execut("SELECT id, name, status, query_params FROM jobs WHERE id = %s", (int(kwargs["id"][0]),))
                results = cur.fetchall()
        except ValueError:
            return respond_error("400 Bad Request", "ValueError", start_response)
        return self._job_query_result(start_response, results, **kwargs)

import json
import os.path
import urllib.parse
import psycopg2
import psycopg2.extras
from job_manager.job import Job
from job_manager.job_list import JobList


class JobManagerAPI:
    def __init__(self, configuration_path):
        with open(configuration_path, "r") as conf_file:
            configuration = json.load(conf_file)
        self.connection = psycopg2.connect(configuration["postgres_connect"])
        self.input_directory = configuration["input_directory"]
        self.output_directory = configuration["output_directory"] 

    def disconnect(self):
        self.connection.close()

    def sanatize_name(oldname):
        name = oldname
        for i in range(0, len(name)):
            if not name[i].isalnum() and name[i] not in ("-", "_", ","):
                name[i] = "_"
        return name

    def respond_error(self, status, message, start_response):
        message_obj = {"message": message}
        response = json.dumps(message_obj).encode("utf-8")
        response_headers = [("Content-type", "application/json"),
                            ("Content-length", str(len(response)))]
        start_response(status, response_headers)
        return [response]

    def create(self, environ, start_response, query_string, **kwargs):
        # check necessary parameters
        request_body_size = int(environ.get("CONTENT_LENGTH", 0))
        if request_body_size <= 0:
            return self.respond_error("400 Bad Request", "request body or Content-Length header is missing", start_response)
        if "wsgi.input" not in environ:
            return self.respond_error("400 Bad Request", "request body is missing", start_response)
        try:
            input_type = environ["CONTENT_TYPE"]
        except KeyError:
            return self.respond_error("400 Bad Request", "Content-type header is missing", start_response)
        if input_type == "application/gpx+xml":
            input_type = "gpx"
        elif input_type == "text/csv":
            input_type = "csv"
        else:
            return self.respond_error("400 Bad Request", "input format {} is not supported".format(inupt_type), start_response)
        # append type to query string
        query_string += "&input_type={}".format(input_type)
        max_id = -1
        infile = None
        with self.connection.cursor() as cur:
            cur.execute("SELECT max(id) AS max_id FROM jobs")
            max_id = cur.fetchone()[0]
            if max_id is None:
                # no jobs exist in the database
                max_id = 0
            new_id = max_id + 1
            name = "job_{}".format(new_id)
            if "name" in kwargs:
                name = kwargs["name"][0]
            infile = "{}.{}".format(os.path.join(self.input_directory, "job_{}_{}".format(new_id, JobManagerAPI.sanatize_name(name))), input_type)
            query_params = urllib.parse.urlencode(kwargs)
            cur.execute("""INSERT INTO jobs (id, name, status, input_file, query_params, created_at) VALUES (%s, %s, 'incomplete', %s, %s, current_timestamp);""", (new_id, name, infile, query_string))
            self.connection.commit()
        if infile is not None:
            with open(infile, "wb") as f:
                f.write(environ["wsgi.input"].read(request_body_size))
                cur = self.connection.cursor()
                cur.execute("""UPDATE jobs SET status = 'queued' WHERE id = %s""", (new_id,))
                self.connection.commit()
                cur.close()
        job = Job(**{"id": new_id, "name": name, "status": "queued", "query_params": query_params})
        job_list = JobList()
        job_list.add(job)
        response = json.dumps(job_list, default=JobList.json_serialize).encode("utf-8")

        response_headers = [("Content-type", "application/json"),
                            ("Content-length", str(len(response)))]
        start_response("200 OK", response_headers)
        return [response]

    def _job_query_result(self, start_response, results, **kwargs):
        if len(results) == 0 and "id" in kwargs and len(kwargs["id"]) > 0:
            return self.respond_error("400 Bad Request", "job {} not found".format(kwargs["id"][0]), start_response)
        job_list = JobList.create_from_dict_list(results)
        response = json.dumps(job_list, default=JobList.json_serialize).encode("utf-8")
        response_headers = [("Content-type", "application/json"),
                            ("Content-length", str(len(response)))]
        start_response("200 OK", response_headers)
        return [response]

    def status(self, environ, start_response, **kwargs):
        results = []
        try:
            cur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            if "id" in kwargs:
                cur.execute("SELECT id, name, status, query_params, created_at, started_at, finished_at, download_path FROM jobs WHERE id = %s", (int(kwargs["id"][0]),))
            else:
                cur.execute("SELECT id, name, status, query_params, created_at, started_at, finished_at, download_path FROM jobs")
            results = cur.fetchall()
        except ValueError:
            return self.respond_error("400 Bad Request", "ValueError", start_response)
        finally:
            if cur is not None:
                self.connection.commit()
                cur.close()
        return self._job_query_result(start_response, results, **kwargs)

    def cancel(self, environ, start_response, **kwargs):
        if "id" not in kwargs or len(kwargs["id"]) != 1:
            return self.respond_error("400 Bad Request", "The query string must have exactly one occurrence of the 'id' parameter.", start_response)
        results = []
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("UPDATE jobs SET status = 'cancelled' WHERE id = %s AND status = 'queued'", (int(kwargs["id"][0]),))
                failed = (cur.rowcount == 0)
                cur.execute("SELECT id, name, status, query_params, created_at, started_at, finished_at, download_path FROM jobs WHERE id = %s", (int(kwargs["id"][0]),))
                results = cur.fetchall()
                error_message = ""
                if len(results) == 0:
                    error_message = "Job {} not found.".format(job.id)
                if failed:
                    error_message = "The job to be cancelled is not queued (status: {}). Please note that running and finished jobs cannot be cancelled.".format(results[0]["status"])
                if failed or len(results) == 0:
                    self.connection.commit()
                    cur.close()
                    return self.respond_error("403 Forbidden", error_message, start_response)
        except ValueError:
            self.connection.commit()
            cur.close()
            return self.respond_error("400 Bad Request", "ValueError", start_response)
        self.connection.commit()
        cur.close()
        return self._job_query_result(start_response, results, **kwargs)

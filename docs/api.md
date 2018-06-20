The REST API supports two different calls:

* `/status` for the status of a specific or all jobs
* `/job` to create and cancel a job

## Responses

Responses by the API are JSON documents like the following.

```json
{
    "jobs": [
        {
            "created_at": "2018-06-19T19:13:43Z",
            "download_path": "/job-manager/download//1_test1.csv",
            "finished_at": "2018-06-19T19:15:49Z",
            "id": 1,
            "name": "test1",
            "query_params": "&name=test1&gps_accuracy=40&max_visited_nodes=10000&vehicle=tgv_all&fill_gaps=true&type=csv&gpx.route=false&input_type=gpx",
            "started_at": "2018-06-19T19:15:49Z",
            "status": "finished"
        },
        {
            "created_at": "2018-06-20T10:43:44Z",
            "download_path": "/job-manager/download//5_metz-guben-shp.zip",
            "finished_at": null,
            "id": 5,
            "name": "fetz",
            "query_params": "&name=fetz&gps_accuracy=40&max_visited_nodes=10000&vehicle=non_tgv&fill_gaps=true&type=shp&gpx.route=false&input_type=gpx",
            "started_at": null,
            "status": "queued"
        }
    ]
}
```

The objects in the `jobs` array have following properties:

* `created_at`: date and time of creation of the job
* `started_at`: date and time when the processing started (null for queued and
  cancelled jobs)
* `finished_at`: date and time when the processing finished (null for queued,
  cancelled and running jobs, failure time for failed jobs)
* `id`: ID of the job (numeric)
* `name`: name of the job, characters other than `[-a-zA-Z,_0-9]` have been
  replaced by `_`
* `status`: job status, possible values are `incomplete`, `queued`,
  `cancelled`, `running`, `failed`, `finished`
* `query_params`: query string of the POST request, will be forwarded to the
  map matching API (with minor changes)
* `download_path`: path to download the result from (you have to append
  hostname and port in front of it)

## Job status

Input:

* API endpoint: `/status`
* HTTP request: GET
* Support query parameters:
    - `id=<ID>`: the ID of a specific job you are interested in

Response: see section Responses


## Job creation

Input:

* API endpoint: `/job`
* HTTP requests: POST
* Query parameters:
    * `name`: name of the job
    * `type`: `csv` for CSV output, `gpx` for GPX output, `JSON` for JSON
      output and `shp` for a zipped ESRI Shapefile. This parameter is forwarded
      to the map matching API. If the value is `shp`, `csv` will be forwarded and
      converted into a shape file by the job manager.
    * All other query parameters are forwarded to the map matching API.
* The request must have a correct `Content-Length` header.
* The request must have a `Content-Type` header. Permitted values are
  `application/gpx+xml` and `text/csv`.

Output: same as the job status call but only the information about the new job is provided

Errors:

* 400 if `Content-Length` or `Content-type` header or the request body is missing.
* 400 if the provided input format is not supported.


## Job cancellation

Input:

* API endpoint: `/job`
* HTTP requests: DELETE
* If your client HTTP stack does not support the DELETE request, you can fake a
  DELETE request by setting the HTTP header `X_HTTP_METHOD_OVERRIDE` to
  `DELETE`.
* Query parameters:
    * `id`: ID of the job to be deleted

Output: same as the job status call but only the information about the
cancelled job is provided

Errors:

* 400 if the value of `id` could not be parsed as integer
* 403 if the job to be cancelled is processed, finished or already cancelled
* 403 if the job to be cancelled does not exist

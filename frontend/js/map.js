"use strict";

// load available flag encoders
function loadInfos() {
    var xhr = new XMLHttpRequest();
    var url = '/railway_routing/info?type=json';
    xhr.open('GET', url, true);
    xhr.setRequestHeader("Content-type", "application/json");
    xhr.responseType = "json";
    xhr.onreadystatechange = function() {
        if(xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            if (!xhr.response.hasOwnProperty('supported_vehicles')) {
                displayError('The response by the routing API does not list any supported routing profile.');
            }
            var supported_vehicles = xhr.response.supported_vehicles;
            var vehicleSelect = document.getElementById('vehicle');
            supported_vehicles.forEach(function(elem) {
                var optionElement = document.createElement("option");
                optionElement.text = elem;
                vehicleSelect.add(optionElement);
            });
	    vehicleSelect.value = supported_vehicles[0];
        }
    }
    xhr.onerror = function() {
        displayError('Failed to fetch basic info about the routing API.');
    };
    xhr.send();
}

function showRequestResult(success, method, call, response) {
    var msgDiv = document.getElementById('message');
    msgDiv.classList.remove('hideMessage');
    msgDiv.classList.remove('okMessage');
    msgDiv.classList.remove('errorMessage');
    var obj = response;
    if (success && method === 'POST' && call === 'job') {
        msgDiv.innerText = 'Job ' + obj["jobs"][0]["name"] + ' successfully created.';
        msgDiv.classList.add('okMessage');
    } else if (success && method === 'DELETE' && call === 'job') {
        msgDiv.innerText = 'Job ' + obj["jobs"][0]["name"] + ' successfully cancelled.';
        msgDiv.classList.add('okMessage');
    } else if (!success) {
        msgDiv.innerText = 'ERROR: ' + obj["message"];
        msgDiv.classList.add('errorMessage');
    }
}

function sendJobPostRequest(inputData) {
    var inputFormat = document.getElementById('inputFormat').value;
    var xhr = new XMLHttpRequest();
    var url = "/job?";
    url += "&name=" + encodeURIComponent(document.getElementById('jobName').value);
    url += "&gps_accuracy=" + document.getElementById('gps_accuracy').value;
    url += "&max_visited_nodes=" + document.getElementById('maxNodes').value;
    url += "&vehicle=" + encodeURIComponent(document.getElementById('vehicle').value);
    url += "&fill_gaps=" + document.getElementById('fillGaps').checked;
    url += "&type=" + document.getElementById('outputFormat').value;
    url += "&gpx.route=false";
    xhr.open("POST", url, true);
    if (inputFormat === "csv") {
        xhr.setRequestHeader("Content-type", "text/csv");
    } else if (inputFormat === "gpx") {
        xhr.setRequestHeader("Content-type", "application/gpx+xml");
    }
    xhr.responseType = "json";
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            showRequestResult(true, "POST", "job", xhr.response);
            $('#table-jobs').DataTable().ajax.reload();
        } else if (xhr.readyState == XMLHttpRequest.DONE) {
            showRequestResult(false, "POST", "job", xhr.response);
        }
    };
    xhr.send(inputData);
}

function createJob(e) {
    var f = document.getElementById('files').files[0];
    var reader = new FileReader();
    var gpxContent = "";
    reader.onload = function(ev) {
        gpxContent = reader.result;
        sendJobPostRequest(gpxContent);
    }
    reader.readAsText(f);
}

function cancelJob(e) {
    var jobId = e.target.getAttribute('data-job-id');
    var xhr = new XMLHttpRequest();
    var url = "/job?id=" + jobId;
    xhr.open("DELETE", url, true);
    xhr.responseType = "json";
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            showRequestResult(true, "DELETE", "job", xhr.response);
            $('#table-jobs').DataTable().ajax.reload();
        } else if (xhr.readyState == XMLHttpRequest.DONE) {
            showRequestResult(false, "DELETE", "job", xhr.response);
        }
    };
    xhr.send();
}

function registerCancelButtonEvents() {
    [].forEach.call(document.getElementsByClassName('cancelButton'), function(e) {
        e.addEventListener('click', cancelJob);
    });
}

function loadDataTable() {
    var gJobTable = $('#table-jobs').DataTable({
        // data source loaded via AJAX
        ajax: {
            url: "/status",
            dataSrc: "jobs"
        },
        // column definitions
        columns: [
            { data: 'id'},
            {
                data: null,
                render: function(data, type, row) {
                    if (row.status === 'queued') {
                        return ' <button id="cancelButtonId' + row.id + '" class="cancelButton" data-job-id="' + row.id + '">Cancel</button>';
                    }
                    if (row.status === 'finished') {
                        return ' <a class="downloadLink" href="' + row.download_path + '" download>Download</a>';
                    }
                    if (row.status === 'failed') {
                        return ' <a class="downloadLink" href="' + row.download_path + '" download>Show error log</a>';
                    }
                    return '';
                },
                sortable: false
            },
            { data: 'name'},
            { data: 'status'},
            { data: 'created_at'},
            { data: 'started_at'},
            { data: 'finished_at'},
            { data: 'query_params'}
        ],
        "initComplete": registerCancelButtonEvents,
    });
    gJobTable.on('draw', registerCancelButtonEvents);
};


loadDataTable();
loadInfos();
document.getElementById('createJob').addEventListener('click', createJob);

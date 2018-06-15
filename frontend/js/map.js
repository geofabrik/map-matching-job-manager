"use strict";

// INFO: Following variables have be modified when this page is deployed on a server
var start_latitude = 48.86; // initial latitude of the center of the map
var start_longitude = 2.39; // initial longitude of the center of the map
var start_zoom = 10; // initial zoom level
var max_zoom = 19; // maximum zoom level the tile server offers
// End of the variables which might be modified if deployed on a server

// define base maps
var osmAttribution = 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var baseLayers = {
    'OSM Carto': L.tileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, imagery CC-BY-SA'}),
    'OSM Carto DE': L.tileLayer('//{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png', {maxZoom: 19, attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, imagery CC-BY-SA'}),
    'SNCFOSM': L.tileLayer('https://carto.sncf.fr/tiles/osm/{z}/{x}/{y}.png', {attribution: osmAttribution}),
    'SNCFOSMFR': L.tileLayer('https://carto.sncf.fr/tiles/osmfr/{z}/{x}/{y}.png', {attribution: osmAttribution}),
    'SNCF': L.tileLayer('https://carto.sncf.fr/tiles/sncf/{z}/{x}/{y}.png', {attribution: osmAttribution}),
    'SNCF_FRANCE': L.tileLayer('https://carto.sncf.fr/tiles/sncf-france/{z}/{x}/{y}.png', {attribution: osmAttribution}),
};
var map = null;

// set current layer, by default the layer with the local tiles
var currentBaseLayerName = 'SNCFOSM';


// functions executed if the layer is changed or the map moved
function update_url(newBaseLayerName='') {
    var newName = newBaseLayerName;
    if (newBaseLayerName === '') {
        newName = currentBaseLayerName;
    }
    var origin = location.origin;
    var pathname = location.pathname;
    var newurl = origin + pathname + "#" + newName + '/' + map.getZoom() + "/" + map.getCenter().lat.toFixed(6) + "/" +map.getCenter().lng.toFixed(6);
    history.replaceState('data to be passed', document.title, newurl);
}


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

function initMap() {
    // define overlay
    var gpxLayer = null;
    var gpxDataStr = '';

    // get layer and location from anchor part of the URL if there is any
    var anchor = location.hash.substr(1);
    if (anchor != "") {
        var elements = anchor.split("/");
        if (elements.length == 4) {
            currentBaseLayerName = decodeURIComponent(elements[0]);
            start_zoom = elements[1];
            start_latitude = elements[2];
            start_longitude = elements[3];
        }
    }

    map = L.map('map', {
        center: [start_latitude, start_longitude],
        zoom: start_zoom,
        layers: [baseLayers[currentBaseLayerName]]
    });
    // layer control
    var layerControl = L.control.layers(baseLayers, {});
    layerControl.addTo(map);

    // event is fired if the base layer of the map changes
    map.on('baselayerchange', function(e) {
        currentBaseLayerName = e.name;
        update_url(e.name);
    });

    // change URL in address bar if the map is moved
     map.on('move', function(e) {
         update_url();
    });
}

function showRequestSuccess(method, call, response) {
    var msgDiv = document.getElementById('message');
    msgDiv.classList.remove('hideMessage');
    msgDiv.classList.remove('okMessage');
    msgDiv.classList.remove('errorMessage');
    var obj = JSON.parse(response);
    if (method === 'POST' && call === 'job') {
        msgDiv.innerText = 'Job ' + obj[0]["name"] + ' successfully created.';
        msgDiv.classList.add('okMessage');
    } else if (method === 'POST' && call === 'job') {
        msgDiv.innerText = 'ERROR: Job ' + obj[0]["name"] + ' could not be created.';
        msgDiv.classList.add('errorMessage');
    }
}

function sendJobPostRequest(inputData) {
    var inputFormat = document.getElementById('inputFormat').value;
    var xhr = new XMLHttpRequest();
    var url = "/job?";
    url += "&name=" + encodeURIComponent(document.getElementById('').value);
    url += "&gps_accuracy=" + document.getElementById('gpsAccuracy').value;
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
            showRequestSuccess("POST", "job", xhr.response);
            loadDataTable();
        } else if (xhr.readyState == XMLHttpRequest.DONE) {
            showRequestFailure("POST", "job", xhr.response);
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

function loadDataTable() {
    var xhr = new XMLHttpRequest();
    var url = "/status";
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            var gJobTable = $('#table-jobs').DataTable({
                data: xhr.response,
                columns: [
                    { data: 'id'},
                    { data: 'name'},
                    { data: 'status'},
                    { data: 'query_params'}
                ]
            });
        }
    };
    xhr.send();


//    var gJobTable = $('#table-jobs').DataTable({
//        ajax: "http://saarland.hatano.geofabrik.de/status",
//        columns: [
//            { data: 'id'},
//            { data: 'name'},
//            { data: 'status'},
//            { data: 'query_params'}
//        ]
//    });
//
//    $('#name')[0].value = new Date(Date.now()).toISOString(); 
};

//document.onreadystatechange = () => {
//    if (document.readyState === 'complete') {
        loadDataTable();
        loadInfos();
        initMap();
        document.getElementById('createJob').addEventListener('click', createJob);
//    }
//};


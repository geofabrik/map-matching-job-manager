ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
FRONTEND:=${ROOT_DIR}/frontend
DOCS:=${ROOT_DIR}/docs
TEMPLATES:=${ROOT_DIR}/templates

all: ${FRONTEND}/index.html ${FRONTEND}/api.html

${FRONTEND}/index.html: ${TEMPLATES}/index.tmpl build_frontend.py
	python3 build_frontend.py -T "Railway routing map matching job management" -l "https://www.geofabrik.de/geofabrik/imprint.html" -p "https://www.geofabrik.de/geofabrik/imprint.html" -t ${TEMPLATES}/index.tmpl > ${FRONTEND}/index.html

${FRONTEND}/api.html: ${TEMPLATES}/index.tmpl build_frontend.py ${DOCS}/api.md
	python3 build_frontend.py -u "http://localhost" -T "API documentation of the railway routing map matching job management" -l "https://www.geofabrik.de/geofabrik/imprint.html" -p "https://www.geofabrik.de/geofabrik/imprint.html" -t ${TEMPLATES}/index.tmpl -m ${DOCS}/api.md > ${FRONTEND}/api.html

clean:
	rm ${FRONTEND}/index.html ${FRONTEND}/api.html

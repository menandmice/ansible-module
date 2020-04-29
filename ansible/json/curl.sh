#!/bin/bash

# Use as: ./curl.sh IPAMRecords/22 -X PUT -d @reser.json

URL="${1}"
shift
CMD="curl -v"
CMD="${CMD} --user apidude:TheAPIDude"
CMD="${CMD} -H 'Content-Type: application/json'"
CMD="${CMD} ${@}"
CMD="${CMD} http://mandm.example.net/mmws/api/${URL}"

${CMD} | jq .
echo "${CMD}"

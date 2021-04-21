#!/bin/bash

# Use as: ./curl.sh IPAMRecords/22 -X PUT -d @reser.json

URL="${1}"
shift
CMD="curl -vs"
CMD="${CMD} --header Content-Type:application/json"
CMD="${CMD} --user apidude:TheAPIDude"
CMD="${CMD} ${@}"
CMD="${CMD} http://micetro.example.net/mmws/api/${URL}"

${CMD} | jq .
echo "${CMD}"

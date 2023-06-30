#!/bin/bash
echo "URL of deployment is:" $1

if [ -z "$1" ] ; then
    echo "Please provide the base URL of the deployment as the first parameter";
    exit 1
fi

docker build -t pblive .
docker run --rm -e "QUIZ_SERVER_URL="$1 -p 5005:5000 -d --name jeu pblive

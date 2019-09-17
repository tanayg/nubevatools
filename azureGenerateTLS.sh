#!/bin/bash


#set arguements
NAME=

#Loop a bunch of interesting things that use encrypted traffic

while true; do
#Grab EICAR first as binary then as text
curl --output /dev/null https://secure.eicar.org/eicar.com
sleep 5
#TLS version of TestmyIDS.com
curl --output /dev/null https://nubevalabs.s3.amazonaws.com/testmyids.txt
sleep 5
#Download Google Homepage via TLS
curl --output /dev/null https://www.google.com
sleep 5
#Download ESPN Homepage via TLS
curl --output /dev/null https://www.bbc.com
sleep 5
done

#!/bin/bash


#set arguements
NAME=

#Loop a bunch of interesting things that use encrypted traffic

while true; do
#Grab 100MB file on S3
wget -q -O /dev/null https://tlsELB-c03c5d178d8b2b95.elb.us-east-1.amazonaws.com/100MB.zip --no-check-certificate
sleep $[ ( $RANDOM % 5 )  + 1 ]s
done

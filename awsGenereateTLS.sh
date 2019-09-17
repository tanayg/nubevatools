#!/bin/bash


#set arguements
NAME=

#Loop a bunch of interesting things that use encrypted traffic

while true; do
#AWS API call on port 443 using TLS to show user info
#JSON is always the preferred format as it visualizes easier
#expected output here is a auth error
#this will fail on Azure of course
aws iam get-user  --output json
sleep 5
#AWS API call on port 443 using TLS to show user info
#aws ec2 describe-vpcs --output json --region us-east-1
#sleep 5
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
#Clone Git Repository
git clone https://github.com/nubevalabs/demorepo.git /tmp/demorepo
sudo rm -r /tmp/demorepo
sleep 5
#save this for later
#http://test.com/items.php?id=2 and 1=1
#This is a SQL injection attempt. The 1=1 is an indicatior. 
done

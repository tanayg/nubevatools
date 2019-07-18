#!/bin/bash


#set arguements
NAME=

#Loop a bunch of interesting things that use encrypted traffic

while true; do
#AWS API call on port 443 using TLS to show user info
#JSON is always the preferred format as it visualizes easier
aws iam get-user  --output json
sleep 5
#AWS API call on port 443 using TLS to show user info
aws ec2 describe-vpcs --output json --region us-east-1
sleep 5
#Grab EICAR first as binary then as text
curl --output /dev/null https://secure.eicar.org/eicar.com
curl --output /dev/null https://secure.eicar.org/eicar.com.txt
sleep 5
#TLS version of TestmyIDS.com
curl --output /dev/null https://evebox.org/files/testmyids.com
sleep 5
done

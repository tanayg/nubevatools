#!/bin/sh
for i in 1 2 3 4 5 6 7 8 9 10
do
  #Website to hit a "hacking" URL category
  curl  --output /dev/null https://2600.com
  sleep 5
  #Grab EICAR first as binary then as text
  curl  --output /dev/null https://secure.eicar.org/eicar.com
  sleep 5
  #TLS version of TestmyIDS.com
  curl  --output /dev/null https://nubevalabs.s3.amazonaws.com/testmyids.txt
  sleep 5
  #Download Google Homepage via TLS
  curl  --output /dev/null https://www.google.com
  sleep 5
  #Download ESPN Homepage via TLS
  curl  --output /dev/null https://www.espn.com
  sleep 5
  #Download BBC via TLS
  curl  --output /dev/null https://www.bbc.com
  sleep 5
done

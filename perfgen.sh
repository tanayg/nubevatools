#!/bin/sh
for i in {1..100}
#for i in 1 2
do
  aws iam get-user > /dev/null
  aws s3 ls > /dev/null
  aws ec2 describe-subnets > /dev/null
  aws ec2 describe-key-pairs > /dev/null
  aws s3 ls > /dev/null

done

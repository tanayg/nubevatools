#!/usr/bin/env python

import boto3
import os
import sys
import paramiko
import StringIO
import json
import time

if len(sys.argv) != 7:
    print("Run Script with Correct Parameters: python iperf_test.py [AWS REGION] [CLIENT INSTANCE ID] [SERVER INSTANCE ID] [TOOL INSTANCE ID] [SSH KEY] [VNI]")
    sys.exit(1)

# Define Test Controls
TEST_THRESHOLD = 0.99  # out of 1
TRAFFIC_DURATION = 10  # seconds

AWS_REGION = sys.argv[1]
ec2 = boto3.resource('ec2', region_name=AWS_REGION)
ec2client = boto3.client('ec2',region_name=AWS_REGION)


###########
# Function handlers
###########

bytes_tapped = 0
bytes_tx = 0
measured_speed = None
cpu_host_user = None
cpu_host_system = None
cpu_host_total = None


def initial_bytes_rx(stdout, stderr):
    global bytes_tapped
    if stderr != "":
        raise Exception("Error received reading bytes:" + stderr)
    bytes_tapped = int(stdout)


def iperf_response(stdout, stderr):
    global bytes_tx
    global measured_speed
    global cpu_host_user
    global cpu_host_system
    global cpu_host_total
    if stderr != "":
        raise Exception("Error received from iperf:" + stderr)
    resp = json.loads(stdout)
    bytes_tx = resp['end']['sum_sent']['bytes']
    measured_speed = resp['end']['sum_sent']['bits_per_second']
    cpu_host_user = resp['end']['cpu_utilization_percent']['host_user']
    cpu_host_system = resp['end']['cpu_utilization_percent']['host_system']
    cpu_host_total = resp['end']['cpu_utilization_percent']['host_total']
    print("")
    print("Test at %s" % speed)
    print("Measured iperf3 speed at %s bit/s" % measured_speed)
    print("Measured cpu user at %s%%" % cpu_host_user)
    print("Measured cpu system at %s%%" % cpu_host_system)
    print("Measured cpu total at %s%%" % cpu_host_total)


def end_bytes_rx(stdout, stderr):
    global bytes_tapped
    if stderr != "":
        raise Exception("Error received reading bytes:" + stderr)
    bytes_tapped = int(stdout) - bytes_tapped


# fetch command-line arguments
source_instance_id = sys.argv[2]
source_ssh_key = sys.argv[5]
destination_instance_id = sys.argv[3]
destination_ssh_key = sys.argv[5]
tool_instance_id = sys.argv[4]
tool_ssh_key = sys.argv[5]
tool_vni = sys.argv[6]
tool_vxlan = "vxlan"+tool_vni

# below is a list of the environment variables that can control the operation
repeat_count = os.environ.get("NUBEVA_TEST_REPEAT", 1)

# Instances
print("Creating ssh connections")
instances = []
instance_types = []
source_instance = ec2.Instance(source_instance_id)

instances.append(source_instance)
destination_instance = ec2.Instance(destination_instance_id)

instances.append(destination_instance)
tool_instance = ec2.Instance(tool_instance_id)
instances.append(tool_instance)

private_keys = []
for i in range(1, 4):
    key = open(sys.argv[5],"r")
    private_key = key.read()
    key.close()
    private_keys.append(private_key)

ssess = []
for i in range(3):
    instance = instances[i]
    instance_username = ''
    if("Ubuntu" in instance.image.description):
        instance_username = 'ubuntu'
    elif("Amazon" in instance.image.description):
        instance_username = 'ec2-user'
    instance_types.append(instance_username)
    pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(private_keys[i]))
    sshsess = paramiko.SSHClient()
    sshsess.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to instance {} at {}".format(instance.id, instance.public_ip_address))
    for j in range(5):
        try:
            sshsess.connect(hostname=instance.public_ip_address, username=instance_username, pkey=pkey, timeout=5)
        except Exception as e:
            print("try: %s error connecting: %s" % (j + 1, e))
        else:
            break
    ssess.append(sshsess)


instance_names = [
    "client",
    "server",
    "tool",
]

source_commands = ["sudo yum install -y iperf3"]

# set destination as iperf server
destination_commands = [
							"sudo yum install -y iperf3",
							"iperf3 -D -J -s"
						]
tool_commands = []

setup_commands = [
    source_commands,
    destination_commands,
    tool_commands
]

test_result = None

print("Setting up test")
for idx, ssh in enumerate(ssess):
    for command in setup_commands[idx]:
        print "Executing {} on instance {}".format(command, instance_names[idx])
        stdin, stdout, stderr = ssh.exec_command(command)
        print stdout.read()
        err = stderr.read()
        if err:
            print("Errors: {}".format(err))

count = 0
while True:
    count += 1

    print("Test run %d" % count)
    for speed in [".25G", ".5G", ".75G", "1G", "1.25G", "1.5G", "1.75G", "2G", "2.25G", "2.5G", "2.75G", "3G", "3.25G"]:
        test_commands = [
            {
                "instance": 2,
                "command": "cat /sys/class/net/" + tool_vxlan + "/statistics/rx_bytes",
                "handler": initial_bytes_rx,
            },
            {
                "instance": 0,
                "command": "iperf3 -J "
                           "-c {dst_addr} "
                           "--get-server-output -b{speed} "
                           "-t{duration}".format(
                    dst_addr=instances[1].private_ip_address,
                    speed=speed,
                    duration=TRAFFIC_DURATION,
                ),
                "handler": iperf_response
            },
            {
                "instance": 2,
                # wait until no more packets received.
                "command": 'while [ "$RX" != $(cat /sys/class/net/' + tool_vxlan + '/statistics/rx_bytes) ]; '
                           'do RX=$(cat /sys/class/net/' + tool_vxlan + '/statistics/rx_bytes); '
                           '   sleep 1; '
                           'done; '
                           'echo "$RX"',
                "handler": end_bytes_rx,
            },
        ]
        for idx, tc in enumerate(test_commands):
    #        print "Executing {} on instance {}".format(tc, instance_names[idx])
            stdin, stdout, stderr = ssess[tc['instance']].exec_command(tc['command'])
            tc['handler'](stdout.read(), stderr.read())
        print("Bytes sent: %s" % bytes_tx)
        print("Bytes tapped: %s" % bytes_tapped)
        print("%.2f%% received at tool." % (100 * bytes_tapped / bytes_tx))
        if (bytes_tapped / bytes_tx) < TEST_THRESHOLD:
            break
        else:
            test_result = measured_speed

    if not test_result:
        raise Exception("Unable to measure speed")

    print("Measured BW at: %s bit/s" % test_result)
    print("Measured cpu user at %s%%" % cpu_host_user)
    print("Measured cpu system at %s%%" % cpu_host_system)
    print("Measured cpu total at %s%%" % cpu_host_total)

    if repeat_count > 0 and count >= repeat_count:
        print("%d tests finished." % count)
        break
    else:
        print("Sleeping 30s before next test run.")
        time.sleep(30)

print("Test completed.")

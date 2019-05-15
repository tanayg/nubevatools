#!/usr/bin/env python

import boto3
import os
import sys
import paramiko
import StringIO
import json
import time
import sshtunnel
import socket
import subprocess
from contextlib import closing

if len(sys.argv) != 8:
    print("Run Script with Correct Parameters: python nuagent_iperf_test.py [AWS REGION] [CLIENT INSTANCE ID] [SERVER INSTANCE ID] [TOOL INSTANCE ID] [BASTION INSTANCE ID] [SSH KEY] [VNI]")
    sys.exit(1)

# Define Test Controls
TEST_THRESHOLD = 0.99  # out of 1
TRAFFIC_DURATION = 10  # seconds
paramiko.util.log_to_file("/tmp/paramiko.bastion_iperf_test.log")

# COMMAND LINE ARGUMENTS
# 1[AWS REGION] 2[CLIENT INSTANCE ID] 3[SERVER INSTANCE ID] 4[TOOL INSTANCE ID] 5[BASTION INSTANCE ID] 6[SSH KEY]
# 7[VNI]
AWS_REGION = sys.argv[1]
source_instance_id = sys.argv[2]
destination_instance_id = sys.argv[3]
tool_instance_id = sys.argv[4]
bastion_instance_id = sys.argv[5]
ssh_key_filename = sys.argv[6]
tool_vni = sys.argv[7]
tool_vxlan = "vxlan"+tool_vni

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


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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


def bastion_exec(b_inst, r_inst, key_file, cmd, quiet=True):
    if "Ubuntu" in r_inst.image.description:
        instance_username = 'ubuntu'
    elif "Amazon" in r_inst.image.description:
        instance_username = 'ec2-user'
    else:
        # the default
        instance_username = "ec2-user"
    ssh_prefix = "ssh -o ProxyCommand='ssh -i {k_f} ec2-user@{b_ip} nc {h_ip} 22' -i {k_f} {un}@{h_ip} ".format(
        b_ip=b_inst.public_ip_address, k_f=key_file, h_ip=r_inst.private_ip_address, un=instance_username)

    if isinstance(cmd, list):
        cmd = " ".join(cmd)

    #print("\nExecuting:\n\t{}".format(cmd))
    stdin, stdout, stderr = subprocess.Popen("{} '{}'".format(ssh_prefix, cmd))
    stdoutS, stderrS = stdout.read(), stderr.read()
    if not quiet:
        print("STDOUT:\n{}".format(stdoutS))
        print("STDERR:\n{}".format(stderrS))

    return stdoutS, stderrS


# below is a list of the environment variables that can control the operation
repeat_count = os.environ.get("NUBEVA_TEST_REPEAT", 1)

# Instances
print("Creating ssh connections")
BASTION_INSTANCE = ec2.Instance(bastion_instance_id)
public_instances = [BASTION_INSTANCE]
ssess = []
for i in public_instances:
    sshsess = paramiko.SSHClient()
    sshsess.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to instance {} at {}".format(i.id, i.public_ip_address))
 #   print("DEBUG: ssh -i {} ec2-user@{}".format(ssh_key_filename, i.public_ip_address))
    for j in range(5):
        try:
            sshsess.connect(hostname=i.public_ip_address, username='ec2-user',
                            key_filename=os.path.expanduser(ssh_key_filename), timeout=5)
        except Exception as e:
            print("try: %s error connecting: %s" % (j + 1, e))
        else:
            break
    ssess.append(sshsess)

with open(os.path.expanduser(ssh_key_filename), "r") as keyfd:
    ssh_key_val = keyfd.read()

public_setup_commands = [
    # bastion
    [
        # "echo -n '{}' > ~/.ssh/bastion_key && chmod 0700 ~/.ssh/bastion_key ".format(ssh_key_val)
        "sudo yum install nc -y"
    ]
]

for idx, ssh in enumerate(ssess):
    for command in public_setup_commands[idx]:
        # print "Executing {} on instance {}".format(command, instance_names[idx])
        stdin, stdout, stderr = ssh.exec_command(command)
     #   print stdout.read()
        err = stderr.read()
        if err:
            print("Errors: {}".format(err))
            raise Exception("barfed on command to linux test instance")

instances = [
    ec2.Instance(source_instance_id),
    ec2.Instance(destination_instance_id),
    ec2.Instance(tool_instance_id)
]

# Private Instances
print("Creating private ssh connections")
priv_ssess = []
for i in instances:
    if "Ubuntu" in i.image.description:
        instance_username = 'ubuntu'
    elif "Amazon" in i.image.description:
        instance_username = 'ec2-user'
    else:
        # the default
        instance_username = "ec2-user"

    sshsess = paramiko.SSHClient()
    sshsess.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to instance {} at {}".format(i.id, i.private_ip_address))
    pcmd= "ssh -o StrictHostKeyChecking=no -i {kf} ec2-user@{bi} nc {ri} 22".format(
        kf=ssh_key_filename, bi=BASTION_INSTANCE.public_ip_address, ri=i.private_ip_address)
 #   print("DEBUG: ssh -i {kf} -o ProxyCommand='{pcmd}' ec2-user@{ri}".format(
 #       kf=ssh_key_filename, pcmd=pcmd, ri=i.private_ip_address))
    proxy = paramiko.ProxyCommand(pcmd)
    for j in range(5):
        try:
            sshsess.connect(hostname=i.public_ip_address, username=instance_username,
                            key_filename=os.path.expanduser(ssh_key_filename),
                            timeout=5, sock=proxy)
        except Exception as e:
            print("try: %s error connecting: %s" % (j + 1, e))
        else:
            break
    else:
        raise Exception("failed to connect to instance {} {}".format(i.id, i.private_ip_address))
    priv_ssess.append(sshsess)


instance_names = [
    "client",
    "server",
    "tool",
    "bastion"
]

source_commands = ["sudo yum install -y iperf3"]
# set destination as iperf server
destination_commands = [
    "sudo yum install -y iperf3",
    "iperf3 -D -J -s"
]
tool_commands = [
    "if ! sudo ip link show | grep vxlan{vni} ; then "
        "sudo ip link add name vxlan{vni} type vxlan id {vni} dev eth0 dstport 4789 ; "
    "fi".format(vni=tool_vni),

    "sudo ip link set up vxlan{vni}".format(vni=tool_vni)
]

setup_commands = [
    source_commands,
    destination_commands,
    tool_commands
]

test_result = None

print("Setting up test")
for idx, instance_i in enumerate(instances):
    for command in setup_commands[idx]:
        # bastion_exec(BASTION_INSTANCE, instances[idx], ssh_key_filename, command)
        print "Executing on instance {}:\n\t'{}'".format(instance_names[idx], command)
        ssh = priv_ssess[idx]
        stdin, stdout, stderr = ssh.exec_command(command)
 #       print stdout.read()
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
            # STDOUT, STDERR = bastion_exec(BASTION_INSTANCE, instances[tc['instance']], ssh_key_filename, tc['command'], quiet=True)
            # tc['handler'](STDOUT, STDERR)
            iIdx = tc['instance']
            command = tc['command']
     #       print "Executing {} on instance {}".format(command, instance_names[iIdx])
            ssh = priv_ssess[iIdx]
            stdin, stdout, stderr = ssh.exec_command(command)
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

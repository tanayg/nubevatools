#!/usr/bin/env python3

import os
import sys
import getopt
import yaml
import subprocess
import fileinput
from shutil import copyfile


CLUSTER_CONFIG_FILE = "nukates.yaml"
PRIVATE_CLUSTER_CONFIG_FILE = "nukates-private.yaml"

OPERATOR_CONFIG_FILE = "operator.yaml"
PRIVATE_OPERATOR_CONFIG_FILE = "operator-private.yaml"

POSTGRES_CONFIG_FILE = "NuComplete.yaml"
PRIVATE_POSTGRES_CONFIG_FILE = "NuComplete-private.yaml"

DEPLOYMENT_PACKAGE_FILE = "private_deploy_package.zip"
FILES_TO_DEPLOY = [
    "service_account.yaml",
    "role.yaml",
    "role_binding.yaml",
    "cluster_role_binding.yaml",
    "nukates.nuos.io_nukates_crd.yaml",
    "nukates.nuos.io_nuconfigs_crd.yaml",
    PRIVATE_OPERATOR_CONFIG_FILE,
    "NuComplete.yaml",
    PRIVATE_CLUSTER_CONFIG_FILE
]

repo_uri = None
bastion_host = None
ssh_key = None


def run_cmd(cmd, cwd=None, silent=False):
    stdout = None
    stderr = None
    if silent:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
    res = subprocess.run(cmd, cwd=cwd, stdout=stdout, stderr=stderr)
    if res.returncode != 0:
        raise SystemExit("failed to execute:\n{}".format(" ".join(cmd)))


def print_help():
    print('Usage: deploy_private.py -u <repository_uri> -b <bastion_host> -i <ssh_key>')


def update_images_in_dict(arr):
    for ic in arr:
        if "image" in ic.lower():
            arr[ic] = update_image(arr[ic])
    return arr


def update_image(image):
    if "sha256" in image:
        t = image.split('@')
        arr = t[0].split('/')
    else:
        arr = image.split('/')

    image_tag = image
    if len(arr) > 1:
        image_tag = arr.pop()

    if ":" in image_tag:
        image_tag_arr = image_tag.split(":")
        image_tag = image_tag_arr[0]

    return "{}/{}".format(repo_uri, image_tag)


def generate_private_cluster_config():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)

    with open("{}/{}".format(dname, CLUSTER_CONFIG_FILE)) as f:
        data = yaml.safe_load(f)
        for entry in data['spec']:
            image_config = data['spec'][entry]
            if 'image' in image_config:
                data['spec'][entry] = update_images_in_dict(image_config)

            if 'kafka' in image_config:
                data['spec'][entry]['kafka'] = update_images_in_dict(image_config['kafka'])
                data['spec'][entry]['kafka_controller']['image'] = update_image(
                    image_config['kafka_controller']['image'])

            if 'm3' in image_config:
                data['spec'][entry]['m3'] = update_images_in_dict(image_config['m3'])

            if entry == 'monitoring':
                data['spec'][entry] = update_images_in_dict(image_config)

    with open("{}/{}".format(dname, PRIVATE_CLUSTER_CONFIG_FILE), 'w') as f:
        yaml.safe_dump(data, f)


def generate_private_operator_config():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)

    with open("{}/{}".format(dname, OPERATOR_CONFIG_FILE)) as f:
        data = yaml.safe_load(f)
        data['spec']['template']['spec']['containers'][0]['image'] = update_image(data['spec']['template']['spec']['containers'][0]['image'])

    with open("{}/{}".format(dname, PRIVATE_OPERATOR_CONFIG_FILE), 'w') as f:
        yaml.safe_dump(data, f)


def main(argv):
    global repo_uri, bastion_host, ssh_key
    try:
        opts, args = getopt.getopt(argv, "hiu:b:")
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt == "-u":
            repo_uri = arg
        elif opt == "-b":
            bastion_host = arg
        elif opt == "-i":
            ssh_key = arg
    if not repo_uri or not bastion_host:
        print_help()
        sys.exit(1)

    generate_private_cluster_config()
    generate_private_operator_config()

    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    ssh_opts = ["-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no"]

    package_cmd = ["tar", "-zcvf", DEPLOYMENT_PACKAGE_FILE] + FILES_TO_DEPLOY
    run_cmd(package_cmd, cwd=dname, silent=True)
    run_cmd(["scp"] + ssh_opts + [DEPLOYMENT_PACKAGE_FILE, "ec2-user@{}:/tmp".format(bastion_host)], silent=True)

    ssh_cmd = ["ssh", "ec2-user@{}".format(bastion_host)] + ssh_opts
    if ssh_key:
        ssh_cmd.append("-i")
        ssh_cmd.append(ssh_key)

    bastion_dir = "/tmp/nubeva/deployment"
    run_cmd(ssh_cmd+["mkdir", "-p", bastion_dir], silent=True)
    run_cmd(ssh_cmd+["tar", "xvzf", "/tmp/{}".format(DEPLOYMENT_PACKAGE_FILE), "-C", bastion_dir], silent=True)
    # docker login to ecr
    run_cmd(ssh_cmd + ["eval $(aws ecr get-login --region $(curl -s "
                       "http://169.254.169.254/latest/meta-data/placement/availability-zone | sed 's/[a-z]$//') "
                       "--no-include-email)"])
    # Need to deploy in certain order
    for file in FILES_TO_DEPLOY:
        print("Deploying {}".format(file))
        run_cmd(ssh_cmd+["kubectl", "apply", "-f", "{}/{}".format(bastion_dir, file)])


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3

# Copyright (c) XXV Inc. dba Synthetic Minds
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import subprocess
import argparse
import tempfile
import time
import signal
import json


"""
Script to start the Libra testnet and run the libra.py concurrently.
Usage: ./run_tests.py -d <path to directory containing scripts, .json file and address file>
"""


LIBRA_BASE = os.path.join(os.getcwd(), '..', '..', '..', '..')
child_signal = False


def cleanup(args):
    """Function to delete half processed files."""
    os.chdir(os.path.join(os.getcwd, args['dirname']))
    for curfile in os.listdir(os.getcwd()):
        if 'processed' in curfile:
            os.system('rm {}'.format(curfile))


def preprocess(args: dict) -> str:
    """Function to preprocess input .mvir files by substituting strings for hexstrings."""
    dirname = args['dirname']
    txn_scripts_dir = os.path.join(os.getcwd(), dirname)

    with open(os.path.join(txn_scripts_dir, 'out.json'), 'r') as f:
        json_contents = json.load(f)

    num_txns = json_contents['total_txns']

    for txn in range(1, num_txns + 1):
        txn_data = json_contents[str(txn)]

        if len(txn_data['args']) != 0:
            raise Exception('Arguments to transaction script not supported.')

        # Make sure the .json has valid input files that exist. Copy over other attributes of json file.
        input_mvir_file = os.path.join(txn_scripts_dir, txn_data['input'])
        if not os.path.isfile(input_mvir_file):
            print('.json file has non file entries.')
            cleanup(args)
            sys.exit(-1)

        processed = 'processed-' + txn_data['input']
        os.system('python3 ./preproc.py {} > {}'.format(input_mvir_file, os.path.join(txn_scripts_dir, processed)))
        txn_data['input'] = processed

    with open(os.path.join(txn_scripts_dir, 'processed.json'), 'w+') as newfile:
        newfile.write(json.dumps(json_contents, indent=2))

    return 'processed.json'


def signal_handler(signum: int, frame) -> None:
    global child_signal

    if signum == signal.SIGUSR1:
        child_signal = True


def read_file(path: str) -> bool:
    with open(path, "r") as f:
        for line in f:
            if "Please, input commands:" in line:
                return True
    return False


def main(args: dict) -> None:
    global LIBRA_BASE

    logs_path = tempfile.mkdtemp(dir=os.getcwd())
    (stdout_fd, stdout_path) = tempfile.mkstemp(dir=os.getcwd())
    print("Logs in: {}".format(logs_path))
    print("stdout in: {}".format(stdout_path))
    os.chdir(LIBRA_BASE)

    with open(stdout_path, "r+") as f:
        parent_proc = subprocess.Popen("RUST_BACKTRACE=1 cargo run -p libra_swarm -- -s -l -c {}".format(logs_path), shell=True, stdout=f, stderr=subprocess.PIPE)
        signal.signal(signal.SIGUSR1, signal_handler)
        while read_file(stdout_path) != True:
            print('Waiting for Libra to start.')
            time.sleep(2)

        os.kill(os.getpid(), signal.SIGUSR1)

        pid = os.fork()
        if pid == 0:
            # child process, start the python script here
            global child_signal

            while child_signal != True:
                pass

            os.chdir(LIBRA_BASE + '/language/stdlib/modules/tests')
            child_proc = subprocess.Popen("./send_commands_to_libra_cli.py -d {}".format(args['dirname']), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child_proc.wait()
            (out, err) = child_proc.communicate()
            print(out.decode())
            print(err.decode())
            return
        else:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError as e:
                os.kill(pid, signal.SIGKILL)

            parent_proc.wait()

    os.close(stdout_fd)
    print("Done execution")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Program to run transactions on Libra.")
    parser.add_argument('-d', '--dirname', help="Directory containing transaction scripts.", required=True)
    args = vars(parser.parse_args()) # convert arguments to dict for easy access.

    newname = preprocess(args)
    main(args)

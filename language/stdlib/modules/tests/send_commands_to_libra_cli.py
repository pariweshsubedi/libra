#!/usr/bin/env python3

# Copyright (c) XXV Inc. dba Synthetic Minds
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import subprocess
import argparse
import time
import json
import socket


"""
Script to take a Libra protocol buffer and interact with the client "touchlessly"
Usage: ./send_commands_to_libra_cli.py -d <path to directory containing scripts, .json file and address file>
"""


LIBRA_BASE = os.getcwd() + '/../../../../' # Path to top level Libra directory.
TCP_IP = '127.0.0.1'
TCP_PORT = 9875
BUFSIZ = 17


# Class to keep track of the various transactions as described in the json file.
class Transaction:
    def __init__(self, sender_address, input_path, args):
        self.sender_id = None
        self.sender_address = sender_address
        self.input_mvir_path = input_path
        self.compiler_output_path = None
        self.transaction_file_path = None
        self.args = args


def compile_input_mvir(txn_list: list, args: dict) -> None:
    """Compiles the input file and returns the path to the output file.

    Args:
        txn_list: List of all the transactions and the input files that need to be compiled.

    Returns:
        None
    """
    tests = os.getcwd() + '/{}'.format(args['dirname'])
    compiler_binary = LIBRA_BASE + '/target/debug/compiler'
    os.chdir(tests)
    path_to_binary = compiler_binary

    for txn in txn_list:
        txn.compiler_output_path = os.path.join(tests, txn.input_mvir_path + '.out')
        compiler_command = "{} -o {} {}".format(path_to_binary, txn.compiler_output_path, txn.input_mvir_path)

        compiler = subprocess.Popen(compiler_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return_code = compiler.wait()
        command_stderr = compiler.communicate()[1]

        if return_code != 0:
            print('File cannot be compiled')
            print(command_stderr)
            cleanup(txn_list)
            sys.exit(-1)


def cleanup(txn_list: list) -> None:
    """Clean up all output files produced by the compiler and transaction_builder.

    Args:
        txn_list: List of all transactions

    Returns:
        None
    """
    for txn in txn_list:
        if txn.compiler_output_path is not None and os.path.exists(txn.compiler_output_path):
            os.remove(txn.compiler_output_path)
        if txn.transaction_file_path is not None and os.path.exists(txn.transaction_file_path):
            os.remove(txn.transaction_file_path)


def main(args) -> None:
    """Main function for the program.
    This function spawns the pexpect child, reads the JSON file containing all transactions and
    executes them. At the end it kills the child process.

    Args:
        args: dict containing all the command line argument mappings.

    Returns:
        None
    """
    global TCP_IP, TCP_PORT, BUFSIZ

    tests = os.getcwd()
    txn_list = []
    accounts = {}
    initial_balance = {}
    accounts_list = []

    json_file = os.path.join(tests, args['dirname'], 'processed.json')
    accounts_file = os.path.join(tests, args['dirname'], 'address-file.dat')

    with open(json_file, 'r') as f:
        data = json.load(f)

    total_transactions = int(data["total_txns"])
    balance = data["init_balance"]

    for txn in range(1, total_transactions + 1):
        try:
            txn_body = data[str(txn)]
            txn_list.append(Transaction(txn_body['sender_address'], txn_body['input'], txn_body['args']))
        except KeyError:
            print("ERROR: Discrepancy in the number of transactions vs total_txns in the JSON file.")
            sys.exit(-1)

    for key, val in balance.items():
        initial_balance[key] = format(float(val/1000000), '0.6f')
        accounts_list.append(key)

    for acc in accounts_list:
        accounts[acc] = 0

    compile_input_mvir(txn_list, args)

    list_of_commands = []
    list_of_commands.append('account recover {}'.format(accounts_file))

    # iterate over the dict and make the account mint commands.
    for k, v in initial_balance.items():
        list_of_commands.append('account mintb {} {}'.format(k, v))

    # Submit the transaction and increment the sequence number (per account) for every transfer executed.
    for txn in txn_list:
        list_of_commands.append('dev e {} {}'.format(txn.sender_address, txn.compiler_output_path))
        list_of_commands.append('query txn_acc_seq {} {} true'.format(txn.sender_address, accounts[txn.sender_address]))
        accounts[txn.sender_address] += 1

    for account in accounts_list:
        list_of_commands.append("q b {}".format(account))

    list_of_commands.append('q!')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    for cmd in list_of_commands:
        s.send(cmd.encode())
        while s.recv(BUFSIZ).decode() != "Command executed.":
            pass

        time.sleep(1)

    print("All commands executed.")
    cleanup(txn_list)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Program to run transactions on Libra.")
    parser.add_argument('-d', '--dirname', help="Name of directory containing transaction scripts.", required=True)
    args = vars(parser.parse_args()) # convert arguments to dict for easy access.

    main(args)

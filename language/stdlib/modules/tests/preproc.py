# Copyright (c) XXV Inc. dba Synthetic Minds
# SPDX-License-Identifier: Apache-2.0

import sys

"""
This file preprocesses a test script, replacing string literals with an encoded byte string.
"""


def encode_strings(source):
    i = 0
    out = ""
    while i < len(source):
        if source[i] == '"':
            for j in range(i+1, len(source)):
                if source[j] == '"':
                    match = source[i:j+1]
                    new = match
                    if source[i-1] != "b":
                        new = 'h"{}"'.format(match[1:-1].encode().hex())

                    out += new
                    i = j + 0
                    break
        else:
            out += source[i]
        i += 1
    return out


def preproc_mvir_source(fname):
    with open(fname) as f:
        source = f.read()
    out = encode_strings(source)
    sys.stdout.write(out)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ./preproc.py <mvir file>", file=sys.stderr)
        sys.exit(1)
    preproc_mvir_source(sys.argv[1])

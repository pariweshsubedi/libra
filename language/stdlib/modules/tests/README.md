# Running Move scripts on Libra

In this directory are three files:
* `run_tests.py`: This is the main entry point. Requires the name of the directory containing the transaction scripts, the `.json` file and the address file.
* `preproc.py`: Move does not support strings just yet. Some of the experimental transaction scripts have strings in them, which are intended to be converted to hexstrings. This file converts the strings into their hex representation.
* `libra.py`: This file is to send commands over the network to the Libra CLI. The source of `LIBRA_BASE/client/src.main.rs` has been modified to expose a port so that commands can be sent to the CLI from `libra.py` using a TCP socket.

To run your transaction scripts, there are three things that are required:
1. Transaction scripts
2. A `.json` file that contains details of each transaction script (arguments, address of the sender, etc.). A sample file is present in `tests/_generated`. (NOTE: arguments currently not supported yet.)
3. The file persisted on disk after some user accounts have been created. This can be obtained by manually creating the number of desired accounts using the Libra CLI and then persisting these accounts to disk using the command `account write <name of file>`.

Usage:
`./run_tests.py -d <name of directory` to run the transaction scripts present in the directory passed in. To use the Libra CLI without these scripts, run `CLI=1 cargo run -p libra_swarm -- -s` in `LIBRA_BASE`. Use the flag `-l` to enable logging.

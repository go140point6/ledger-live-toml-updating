Use your validator to send information to your webhost to update your toml file, then create a landing page based on the data found in your toml file.

No connection (no holes) to your validator or node,

update every key ledger (or whenever you want) via listener.py

or timed intervals, by setting 'load-type' within in the update.py file, and loading direct, instead of listener.


Be more transparent. Display your validator info, load, amendments, organization and principle. Hands free.

Works on xrpl mainnet, xahau, testnet

Xahau example here: https://xahau.validator.report/ or https://xahau.zerp.network

Mainnet example here: https://mainnet.validator.report/ and here: https://mainnet2.validator.report/


# Setup Instructions - Validator and Web Host Configuration

# Part 1: Validator/Node Server Setup

Prerequisites:

Python3, mpstat, free, df, awk

Python3 requires: json, websockets, subprocess, asyncio, requests

`pip3 install websockets requests`

Optional text editor: nano

Upload Pre-existing Files: Upload update.py and listener.py to the validator server or use nano to create these files and paste the contents accordingly

### Editing update.py:
Modify the following lines:
    xrpl = 'xahaud' # Replace with your XRPL node executable eg. "rippled" or "xahaud"
    load_type = 'standalone' # 'standalone' when its loaded direct, it then uses a timer to trigger the update, 'listener' when being ran by the listener script to trigger the update.
    mode = 'node' # 'validator' for validator type, so it checks/logs the AMMENDMENTS, and so it saves toml via API, 'node' has no ammendments and saves locally
    wait_time = 60 # wait time before re-creating .toml (in seconds)
    api_url = 'https://yourhost.com/toml.php'  # Replace with your API URL
    api_key = 'key'  # Replace with your API key, this can be anything you want, you need to update the php script to match
    file_path = '/home/www/.well-known/xahau.toml' # path to local .toml file, for use in node mode
    allowlist_path = '/root/xahl-node/nginx_allowlist.conf' # allow list path, for use in connections output (node mode)
    websocket_port = '6008' # port thats used for websocket (for use in connections, in node mode)

### Editing listener.py for use in `load_type = 'listener' ``:
Modify the line if necessary:
    uri = "ws://127.0.0.1:6009": Replace with the correct WebSocket server URI, you can find this in your validator config "port_ws_admin_local"


# Part 2: Web Host Setup

Webhost requires:

### PHP

Editing toml.php, Change the following lines:

    $allowedIPAddress = '0.0.0.0': Replace with your validator IP address to reject other sources
    $apiKey = 'key': Set your API key (must match the one in update.py)
    $filePath = '.well-known/xahau.toml': Change the file path as needed (xrp-ledger.toml for Mainnet)

then Set file permissions to 644


### Editing index.html:

Replace .well-known/xahau.toml with the correct TOML file path (use xrp-ledger.toml for Mainnet)


# PART 3, Starting the Script, 

To run the script,

if you want to run in 'listener' mode type, have `load_mode = 'listener'` in the update.py setting, and do `nohup python3 listener.py &` this then updates the .toml file depending on the ledger action

if you want to update the .toml file at regular intavals, set `load_mode = 'standalone'`, and adjust `wait_time = 60` in updater.py file, and then do `nohup python3 update.py` 

### Stopping the Script:

Find the process ID with ps aux | grep python

Terminate using kill [process id]

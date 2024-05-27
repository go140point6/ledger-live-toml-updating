import ast
from datetime import datetime
import json
import os
import requests
import re
import subprocess
import time
import toml

# You can change these variables to match your setup
xrpl = '/opt/xahaud/bin/xahaud' # Replace with your XRPL node executable eg. "/opt/rippled/bin/rippled" or "/opt/xahaud/bin/xahaud"
load_type = 'listener' # 'standalone' mode is when its loaded directly, it then uses a timer to trigger the updates, 'listener' mode is for when being ran by the listener/seperate script to trigger the update.
mode = 'node' # 'validator' for validator type, so it checks/logs the AMMENDMENTS, and so it saves toml via API, 'node' has no ammendments and saves locally
wait_time = 1800 # Used in 'standalone' mode only, is the wait time before re-creating .toml (in seconds)
data_point_amount = 48 # amount of data points to collect, for showing in graph
api_url = 'https://yourhost.com/toml.php'  # Replace with your API URL
api_key = 'key'  # Replace with your API key, this can be anything you want, you need to update the php script to match
toml_path = '/home/www/.well-known/xahau.toml' # path to local .toml file, for use in node mode
allowlist_path = '/root/xahl-node/nginx_allowlist.conf' # allow list path, for use in connections output (node mode)
websocket_port = '6009' # port thats used for websocket (for use in connections, in node mode)

def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return float(result.stdout.strip().replace('%',''))
    except Exception as e:
        return str(e)

def get_xrpl_server_info(key, timenow):
    try:
        server_info_result = subprocess.run([xrpl, "server_info"], capture_output=True, text=True)
        server_info_data = json.loads(server_info_result.stdout)

        status = server_info_data['result']['info']['server_state']
        status_count = int(server_info_data['result']['info']['state_accounting']['full']['transitions'])
        version = server_info_data['result']['info']['build_version']
        status_time = int(server_info_data['result']['info']['server_state_duration_us']) / 1000000
        node_size = server_info_data['result']['info']['node_size']
        ledger = server_info_data['result']['info'].get('validated_ledger', {}).get('seq', 0)
        ledgers = server_info_data['result']['info']['complete_ledgers']
        peers = server_info_data['result']['info']['peers']
        network = server_info_data['result']['info'].get('network_id', 0) # Mainnet doesn't provide a network id, so default 0

        uptime_in_seconds = server_info_data['result']['info']['uptime']
        days = uptime_in_seconds // 86400
        hours = (uptime_in_seconds % 86400) // 3600
        minutes = (uptime_in_seconds % 3600) // 60
        formatted_uptime = f"{days} Days, {str(hours).zfill(2)} Hours, and {str(minutes).zfill(2)} Mins"

        if type == 'validator':
            feature_result = subprocess.run([xrpl, "feature"], capture_output=True, text=True)
            feature_data = json.loads(feature_result.stdout)
            amendments = feature_data['result']['features']
            filtered_amendments = {
                value['name']: key
                for key, value in amendments.items()
                if value.get('enabled') == False and value.get('supported') == True and value.get('vetoed') == False
            }
            amendments_output = "\n".join([f"{name} = \"{id}\"" for name, id in filtered_amendments.items()])

            websocket_connections = 0
            allowlist_count = 0

        else:
            amendments_output = ledger
            websocket_connections = int(run_command( "netstat -an | grep " + websocket_port + " | wc -l | awk '{print int(($1 - 1) / 2)}'" )) # we subtract 1 (the node itself) and then divide by two, as it lists the proxy AND node seperately
            allowlist_count = int(run_command ( "wc -l " + allowlist_path + " | awk '{print $1}' " )) - 2 # we -2 here as 2 entries out of the 3 default entries that are created on install are for the node itself

        # extract data from .toml file, to append to, also force string to list
        toml_data = toml.load(toml_path)
        cpu_data = ast.literal_eval(toml_data.get('STATUS')[0].get('CPU',"[]"))
        ram_data = ast.literal_eval(toml_data.get('STATUS')[0].get('RAM',"[]"))
        hdd_data = ast.literal_eval(toml_data.get('STATUS')[0].get('HDD',"[]"))
        swp_data = ast.literal_eval(toml_data.get('STATUS')[0].get('SWP',"[]"))
        status_count_data = ast.literal_eval(toml_data.get('STATUS')[0].get('STATUS_COUNT',"[]"))
        wss_connect_data = ast.literal_eval(toml_data.get('STATUS')[0].get('WSS_CONNECTS',"[]"))
        time_data = ast.literal_eval(toml_data.get('STATUS')[0].get('TIME',"[]"))

        cpu_usage_current = run_command("top -n1 -b -U xahaud | awk '/" + os.path.basename(xrpl) + "/{print $9}'")
        cpu_data.append(cpu_usage_current)
        if len(cpu_data) > data_point_amount: cpu_data.pop(0)

        ram_usage_current = run_command("free | awk '/Mem:/ {printf(\"%.2f\"), $3/$2 * 100}'")
        ram_data.append(ram_usage_current)
        if len(ram_data) > data_point_amount: ram_data.pop(0)

        hdd_usage_current = run_command("df -h . | awk 'NR==2{print $5}'")
        hdd_data.append(hdd_usage_current)
        if len(hdd_data) > data_point_amount: hdd_data.pop(0)

        swp_usage_current = run_command("free | awk '/Swap:/ {printf(\"%.2f%\"), $3/$2 * 100}'")
        swp_data.append(swp_usage_current)
        if len(swp_data) > data_point_amount: swp_data.pop(0)

        status_count_data.append(status_count)
        if len(status_count_data) > data_point_amount: status_count_data.pop(0)

        wss_connect_data.append(websocket_connections)
        if len(wss_connect_data) > data_point_amount: wss_connect_data.pop(0)

        time_usage_current = timenow.strftime("%H:%M")
        time_data.append(time_usage_current)
        if len(time_data) > data_point_amount: time_data.pop(0)

        status_output = f"""
STATUS = "{status}"
FULLCOUNT = "{status_count}"
BUILDVERSION = "{version}"
LASTREFRESH = "{timenow}Z UTC"
UPTIME = "{formatted_uptime}"
STATUSTIME = "{status_time} in seconds"
CURRENTLEDGER = "{ledger}"
LEDGERS = "{ledgers}"
NODESIZE = "{node_size}"
NETWORK = "{network}"
CONNECTIONS = "{websocket_connections}/{allowlist_count}"
PEERS = "{peers}"

CPU = "{cpu_data}"
RAM = "{ram_data}"
HDD = "{hdd_data}"
SWP = "{hdd_data}"
STATUS_COUNT = "{status_count_data}"
WSS_CONNECTS = "{wss_connect_data}"
TIME = "{time_data}"

KEY = "{key}"
"""
        if mode == 'validator':
            return { 'STATUS': status_output, 'AMENDMENTS': amendments_output }
        else:
            return status_output
    
    except Exception as e:
        print("oops: error with creating status_ouput error:", str(e))
        return

def send_to_api(data):

    try:
        headers = {'Content-Type': 'application/json'}
        params = {'apiKey': api_key}
        response = requests.post(api_url, json=data, headers=headers, params=params)
        response.raise_for_status()

        print("Response from API:", response.text)
    except requests.exceptions.HTTPError as errh:
        print("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Oops: Something Else", err)

def update_toml_file(info, utcnow):
    with open(toml_path, 'r') as file:
        file_content = file.read()
    updated_content = re.sub(
        r'\[\[STATUS\]\].*?\[\[AMENDMENTS\]\]',
        '[[STATUS]]' + info + '\n[[AMENDMENTS]]',
        file_content,
        flags=re.DOTALL
    )
    updated_content = re.sub(
        r'^modified = .*',
        f'modified = {utcnow.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}',
        updated_content,
        flags=re.M
    )

    #print(updated_content)
    with open(toml_path, 'w') as file:
        file.write(updated_content)

if __name__ == "__main__":
    
    if mode == 'validator':
        while True:
            import sys
            if len(sys.argv) != 3 & load_type == 'listener':
                print("Usage: update.py <KEY> <TIME>")
            else:
                key = sys.argv[1]
                timearg = sys.argv[2]
                info = get_xrpl_server_info(key, timearg)
                send_to_api(info)
            if load_type == 'listener': break
            else: time.sleep(wait_time)

    if mode == 'node':
        while True:
            info = get_xrpl_server_info(False, datetime.utcnow())
            update_toml_file(info, datetime.utcnow())
            if load_type == 'listener': break
            else: time.sleep(wait_time)

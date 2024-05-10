const { exec } = require('child_process');
const fetch = require('node-fetch');
const fs = require('fs');
const { promisify } = require('util');
const sleep = promisify(setTimeout);

// You can change these variables to match your setup
const xrpl = 'xahaud'; // Replace with your XRPL node executable eg. "rippled" or "xahaud"
const loadType = 'standalone'; // 'standalone' when it's loaded direct, it then uses a timer to trigger the update, 'listener' when being run by the listener script to trigger the update.
const mode = 'node'; // 'validator' for validator type, so it checks/logs the AMMENDMENTS, and so it saves toml via API, 'node' has no ammendments and saves locally
const waitTime = 900000; // wait time before re-creating .toml (in milliseconds)
const dataPointAmount = 6; // amount of data points to collect, for showing in graph
const apiUrl = 'https://yourhost.com/toml.php'; // Replace with your API URL
const apiKey = 'key'; // Replace with your API key, this can be anything you want, you need to update the php script to match
const tomlPath = '/home/www/.well-known/xahau.toml'; // path to local .toml file, for use in node mode
const allowlistPath = '/root/xahl-node/nginx_allowlist.conf'; // allow list path, for use in connections output (node mode)
const websocketPort = '6008'; // port that's used for websocket (for use in connections, in node mode)

function runCommand(command) {
    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout.trim());
        });
    });
}

async function getXrplServerInfo(key, timenow) {
    try {
        const serverInfoResult = await runCommand(`${xrpl} server_info`);
        const serverInfoData = JSON.parse(serverInfoResult);

        const status = serverInfoData.result.info.server_state;
        const version = serverInfoData.result.info.build_version;
        const statusTime = parseInt(serverInfoData.result.info.server_state_duration_us) / 1000000;
        const nodeSize = serverInfoData.result.info.node_size;
        const ledger = serverInfoData.result.info.validated_ledger?.seq || 0;
        const ledgers = serverInfoData.result.info.complete_ledgers;
        const peers = serverInfoData.result.info.peers;
        const network = serverInfoData.result.info.network_id || 0; // Mainnet doesn't provide a network id, so default 0

        const uptimeInSeconds = serverInfoData.result.info.uptime;
        const days = Math.floor(uptimeInSeconds / 86400);
        const hours = Math.floor((uptimeInSeconds % 86400) / 3600);
        const minutes = Math.floor((uptimeInSeconds % 3600) / 60);
        const formattedUptime = `${days} Days, ${String(hours).padStart(2, '0')} Hours, and ${String(minutes).padStart(2, '0')} Mins`;

        // extract data from .toml file, to append to, also force string to list
        const tomlData = require(tomlPath);
        let cpuData = JSON.parse(tomlData.STATUS[0].CPU || '[]');
        let ramData = JSON.parse(tomlData.STATUS[0].RAM || '[]');
        let hddData = JSON.parse(tomlData.STATUS[0].HDD || '[]');
        let swpData = JSON.parse(tomlData.STATUS[0].SWP || '[]');
        let timeData = JSON.parse(tomlData.STATUS[0].TIME || '[]');

        const cpuUsageCurrent = await runCommand(`top -n1 -b -U xahaud | awk '/${xrpl}/{print $9}'`);
        cpuData.push(cpuUsageCurrent);
        if (cpuData.length > dataPointAmount) cpuData.shift();

        const ramUsageCurrent = await runCommand("free | awk '/Mem:/ {printf(\"%.2f\"), $3/$2 * 100}'");
        ramData.push(ramUsageCurrent);
        if (ramData.length > dataPointAmount) ramData.shift();

        const hddUsageCurrent = await runCommand("df -h . | awk 'NR==2{print $5}'");
        hddData.push(hddUsageCurrent);
        if (hddData.length > dataPointAmount) hddData.shift();

        const swpUsageCurrent = await runCommand("free | awk '/Swap:/ {printf(\"%.2f%\"), $3/$2 * 100}'");
        swpData.push(swpUsageCurrent);
        if (swpData.length > dataPointAmount) swpData.shift();

        const timeUsageCurrent = timenow.toISOString().slice(11, 16);
        timeData.push(timeUsageCurrent);
        if (timeData.length > dataPointAmount) timeData.shift();

        let amendmentsOutput = '';
        let websocketConnections = 0;
        let allowlistCount = 0;

        const statusOutput = `
STATUS = "${status}"
BUILDVERSION = "${version}"
LASTREFRESH = "${timenow.toISOString()}Z UTC"
UPTIME = "${formattedUptime}"
STATUSTIME = "${statusTime} in seconds"
CURRENTLEDGER = "${ledger}"
LEDGERS = "${ledgers}"
NODESIZE = "${nodeSize}"
NETWORK = "${network}"
CONNECTIONS = "${websocketConnections}/${allowlistCount}"
PEERS = "${peers}"

CPU = "${JSON.stringify(cpuData)}"
RAM = "${JSON.stringify(ramData)}"
HDD = "${JSON.stringify(hddData)}"
SWP = "${JSON.stringify(hddData)}"
TIME = "${JSON.stringify(timeData)}"

KEY = "${key}"
`;

        if (mode === 'validator') {
            const featureResult = await runCommand(`${xrpl} feature`);
            const featureData = JSON.parse(featureResult);
            const amendments = featureData.result.features;
            const filteredAmendments = Object.entries(amendments)
                .filter(([_, value]) => !value.enabled && value.supported && !value.vetoed)
                .map(([name, id]) => `${name} = "${id}"`);
            amendmentsOutput = filteredAmendments.join('\n');
        } else {
            amendmentsOutput = ledger;
            websocketConnections = parseInt(await runCommand(`netstat -an | grep ${websocketPort} | wc -l | awk '{print int(($1 - 1) / 2)}'`));
            allowlistCount = parseInt(await runCommand(`wc -l ${allowlistPath} | awk '{print $1}' `)) - 2;
        }

        if (mode === 'validator') {
            return { STATUS: statusOutput, AMENDMENTS: amendmentsOutput };
        } else {
            return statusOutput;
        }

    } catch (error) {
        console.error("oops: error with creating status_ouput error:", error);
        return
    }
}

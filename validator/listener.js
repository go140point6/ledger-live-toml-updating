const WebSocket = require('ws');
const { exec } = require('child_process');

async function ledgerStream() {
    const uri = "ws://127.0.0.1:6009"; // Replace with the correct WebSocket server URI

    try {
        const websocket = new WebSocket(uri);

        websocket.on('open', function open() {
            const subscriptionPayload = {
                id: "ledger stream",
                command: "subscribe",
                streams: ["ledger"]
            };

            websocket.send(JSON.stringify(subscriptionPayload));
        });

        websocket.on('message', async function incoming(message) {
            const response = JSON.parse(message);
            const ledgerIndex = response.ledger_index;

            if (ledgerIndex && ledgerIndex % 256 === 0) {
                console.log(`Received ledger stream update (divisible by 256): ${message}`);
                const ledgerTime = response.ledger_time || "";

                exec(`node update.js ${ledgerIndex} ${ledgerTime}`, (error, stdout, stderr) => {
                    if (error) {
                        console.error(`exec error: ${error}`);
                        return;
                    }
                    console.log(`stdout: ${stdout}`);
                    console.error(`stderr: ${stderr}`);
                });
            }
        });

        websocket.on('close', function close() {
            console.log("WebSocket connection closed.");
        });

    } catch (error) {
        console.error(error);
    }
}

ledgerStream();


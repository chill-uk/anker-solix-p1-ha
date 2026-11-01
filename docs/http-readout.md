# Help validate P1 HTTP decryption

I'm looking to validate if I have found a global/private key to decrypt some extra HTTP endpoints.  
This will be used add additional diagnostic fields to Home Assistant:  
(device serial number, firmware version, MAC address, etc..).  

## Capture with curl

Connect to the same network as your P1 and replace `<p1-dongle-ip>` with its IP address.
Run any one command, or all three:

```sh
curl -o measurement.bin http://<p1-dongle-ip>/api/measurement
curl -o wifi_info.bin http://<p1-dongle-ip>/api/wifi_info
curl -o device_info.bin http://<p1-dongle-ip>/api/device_info
```

The files are saved in your current folder. Encrypt them before sharing, as below.

Keep the files exactly as saved.  
The expected response is encrypted binary, not readable JSON.

## Encrypt before sharing

In order to ensure no-one can read your captures (especially if the decryption key is reused globally),  
I add another layer of encryption, to which only I have the private key.

Save [capture.py](../custom_components/anker_solix_p1/capture.py) alongside your
`.bin` files. It runs without Home Assistant and uses the same support public key
as the integration. Set up a Python virtual environment and install PyNaCl:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pynacl
```

Run the encryption command below in the same terminal, with the environment active.

Replace the IP below with the P1 address you used for curl:

```sh
python3 capture.py --ip <p1-dongle-ip> measurement.bin
```

For all three files, append `wifi_info.bin device_info.bin` to that command.
It creates **`http-readout.encrypted.json`**, containing the original response
bytes and capture-time IP, encrypted with a libsodium sealed box. Only the holder
of the matching support private key can decrypt it. Everything runs locally;
nothing is uploaded. Your original `.bin` files remain on your laptop.

## What each payload contains

After successful decryption, the responses in the captures examined so
far contain the following JSON fields. Other firmware versions may differ.

| Endpoint / saved file | Contents after decryption |
| --- | --- |
| `/api/measurement` / `measurement.bin` | Meter identifier (`unique_id`), protocol version, meter model, timestamp, imported/exported energy in kWh, total and per-phase power in W, per-phase voltage in V, and total/per-phase current in A. Field names include `energy_import_kwh`, `energy_export_kwh`, `power_w`, `power_l1_w` through `power_l3_w`, `voltage_l1_v` through `voltage_l3_v`, and `current_a` / `current_l1_a` through `current_l3_a`. |
| `/api/wifi_info` / `wifi_info.bin` | Wi-Fi network name (`wifi_ssid`) and signal strength (`wifi_rssi_db`). The examined response does not contain a Wi-Fi password. |
| `/api/device_info` / `device_info.bin` | Product name/type, device serial number, firmware version, MAC address, API version, and firmware compatibility value (`firmware_Compatibility`). |


## What to send

Send **`http-readout.encrypted.json`** to the maintainer. The P1 IP is already
inside the encrypted record, so you do not need to post it separately. Include
the firmware version if known. No Wi-Fi password, cloud credentials, flash dump,
or decryption secret is needed.

Open a [GitHub issue](https://github.com/chill-uk/anker-solix-p1-ha/issues/new)
to arrange sharing. Do not attach the original `.bin` files or post your IP:
the endpoint encryption alone does not keep their contents private from someone
who knows its derivation. Send the support-encrypted JSON file instead.

For maintainers, the existing `scripts/decrypt_diagnostics.py` accepts this JSON
file and the support private key. The decrypted record contains `device_ip` and
`responses`, with each original response body in `body_base64`.

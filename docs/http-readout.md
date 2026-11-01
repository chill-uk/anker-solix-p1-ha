# Help validate P1 HTTP decryption

I'm looking to validate if I have found a global/private key to decrypt some extra HTTP endpoints.  
This will be used for additional diagnostic fields in Home Assistant:  
(device serial number, firmware version, MAC address, etc..).  

## Capture with curl

Connect to the same network as your P1 and replace `<p1-dongle-ip>` with its IP address.
Run any one command, or all three:

```sh
curl -o measurement.bin http://<p1-dongle-ip>/api/measurement
curl -o wifi_info.bin http://<p1-dongle-ip>/api/wifi_info
curl -o device_info.bin http://<p1-dongle-ip>/api/device_info
```

These files are encrypted binaries, not readable JSON files.
I'm trying to understand if these files are encrypted with a device specific key, or a generic key.
Please don't share these files as they are in case a generic encryption key is used.

## Encrypt before sharing

In order to ensure no-one can read your captures (especially if the Anker decryption key is reused globally),  
We will add another layer of encryption, to which only I have the private key.

Save [capture.py](../custom_components/anker_solix_p1/capture.py) alongside your `.bin` files.  
It runs without Home Assistant and uses the same support public key as the integration.  

Set up a Python virtual environment and install PyNaCl:

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

One capture should be enough, but if you want to send more data, swap in `wifi_info.bin` or `device_info.bin` to that command.  
It creates a **`http-readout.encrypted.json`** file, containing the response bin file and capture-time IP.  
It's then encrypted with my public key.  

## What each payload contains

What exactly are you sending me?  
Each endpoint contains info as shown below. You might decide that sending me the  
device serial number is ok, but the serial number of your meter / wifi ssid are not.

| Endpoint / saved file | Contents after decryption |
| --- | --- |
| `/api/measurement` / `measurement.bin` | Meter identifier (`unique_id`), protocol version, meter model, timestamp, imported/exported energy in kWh, total and per-phase power in W, per-phase voltage in V, and total/per-phase current in A. Field names include `energy_import_kwh`, `energy_export_kwh`, `power_w`, `power_l1_w` through `power_l3_w`, `voltage_l1_v` through `voltage_l3_v`, and `current_a` / `current_l1_a` through `current_l3_a`. |
| `/api/wifi_info` / `wifi_info.bin` | Wi-Fi network name (`wifi_ssid`) and signal strength (`wifi_rssi_db`). The examined response does not contain a Wi-Fi password. |
| `/api/device_info` / `device_info.bin` | Product name/type, device serial number, firmware version, MAC address, API version, and firmware compatibility value (`firmware_Compatibility`). |


## What to send

Open a [GitHub issue](https://github.com/chill-uk/anker-solix-p1-ha/issues/new) to arrange sharing.  
I will walk you through the steps to encrypt and upload the files.  
Do not attach the original `.bin` files or send any other data.  
The support-encrypted JSON file is all that I need.

Send only the **`http-readout.encrypted.json`**.  
The P1 IP is already inside the encrypted record, so you do not need to post it separately.  
No other details are needed.



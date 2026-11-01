# Help validate P1 HTTP decryption

Please send me the binary response body from **any one** of these endpoints on
your Anker SOLIX P1 Energy Tracker. One file is enough to start; all three are
welcome. This helps check whether the same key derivation works across devices
using AES-GCM authentication, rather than merely checking whether output looks
readable. You do not need a decryption key, experimental mode, or a firmware dump
to collect these files.

## Capture with curl

Connect to the same network as your P1 and replace `192.168.1.123` with its IP address.
Run any one command, or all three:

```sh
curl -o measurement.bin http://192.168.1.123/api/measurement
curl -o wifi_info.bin http://192.168.1.123/api/wifi_info
curl -o device_info.bin http://192.168.1.123/api/device_info
```

The files are saved in your current folder. Send the original `.bin` file and the
P1 IP address you used.

Keep the files exactly as saved: do not paste them into a text editor, convert
them to text, add HTTP headers, or edit/redact their bytes. Changes can prevent
authentication. The expected response is encrypted binary, not readable JSON.

## What each payload contains

After successful decryption, the responses in the captures examined so
far contain the following JSON fields. Other firmware versions may differ.

| Endpoint / saved file | Contents after decryption |
| --- | --- |
| `/api/measurement` / `measurement.bin` | Meter identifier (`unique_id`), protocol version, meter model, timestamp, imported/exported energy in kWh, total and per-phase power in W, per-phase voltage in V, and total/per-phase current in A. Field names include `energy_import_kwh`, `energy_export_kwh`, `power_w`, `power_l1_w` through `power_l3_w`, `voltage_l1_v` through `voltage_l3_v`, and `current_a` / `current_l1_a` through `current_l3_a`. |
| `/api/wifi_info` / `wifi_info.bin` | Wi-Fi network name (`wifi_ssid`) and signal strength (`wifi_rssi_db`). The examined response does not contain a Wi-Fi password. |
| `/api/device_info` / `device_info.bin` | Product name/type, device serial number, firmware version, MAC address, API version, and firmware compatibility value (`firmware_Compatibility`). |

## What to send

Please send the maintainer:

- At least one of the original `.bin` files, noting which endpoint produced it.
- **The P1's local IPv4 address when the file was captured.** The address is an
  input to key derivation; your laptop's address or your public internet IP
  will not work.
- The device firmware version, if known, and approximate capture time.

Please open a [GitHub issue](https://github.com/chill-uk/anker-solix-p1-ha/issues/new)
to arrange a private exchange with the maintainer. The issue can simply say you
have a capture available; do not attach the files or your IP there.

Although the files are encrypted, they can reveal the identifiers, network name,
and readings listed above to someone able to decrypt them. Share the files and
capture-time IP privately. No Wi-Fi password, cloud credentials, flash dump, or
decryption secret is needed.

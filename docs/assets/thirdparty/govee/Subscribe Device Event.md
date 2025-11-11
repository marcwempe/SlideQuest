---
title: "Subscribe Device Event"
source: "https://developer.govee.com/reference/subscribe-device-event"
author:
  - "[[Govee Development Platform]]"
published:
created: 2025-11-11
description: "If your device's capabilities include 'devices.capabilities.event', then you can listen for the event in the following ways. Connection parameters: Host: mqtts://mqtt.openapi.govee.com Port: 8883 Username: [Your Api-Key] Password: [Your Api-Key] Topic: GA/ [Your Api-Key] For example: const mqtt = re..."
tags:
  - "clippings"
---
If your device's capabilities include 'devices.capabilities.event', then you can listen for the event in the following ways.

Connection parameters:

Host: mqtts://mqtt.openapi.govee.com

Port: 8883

Username: \[Your Api-Key\]

Password: \[Your Api-Key\]

Topic: GA/ \[Your Api-Key\]

For example:

- If your ice machine(H7172) is out of water, you will receive the following message.

```json
{
    "sku": "H7172",
    "device": "41:DA:D4:AD:FC:46:00:64",
    "deviceName": "H7172",
    "capabilities":[
        {
            "type": "devices.capabilities.event",
            "instance": "lackWaterEvent",
            "state": [
                {
                    "name": "lack",
                    "value": 1,
                    "message": "Lack of Water"
                }
            ]
        }
    ]
}
```

- Presence Sensor(H5127): You will receive notifications of Presence

```json
{
    "sku": "H5127",
    "device": "06:30:60:74:F4:45:B9:DA",
    "deviceName": "Presence Sensor",
    "capabilities": [
        {
            "type": "devices.capabilities.event",
            "instance": "bodyAppearedEvent",
            "state": [
                {
                    "name": "Presence",
                    "value": 1
                }
            ]
        }
    ]
}
```

- Presence Sensor(H5127): You will receive notifications of Absence

```json
{
    "sku": "H5127",
    "device": "06:30:60:74:F4:45:B9:DA",
    "deviceName": "Presence Sensor",
    "capabilities": [
        {
            "type": "devices.capabilities.event",
            "instance": "bodyAppearedEvent",
            "state": [
                {
                    "name": "Absence",
                    "value": 2
                }
            ]
        }
    ]
}
```

- Dehumidifier(H7151)：Full water notification.

```json
{
    "sku": "H7151",
    "device": "06:30:60:74:F4:45:B9:DA",
    "deviceName": "Dehumidifier",
    "capabilities":[
        {
            "type": "devices.capabilities.event",
            "instance": "lackWaterEvent",
            "state": [
                {
                    "name": "lack",
                    "value": 1,
                    "message": "Lack of Water"
                }
            ]
        }
    ]
}
```
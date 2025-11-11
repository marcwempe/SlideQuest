---
title: "Get Device State"
source: "https://developer.govee.com/reference/get-devices-status"
author:
  - "[[Govee Development Platform]]"
published:
created: 2025-11-11
description: "Query Device's State Query the current status of the device through device and sku. example for lights and appliances capabilities { \"sku\": \"H7143\", \"device\": \"BA:82:D4:ad:FC:94:A1:D8\", \"deviceName\": \"Smart Humidifier\", \"type\": \"devices.types.humidifier\", \"capabilities\": [ { \"type\": \"devices.capabil..."
tags:
  - "clippings"
---
Query the current status of the device through device and sku.

- capabilities
- request example
- response success example
  
- capabilities
  
- request
- response
  

### response field

| field | data type |  |
| --- | --- | --- |
| sku | String | Product model |
| device | String | device id |
| deviceName | String | The device name in Govee Home App. |
| capabilities | Array | device capabilities array |

Capabilities Array

| field | data type |  |
| --- | --- | --- |
| type | String | capbility type |
| instance | String | capability instance |
| state | Object | the struct definition of current state in this instance |

State Define Object

1. enum control value

| field | data type | desc |
| --- | --- | --- |
| value | Object | The type of value depends on the dataType returned by Get You Device. |

In capabilities, if type is 'devices.capabilities.online', it indicates whether the device is wifi online. If it is false, the status data queried is historical data and has no reference significance. If state is true, it means the device is online, and the returned value is the value of the current device status. These values correspond to the list returned by [Get You Device](https://dash.readme.com/project/govee-openapi/v1.0/refs/get-you-devices). If the value value is empty, it means that the instance does not support query.

In capabilities, if the type is 'devices.capabilities.event', this is a property of real-time monitoring. It will only be reported when the event occurs on the device and cannot be obtained through query. If you want to obtain the status in real time, please refer to ' [Subscribe Device Event](https://dash.readme.com/project/govee-openapi/v1.0/refs/subscribe-device-event) ' interface

- Friendly Reminder  
	if the request response 429, means request limits happens, 10000/Account/Day
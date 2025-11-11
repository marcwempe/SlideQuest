---
title: "Get You Devices"
source: "https://developer.govee.com/reference/get-you-devices"
author:
  - "[[Govee Development Platform]]"
published:
created: 2025-11-11
description: "Get you devices and capabilities"
tags:
  - "clippings"
---
## Device Types

- devices.types.light
- devices.types.air\_purifier
- devices.types.thermometer
- devices.types.socket
- devices.types.sensor
- devices.types.heater
- devices.types.humidifier
- devices.types.dehumidifier
- devices.types.ice\_maker
- devices.types.aroma\_diffuser
- devices.types.box

## Capability Types

| capabilities | instance | overview |
| --- | --- | --- |
| devices.capabilities.on\_off | powerSwitch | on/off enum options |
| devices.capabilities.toggle | oscillationToggle,nightlightToggle,gradientToggle,ect | on/off Enum options |
| devices.capabilities.range | brightness,humidity,volume,temperature,ect | set a range number |
| devices.capabilities.mode | ngihtlightScene,presetScene,gearMode,fanSpeed,ect | enum options |
| devices.capabilities.color\_setting | colorRgb,colorTemperatureK | rgb or Kelvin color temperature |
| devices.capabilities.segment\_color\_setting | segmentedBrightness,segmentedColorRgb | set color or brightness on segment |
| devices.capabilities.music\_setting | musicMode | set music mode |
| devices.capabilities.dynamic\_scene | lightScene,diyScene,snapshot | set scene,but the options are not static |
| device.capabilities.work\_mode | workMode | Set the working mode and give it a working value |
| device.capabilities.temperature\_setting | targetTemperature,sliderTemperature | set temperature |

## Discover Devices

Get your devices from Govee ，it will return the capabilities，

- request example
- response success example
- response field

| field | data type |  |
| --- | --- | --- |
| sku | String | Product model |
| device | String | device id |
| deviceName | String | The device name in Govee Home App. |
| capabilities | Array | device capabilities array |

- capabilities array

| field | data type |  |
| --- | --- | --- |
| type | String | capbility type |
| instance | String | capability instance |
| parameters | Object | the struct definition of control command in this instance |

- parameters object
1. enum type parameters

| field | data type | desc |
| --- | --- | --- |
| dataType | String | define the data type of control value.   e.g. **ENUM**,INTEGER,STRUCT |
| options | Array | show the options of control value |
| options.name | String | show the name of this option |
| options.value | \-- | the control value |

1. integer type parameters

| field | data type | desc |
| --- | --- | --- |
| dataType | String | define the data type of control value.   e.g. ENUM,**INTEGER**,STRUCT |
| range | Object | define the range of value |
| range.max | Integer | the max of control value |
| range.min | Integer | the min of control value |
| range.precision | Integer | the precision of control value |
| unit | String | the unit of this control value e.g. temperature Celsius,temperature Fahrenheit |

1. struct type parameters

| field | data type | desc |
| --- | --- | --- |
| dataType | String | define the data type of control value.   e.g. ENUM,INTEGER,**STRUCT** |
| fields | Array | when control value is struct, define the struct filed |
| Array.fieldName | String | the struct field name |
| Array.dataType | String | define the field data type   e.g. ENUM,**INTEGER**,STRUCT |
| Array.required | Boolean | required of this field |
|  |  |  |

- http code

| code | desc |
| --- | --- |
| 200 | success |
| 429 | too many request, request limits, 10000/Account/Day |
| 401 | Unauthorized. check you apiKey |

- Friendly Reminder  
	if the request response 429, means request limits happens, 10000/Account/Day
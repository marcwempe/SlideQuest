---
title: "Control You Device"
source: "https://developer.govee.com/reference/control-you-devices"
author:
  - "[[Govee Development Platform]]"
published:
created: 2025-11-11
description: "On_off devices.capabilities.on_off In this capability you can control the device power on/off instance overview powerSwitch powerSwitch description of this capability the parameters object defines how to pass parameters to control device { \"sku\": \"H713B\", \"device\": \"AC:3b:D4:ad:FC:b5:BA:CC\", \"capabi..."
tags:
  - "clippings"
---
## On\_off

`devices.capabilities.on_off`

In this capability you can control the device power on/off

| instance | overview |
| --- | --- |
| powerSwitch | powerSwitch |

- description of this capability

the parameters object defines how to pass parameters to control device

- example of request
- parameters

| field | type | required | overview |
| --- | --- | --- | --- |
| requestId | String | Yes | unique id in this request, will be carried back in response body |
| payload | Object | \-- | request payload |
| payload.sku | String | Yes | the product model |
| payload.device | String | Yes | the device id |
| payload.capability | Object | \-- | the device capability to be controlled |
| capability.type | String | Yes | the type of this capability |
| capability.instance | String | Yes | the instance of this capability e.g. powerSwitch, |
| capability.value | String | Yes | the control value of this instance, defin in '/router/api/v1/user/devices', see the parameters |

## Toggle

`devices.capabilities.toggle`

In this capability you can control the device small switch like oscillation,nightlight

| instance | overview |
| --- | --- |
| oscillationToggle | used for Fan,Heater,Thermostat |
| nightlightToggle | used for appliances with night light |
| airDeflectorToggle | used for Fan Heater Air Condition |
| gradientToggle | used for Light color gradient |
| thermostatToggle | used for Heater |
| warmMistToggle | used for Humidifier |

- description of this capability

provided two command value 0 is off,1 is on

- example of request

## Color\_setting

`devices.capabilities.color_setting`

- list of instance

| instance | overview |
| --- | --- |
| colorRgb | setting the light color |
| colorTemperatureK | setting the color temperature in Kelvin， |

- example of request

The instance `colorRgb` can change light color，you can get RGB number follow this formula `((r & 0xFF) << 16) | ((g & 0xFF) << 8) | ((b & 0xFF) << 0)`

## Mode

`devices.capabilities.mode`

In this capability you can switch the mode, such as the night light scene

- list of instance

| instance | overview |
| --- | --- |
| nightlightScene | switch the night scene, used for appliance with night light |
| presetScene | used for `devices.types.aroma_diffuser`, preset scenes |

- example description of this capability

provided value options

- example of request

## Range

`devices.capabilities.range`

Manage device parameters that have a range. For example, lamp brightness, sound volume, heater temperature, humidifier humidity

- list of instance

| instance | overview |
| --- | --- |
| brightness | setting the brightness, used for 'devices.types.light' |
| humidity | setting humidity, used for 'devices.types.humidifier' |

- example description of this capability

parameters object defines how to pass parameters to change adjust the range of brightness

- example of request

## Work\_mode

`devices.capabilities.work_mode`

In this capability, you can set the working mode of the device and set its working values.

- list of instance

| instance | overview |
| --- | --- |
| workMode | device work mode |

- example of this capability
- example of request
- value object parameters

| field | type | required | overview |
| --- | --- | --- | --- |
| workMode | Integer | Yes | the temperature Whether to maintain or auto stop.   1\. autoStop,0.maintain,default 0 |
| modeValue | Integer | No | the target temperature to set |

## Segment\_color\_setting

`devices.capabilities.segment_color_setting`

In this capability, you can set color on several segment, when you light strip support segmented color

- list of instance

| instance | overview |
| --- | --- |
| segmentedColorRgb | setting the segmentedColorRgb, |
| segmentedBrightness | setting the segmentedBrightness |

- example of this capability
- example of request

value is a structure, segment is an array, pointing to the segment of the light strip.

- parameters

| field | type | required | overview |
| --- | --- | --- | --- |
| segment | Array | Yes | the segment of the light strip, see govee app |
| brightness | Integer | No | set brightness when instance is segmentedBrightness |
| rgb | Integer | No | set color when instance is segmentedColorRgb, you can get RGB number follow this formula `((r & 0xFF) << 16) \| ((g & 0xFF) << 8) \| ((b & 0xFF) << 0)` |

## Dynamic\_scene

`devices.capabilities.dynamic_scene`

dynamic\_scene means you should edit in govee app such as Scene DIY Snapshot,then get these options from the interface

- list of instance

| instance | overview |
| --- | --- |
| lightScene | light scene in govee app, used for `devices.types.light`,if the scene options is empty, you need to get these scene options dynamically, see Get Dynamic Scene [/router/api/v1/device/scenes](https://developer.govee.com/reference/get-light-scene), |
| diyScene | diy in govee app,used for `devices.types.light`, if the diy options is empty, you need get these dynamically, see Get Dynamic Scene [/router/api/v1/device/diy-scenes](https://developer.govee.com/reference/get-light-scene) |
| snapshot | snapshot list in govee app,used for `devices.types.light`,if the diy options is empty, you should create a snapshot first in govee app |

- example of request

## Music\_setting

`devices.capabilities.music_setting`

You can use this capability to switch music modes，and you can pass sensitivity and autoColor field

- list of instance

| instance | overview |
| --- | --- |
| musicMode | light music in govee app |

- example of this capability
- example of request
- parameters

| field | type | required | overview |
| --- | --- | --- | --- |
| musicMode | Integer | Yes | the music code or music number |
| sensitivity | Integer | No | the sensitivity of |
| autoColor | Integer | No | auto color |
| rgb |  | No | the rgb color `((r & 0xFF) << 16) \| ((g & 0xFF) << 8) \| ((b & 0xFF) << 0)` |

## Temperature\_setting

You can set the temperature and choose whether to stop automatically. In addition, you can also choose the temperature unit.

`devices.capabilities.temperature_setting`

- list of instance

| instance | overview |
| --- | --- |
| targetTemperature | setting the thermostat temperature, used for   'devices.types.heater' or 'devices.types.thermostat' |
| sliderTemperature | setting temperature, used for 'devices.types.kettle' |

- example of this capability

You will pass an structure type value，which describes the parameters required to set the temperature

- example of request
- value object parameters

| field | type | required | overview |
| --- | --- | --- | --- |
| autoStop | Integer | No | the temperature Whether to maintain or auto stop.   1\. autoStop,0.maintain,default 0 |
| temperature | Integer | Yes | the target temperature to set |
| unit | String | No | the temperature unit, Celsius or Fahrenheit,default Celsius |

## failure response

- example of response
- failure reason

| code | overview |
| --- | --- |
| 400 | Missing Parameter |
| 400 | Parameter value cannot be empty |
| 400 | Invalid parameter format |
| 400 | Invalid parameter type |
| 400 | Parameter value out of range |
| 400 | Parameter length does not meet requirements |
| 400 | Duplicate parameter value |
| 404 | Instance Not Fund |
| 404 | device not found |
| 429 | too many request,the limits |

- Friendly Reminder

if the request response 429, means request limits happens, 10000/Account/Day
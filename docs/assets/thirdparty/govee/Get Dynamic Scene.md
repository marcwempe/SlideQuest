---
title: "Get Dynamic Scene"
source: "https://developer.govee.com/reference/get-light-scene"
author:
  - "[[Govee Development Platform]]"
published:
created: 2025-11-11
description: "Query Device's Light Scene Query Dynamic Light Scene of the device through device and sku. The scene found by this interface is a dynamic scene. The scene found by getting the device list(Get You Devices) is a static scene, but their control methods are the same. The reason why the scene is divided ..."
tags:
  - "clippings"
---
Query Dynamic Light Scene of the device through device and sku. The scene found by this interface is a dynamic scene. The scene found by getting the device list(Get You Devices) is a static scene, but their control methods are the same. The reason why the scene is divided into two parts is because the number of dynamic scenes will be relatively large.

- request example

```http
POST /router/api/v1/device/scenes HTTP/1.1
Host: https://openapi.api.govee.com
Content-Type: application/json
Govee-API-Key: xxxx

{
    "requestId": "uuid",
    "payload": {
        "sku": "H618E",
        "device": "8C:2E:9C:04:A0:03:82:D1"
    }
}
```

- response success example

```json
{
    "requestId": "uuid",
    "msg": "success",
    "code": 200,
    "payload": {
        "sku": "H6057",
        "device": "2F:56:C1:9A:7C:E8:5B:19",
        "capabilities": [
            {
                "type": "devices.capabilities.dynamic_scene",
                "instance": "lightScene",
                "parameters": {
                    "dataType": "ENUM",
                    "options": [
                        {
                            "name": "Sunrise",
                            "value": {
                                "paramId": 4280,
                                "id": 3853
                            }
                        },
                        {
                            "name": "Sunset",
                            "value": {
                                "paramId": 4281,
                                "id": 3854
                            }
                        },
                        {
                            "name": "Sunset Glow",
                            "value": {
                                "paramId": 4282,
                                "id": 3855
                            }
                        },
                        {
                            "name": "Spring",
                            "value": {
                                "paramId": 4283,
                                "id": 3856
                            }
                        },
                        {
                            "name": "Aurora",
                            "value": {
                                "paramId": 4284,
                                "id": 3857
                            }
                        },
                        {
                            "name": "Rainbow",
                            "value": {
                                "paramId": 4285,
                                "id": 3858
                            }
                        },
                        {
                            "name": "Forest",
                            "value": {
                                "paramId": 4286,
                                "id": 3859
                            }
                        },
                        {
                            "name": "Ocean",
                            "value": {
                                "paramId": 4287,
                                "id": 3860
                            }
                        },
                        {
                            "name": "Snowing",
                            "value": {
                                "paramId": 4288,
                                "id": 3861
                            }
                        },
                        {
                            "name": "Spring Wind",
                            "value": {
                                "paramId": 4289,
                                "id": 3862
                            }
                        },
                        {
                            "name": "Cloudy",
                            "value": {
                                "paramId": 4290,
                                "id": 3863
                            }
                        },
                        {
                            "name": "Firefly",
                            "value": {
                                "paramId": 4291,
                                "id": 3864
                            }
                        },
                        {
                            "name": "Fire",
                            "value": {
                                "paramId": 4292,
                                "id": 3865
                            }
                        },
                        {
                            "name": "Waterfall",
                            "value": {
                                "paramId": 4293,
                                "id": 3866
                            }
                        },
                        {
                            "name": "Falling Petals",
                            "value": {
                                "paramId": 4294,
                                "id": 3867
                            }
                        },
                        {
                            "name": "Wave",
                            "value": {
                                "paramId": 4295,
                                "id": 3868
                            }
                        },
                        {
                            "name": "Raining",
                            "value": {
                                "paramId": 4296,
                                "id": 3869
                            }
                        },
                        {
                            "name": "Falling Leaves",
                            "value": {
                                "paramId": 4297,
                                "id": 3870
                            }
                        },
                        {
                            "name": "River",
                            "value": {
                                "paramId": 4298,
                                "id": 3871
                            }
                        },
                        {
                            "name": "Water Drop",
                            "value": {
                                "paramId": 4299,
                                "id": 3872
                            }
                        },
                        {
                            "name": "Morning",
                            "value": {
                                "paramId": 4300,
                                "id": 3873
                            }
                        },
                        {
                            "name": "Afternoon",
                            "value": {
                                "paramId": 4301,
                                "id": 3874
                            }
                        },
                        {
                            "name": "Leisure",
                            "value": {
                                "paramId": 4302,
                                "id": 3875
                            }
                        },
                        {
                            "name": "Refreshing",
                            "value": {
                                "paramId": 4303,
                                "id": 3876
                            }
                        },
                        {
                            "name": "Marshmallow",
                            "value": {
                                "paramId": 4304,
                                "id": 3877
                            }
                        },
                        {
                            "name": "Fish tank",
                            "value": {
                                "paramId": 4305,
                                "id": 3878
                            }
                        },
                        {
                            "name": "Cherry Blossom Festival",
                            "value": {
                                "paramId": 4306,
                                "id": 3879
                            }
                        },
                        {
                            "name": "Candy",
                            "value": {
                                "paramId": 4307,
                                "id": 3880
                            }
                        },
                        {
                            "name": "Strawberry",
                            "value": {
                                "paramId": 4308,
                                "id": 3881
                            }
                        },
                        {
                            "name": "Breathe",
                            "value": {
                                "paramId": 4309,
                                "id": 3882
                            }
                        },
                        {
                            "name": "Gradient",
                            "value": {
                                "paramId": 4310,
                                "id": 3883
                            }
                        },
                        {
                            "name": "Swing",
                            "value": {
                                "paramId": 4311,
                                "id": 3884
                            }
                        },
                        {
                            "name": "Train",
                            "value": {
                                "paramId": 4312,
                                "id": 3885
                            }
                        },
                        {
                            "name": "Candy Crush",
                            "value": {
                                "paramId": 4313,
                                "id": 3886
                            }
                        },
                        {
                            "name": "Gleam",
                            "value": {
                                "paramId": 4314,
                                "id": 3887
                            }
                        },
                        {
                            "name": "Drift",
                            "value": {
                                "paramId": 4315,
                                "id": 3888
                            }
                        },
                        {
                            "name": "Graffiti",
                            "value": {
                                "paramId": 4316,
                                "id": 3889
                            }
                        },
                        {
                            "name": "Blossom",
                            "value": {
                                "paramId": 4317,
                                "id": 3890
                            }
                        },
                        {
                            "name": "Love Heart",
                            "value": {
                                "paramId": 4318,
                                "id": 3891
                            }
                        },
                        {
                            "name": "Fireworks",
                            "value": {
                                "paramId": 4319,
                                "id": 3892
                            }
                        },
                        {
                            "name": "Cheerful",
                            "value": {
                                "paramId": 4320,
                                "id": 3893
                            }
                        },
                        {
                            "name": "Flow",
                            "value": {
                                "paramId": 4321,
                                "id": 3894
                            }
                        },
                        {
                            "name": "Healing",
                            "value": {
                                "paramId": 4322,
                                "id": 3895
                            }
                        },
                        {
                            "name": "Star",
                            "value": {
                                "paramId": 4323,
                                "id": 3896
                            }
                        },
                        {
                            "name": "Accompany",
                            "value": {
                                "paramId": 4324,
                                "id": 3897
                            }
                        },
                        {
                            "name": "Dreamland",
                            "value": {
                                "paramId": 4325,
                                "id": 3898
                            }
                        },
                        {
                            "name": "Night",
                            "value": {
                                "paramId": 4326,
                                "id": 3899
                            }
                        },
                        {
                            "name": "Night Light",
                            "value": {
                                "paramId": 4327,
                                "id": 3900
                            }
                        },
                        {
                            "name": "Venus",
                            "value": {
                                "paramId": 4328,
                                "id": 3901
                            }
                        },
                        {
                            "name": "Earth",
                            "value": {
                                "paramId": 4329,
                                "id": 3902
                            }
                        },
                        {
                            "name": "Mars",
                            "value": {
                                "paramId": 4330,
                                "id": 3903
                            }
                        },
                        {
                            "name": "Jupiter",
                            "value": {
                                "paramId": 4331,
                                "id": 3904
                            }
                        },
                        {
                            "name": "Uranus",
                            "value": {
                                "paramId": 4332,
                                "id": 3905
                            }
                        },
                        {
                            "name": "Milky Way",
                            "value": {
                                "paramId": 4333,
                                "id": 3906
                            }
                        }
                    ]
                }
            }
        ]
    }
}
```

- response field

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
| parameters | Object | the struct definition of current parameter in this instance |

Parameter Define Object

enum control value

| field | data type | desc |
| --- | --- | --- |
| dataType | String | define the data type of control value.   e.g. **ENUM**,INTEGER,STRUCT |
| value | Object | show the options of control value |

- control light scene request

```http
POST /router/api/v1/device/control HTTP/1.1
Host: https://openapi.api.govee.com
Content-Type: application/json
Govee-API-Key: xxxx

{
  "requestId": "xxxx",
  "payload": {
    "sku": "H6057",
    "device": "2F:56:C1:9A:7C:E8:5B:19",
    "capability": {
      "type": "devices.capabilities.dynamic_scene",
      "instance": "lightScene",
      "value": {
          "paramId": 4280,
        "id": 3853                    
      }
    }
  }
}
```

Query Dynamic DIY Scene of the device through device and sku.

- request example

```http
POST /router/api/v1/device/diy-scenes HTTP/1.1
Host: https://openapi.api.govee.com
Content-Type: application/json
Govee-API-Key: xxxx

{
    "requestId": "uuid",
    "payload": {
        "sku": "H618E",
        "device": "8C:2E:9C:04:A0:03:82:D1"
    }
}
```

- response success example

```json
{
    "requestId": "uuid",
    "msg": "success",
    "code": 200,
    "payload": {
        "sku": "H618E",
        "device": "8C:2E:9C:04:A0:03:82:D1",
        "capabilities": [
            {
                "type": "devices.capabilities.diy_color_setting",
                "instance": "diyScene",
                "parameters": {
                    "dataType": "ENUM",
                    "options": [
                        {
                            "name": "Xmas lights 2",
                            "value": 8216931
                        },
                        {
                            "name": "Xmas",
                            "value": 8216930
                        },
                        {
                            "name": "White lights non holid",
                            "value": 8216929
                        },
                        {
                            "name": "test",
                            "value": 8216643
                        }
                    ]
                }
            }
        ]
    }
}
```

- Friendly Reminder  
	if the request response 429, means request limits happens, 10000/Account/Day
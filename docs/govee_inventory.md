# Govee Geräteinventar (Testsetup)

| Name | Gerät-ID | SKU | Gerätetyp | Power-Status | Capabilities |
| --- | --- | --- | --- | --- | --- |
| Stehleuchte Links | EA:A2:D5:33:C4:46:35:84 | H60A1 | devices.types.light | AN | devices.capabilities.on_off (powerSwitch), devices.capabilities.toggle (gradientToggle, dreamViewToggle), devices.capabilities.range (brightness), devices.capabilities.segment_color_setting (segmentedBrightness, segmentedColorRgb), devices.capabilities.color_setting (colorRgb, colorTemperatureK), devices.capabilities.dynamic_scene (lightScene, diyScene, snapshot), devices.capabilities.music_setting (musicMode) |
| Stehleuchte Rechts | DE:25:D5:33:C3:86:23:8C | H60A1 | devices.types.light | AN | wie oben |
| Bildschirm | B6:5A:ED:A6:DA:4F:15:9A | H60A1 | devices.types.light | AN | wie oben |
| Gute Stube Decke Tür | 08:6D:98:17:3C:1B:F9:98 | H60A1 | devices.types.light | AN | devices.capabilities.on_off (powerSwitch), devices.capabilities.range (brightness), devices.capabilities.segment_color_setting (segmentedBrightness, segmentedColorRgb), devices.capabilities.color_setting (colorRgb, colorTemperatureK), devices.capabilities.dynamic_scene (lightScene, diyScene, snapshot) |
| Gute Stube Decke TV | 07:76:98:17:3C:1C:97:F4 | H60A1 | devices.types.light | AN | wie oben |
| Gute Stube (Alle) | 13277625 | H60A1 | devices.types.light | UNBEKANNT | devices.capabilities.on_off (powerSwitch) |
| Gute Stube (Stand) | 13277635 | H60A1 | devices.types.light | UNBEKANNT | devices.capabilities.on_off (powerSwitch) |
| Gute Stube (Decke) | 13277630 | H60A1 | devices.types.light | UNBEKANNT | devices.capabilities.on_off (powerSwitch) |

> Stand: 2025-11-12 22:26 (aus `logs/dev.log`).  
> Power-Status “UNBEKANNT” deutet auf Szenen/Gruppen ohne direkten Status zurück.

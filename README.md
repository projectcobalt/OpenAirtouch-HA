# OpenAirTouch Home Assistant Integration

Native Home Assistant entities for an OpenAirTouch add-on instance.

This integration talks to the OpenAirTouch add-on HTTP API and creates Home
Assistant entities from the runtime state:

- AC heads as climate entities.
- Sensor-backed zones as climate entities.
- Zone dampers as cover entities.
- Useful temperatures, percentages, errors, and low-battery states as support entities.

The add-on remains the protocol/runtime owner. This integration is only the
Home Assistant facade.

## Development install

Copy `custom_components/openairtouch` into a Home Assistant `custom_components`
directory, restart Home Assistant, then add OpenAirTouch from Settings >
Devices & services.

Default add-on URL:

```text
http://a0d7b954-openairtouch:8099
```

If the add-on exposes port `8099/tcp`, a direct host/IP URL can also be used.

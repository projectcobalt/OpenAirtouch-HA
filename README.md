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
directory, then restart Home Assistant.

If the OpenAirTouch add-on is installed, Home Assistant should discover it from
the add-on metadata. Accept the discovered OpenAirTouch entry from Settings >
Devices & services.

For manual setup, use the HTTP API URL for your installed add-on instance. On
Home Assistant OS/Supervised installs, the internal hostname usually matches the
add-on slug with underscores replaced by hyphens, for example
`http://<repository>-openairtouch:8099`. If the add-on exposes port `8099/tcp`,
a direct host/IP URL can also be used.

# CC REST API (via cc_json tunnel)

These are HTTP-style calls the app makes to the CC, transported inside
`JsonWebRequest` frames (see [PROTOCOL-AND-TLS.md](PROTOCOL-AND-TLS.md)). The CC forwards
them to its own `http://127.0.0.1:8000`. All bodies are JSON.

**Golden rule:** the CC validates every write against a **JSON Schema** and, on failure,
returns `400` with the **full schema embedded in `errorMessages`**. Use that to discover
exact requirements:

```jsonc
// PATCH /api/rooms/0  with {}  →  400
{ "errorMessages": [
  "JSON content does not conform to JSON Schema.\nSchema:\n\n{ \"title\": \"Room\", ... }"
] }
```

## Read endpoints (GET)

| Path | Returns |
|------|---------|
| `/api/system/info` | `name`, `serialNo`, `version`, `brandingType`, `uptime`, `systemTime`, `autoUpdateSoftware`, `limitPauseDuration` |
| `/api/system/status` | `currentState` (`AtHome`…), `schedule`, `normalSchedule` |
| `/api/system/apiversions` | `[1,2,3,4]` |
| `/api/rooms` | array of rooms (see below) |
| `/api/modes` | array of `{type, state}` for AtHome/Vacation/Pause |
| `/api/alarms` | array of alarms (`id`, `level`, `room`, `node`, `isRead`, `titleTextId`, `createdDate`) |
| `/api/onoffdevices` | array of on/off devices (may be empty) |
| `/api/zones/living` | a zone (see below) |
| `/api/settings/temperature` | temperature settings (incl. `vacationTemperature`) |

### Room object

```json
{
  "id": 0,
  "name": "Living",
  "ambientTemperature": 20.6,
  "setpoint": { "temperature": 21.0, "type": "Adjustable" },
  "regulation": {
    "type": "Schedule",
    "atHomeSetpoint": 20.5,
    "awaySetpoint": 17.0,
    "manualSetpoint": 22.0
  },
  "minSetpoint": 6.0, "maxSetpoint": 35.0,
  "regulationState": "Heating",
  "state": "Normal",
  "zone": "Living",
  "mode": "Schedule",
  "hasTemperatureSensor": true
}
```

### Zone object

```json
{
  "name": "Living",
  "regulationType": "Schedule",
  "rooms": [0, 1],
  "schedule": { "monday": [ { "state": "AtHome",
    "startTimeFromMidnight": "00:00:00", "endTimeFromMidnight": "1.00:00:00" } ], ... }
}
```

## Write endpoints

### `PATCH /api/rooms/<id>` — setpoint / regulation / name / schedule

Schema title `Room`. **`id` is required**, `additionalProperties: false`.

```jsonc
// change the target temperature
PATCH /api/rooms/0
{ "id": 0, "setpoint": { "temperature": 21.0 } }

// change regulation setpoints (only the provided key is sent by the app)
{ "id": 0, "regulation": { "atHomeSetpoint": 20.5 } }
{ "id": 0, "regulation": { "awaySetpoint": 17.0 } }
{ "id": 0, "regulation": { "manualSetpoint": 22.0 } }
{ "id": 0, "regulation": { "type": "Schedule" } }   // "Schedule" | "Manual"

// rename / reorder / move to zone
{ "id": 0, "name": "Living room" }
{ "id": 0, "sortOrder": 3 }
{ "id": 0, "zone": "Living" }

// schedule (per weekday; state "AtHome"|"Away"; times "HH:MM:SS"; end may be "1.00:00:00")
{ "id": 0, "schedule": { "monday": [ { "state": "AtHome",
  "startTimeFromMidnight": "00:00:00", "endTimeFromMidnight": "1.00:00:00" } ] } }
```

### `PUT /api/modes/<athome|vacation|pause|boost>`

Schema title `Mode` (differs per mode). Body always has `type` and `state`.

```jsonc
// simple on/off
PUT /api/modes/pause
{ "type": "Pause", "state": "Active" }      // or "Inactive"

PUT /api/modes/vacation
{ "type": "Vacation", "state": "Active" }   // optional "startTime"/"endTime"

// AtHome activation REQUIRES a non-empty rooms array (minItems: 1)
PUT /api/modes/athome
{ "type": "AtHome", "state": "Active", "rooms": [0, 1, 2] }
```

> Deactivating a mode uses `"state": "Inactive"` (AtHome deactivation does not need
> `rooms`).

### `PATCH /api/zones/living` — zone

Schema title `Zone`. **`name` is required** even if you only change other fields.

```jsonc
PATCH /api/zones/living
{ "name": "Living", "regulationType": "Manual" }   // "Schedule" | "Manual"
{ "name": "Living", "schedule": { "monday": [ ... ] } }
```

### `PATCH /api/onoffdevices/<id>`

Schema title `OnOffDevice`. `id` required.

```jsonc
{ "id": 0, "state": "On" }                          // "On" | "Off"
{ "id": 0, "regulation": "Schedule" }               // "Schedule" | "Manual"
{ "id": 0, "activitySimulationEnabled": true }
{ "id": 0, "schedule": { "monday": [ { "state": "On",
  "startTimeFromMidnight": "07:00:00", "endTimeFromMidnight": "22:00:00" } ] } }
```

### `PATCH /api/settings/temperature`

```jsonc
{ "vacationTemperature": { "setpoint": 15.0 } }
```

### `PATCH /api/system/info`

```jsonc
{ "name": "My home" }
```

### Alarms

`PATCH /api/alarms/<id>` toggles read state (schema `Alarm`).

## Notes

- Time patterns: `startTimeFromMidnight` `^(\d{2}):(\d{2}):(\d{2})$`;
  `endTimeFromMidnight` `^1\.00:00:00$|^((\d{2}):(\d{2}):(\d{2}))$` (the `1.` prefix
  means “end of day / midnight”).
- `additionalProperties: false` — never send unknown keys.
- The integration's `DanfossLinkCoordinator.async_request(uri, method, content)` wraps all
  of this and refreshes entities afterwards.

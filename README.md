# Stratasys 3D Printer — Home Assistant Integration

A Home Assistant custom integration that provides local, real-time monitoring and control of Stratasys FDM 3D printers. The integration communicates directly with the printer over your local network with no cloud dependency, exposing a comprehensive set of sensors, controls, and status entities.

Tested on a Stratasys Dimension 768. Other Stratasys FDM models that use the same local socket protocol should also work, though compatibility is not guaranteed.

---

## Table of Contents

- [Features](#features)
- [Entities](#entities)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Changing the Poll Interval After Setup](#changing-the-poll-interval-after-setup)
- [Notes](#notes)
- [License](#license)

---

## Features

- Fully local — no cloud account or Stratasys cloud service required
- Real-time printer status, build progress, and job information
- Detailed temperature monitoring for the part head, support head, and build chamber
- Material and cassette tracking
- Odometer readings (runtime, build time, tip time)
- Chamber light control
- Door latch lock/unlock control
- Configurable polling interval (5 – 600 seconds, default 30 seconds)
- Automatic slow-poll fallback (every 5 minutes) when the printer is offline or unreachable
- Full UI-based setup via the Home Assistant Config Flow — no YAML required

---

## Entities

### Binary Sensor

| Entity | Description |
|---|---|
| Printer Online | Reports whether the printer is reachable on the network (device class: connectivity) |

### Sensors — Printer Status and Build Progress

| Entity | Description |
|---|---|
| Printer Online Status | Text representation of the network reachability state |
| Printer Status | Current printer status string reported by the firmware |
| Internal State | Raw internal state code from the printer |
| Modeler Explanation | Human-readable explanation of the current modeler state |
| Current Layer | The layer currently being printed |
| Total Layers | Total number of layers in the active job |
| Percentage Done | Build completion percentage |
| Elapsed Build Time | Time elapsed since the build started (HH:MM) |
| Estimated Build Time | Estimated total build duration (HH:MM) |
| Estimated Completion Time | Projected date/time when the build will finish |
| Completion Status | Whether the job has completed |

### Sensors — Machine Information

| Entity | Description |
|---|---|
| Model Type | Printer model identifier reported by the firmware |
| Controller Version | Firmware controller version |
| Compatible CMB Version | Compatible CMB (Controller Main Board) version |
| Product Serial | Printer serial number |
| Product Version | Product version string |

### Sensors — Temperatures

| Entity | Description |
|---|---|
| Part Head Current Temp | Measured temperature of the model/part print head |
| Part Head Set Temp | Target temperature for the model/part print head |
| Standby Head Temp | Part head temperature in standby mode |
| Support Head Current Temp | Measured temperature of the support print head |
| Support Head Set Temp | Target temperature for the support print head |
| Standby Support Temp | Support head temperature in standby mode |
| Envelope Current Temp | Measured build chamber/envelope temperature |
| Envelope Set Temp | Target build chamber/envelope temperature |
| Standby Chamber Temp | Chamber temperature in standby mode |

### Sensors — Mechanical State and Positioning

| Entity | Description |
|---|---|
| XY Homed | Whether the XY axes have been homed |
| Z Homed | Whether the Z axis has been homed |
| XY Ready | Whether the XY stage is ready |
| Door Open | Whether the build chamber door is open |
| Door Latched | Whether the door latch is engaged |
| Lights On | Whether the chamber lights are on |
| Z Foam | Z foam sensor state |
| Tip Offset X | X-axis tip offset value |
| Tip Offset Y | Y-axis tip offset value |
| Z Offset | Z-axis offset value |
| Current X Position | Current X-axis carriage position |
| Current Y Position | Current Y-axis carriage position |
| Current Z Position | Current Z-axis platform position |
| Current Curve | Current curve/path value |

### Sensors — Head and Tip Details

| Entity | Description |
|---|---|
| Part Tip | Installed model/part tip identifier |
| Support Tip | Installed support tip identifier |
| Model In Head | Whether model material is loaded in the head |
| Support In Head | Whether support material is loaded in the head |
| Model Latched | Whether the model material is latched |
| Support Latched | Whether the support material is latched |
| Model Motor Enabled | Whether the model filament motor is enabled |
| Support Motor Enabled | Whether the support filament motor is enabled |
| Model Cart Motor Running | Whether the model cartridge motor is running |
| Support Cart Motor Running | Whether the support cartridge motor is running |
| Model Heater PWM | PWM duty cycle of the model head heater |
| Support Heater PWM | PWM duty cycle of the support head heater |
| Chamber Heater | Chamber heater state |

### Sensors — Materials and Cassettes

| Entity | Description |
|---|---|
| Cassette 1 Type | Material type loaded in cassette slot 1 |
| Cassette 2 Type | Material type loaded in cassette slot 2 |
| Part Total Material | Total model material available |
| Support Total Material | Total support material available |
| Part Material Consumed | Model material consumed by the current/last job |
| Support Material Consumed | Support material consumed by the current/last job |

### Sensors — Current Job

| Entity | Description |
|---|---|
| Job Name | Name of the active print job |
| Job Owner | User or system that submitted the job |
| Job ID | Unique job identifier |
| Start Time | Time the job started building |
| Submit Time | Time the job was submitted to the printer |
| Part Material Name | Material name used for the model |
| Support Material Name | Material name used for the support |
| Job Comment | Optional comment attached to the job |
| Pack | Pack identifier for the job |
| Producer | Software that produced the job file |

### Sensors — Odometer

| Entity | Description |
|---|---|
| Run Time Odometer | Total accumulated runtime of the printer |
| Build Time Odometer | Total accumulated build time |
| Tip Time Odometer | Total accumulated tip usage time |

### Sensors — Previous Job

| Entity | Description |
|---|---|
| Previous Job Name | Name of the most recently completed job |

### Switch

| Entity | Description |
|---|---|
| Door Lock | Locks or unlocks the build chamber door latch |

### Light

| Entity | Description |
|---|---|
| Chamber Light | Turns the build chamber light on or off |

---

## Requirements

- Home Assistant 2023.1 or later
- [HACS](https://hacs.xyz) (for the recommended installation method)
- Your Stratasys printer must be reachable on the same local network as your Home Assistant instance
- The printer's network interface must be enabled and configured with a static or reserved IP address

---

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three-dot menu in the top right.
3. Select **Custom repositories**.
4. Add the URL `https://github.com/bnevets27/HA-Stratasys-Monitor` and set the category to **Integration**.
5. Search for **Stratasys** in HACS and install it.
6. Restart Home Assistant.
7. Proceed to [Configuration](#configuration).

### Manual Installation

1. Download or clone this repository.
2. Copy the `custom_components/stratasys/` folder into your Home Assistant configuration directory under `custom_components/stratasys/`.
3. Restart Home Assistant.
4. Proceed to [Configuration](#configuration).

---

## Configuration

1. In Home Assistant, go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Stratasys Printer**.
3. Enter the following details:

| Field | Description | Default |
|---|---|---|
| Host | IP address of your Stratasys printer | — |
| Port | Network port the printer listens on | `53742` |
| Scan Interval | How often to poll the printer, in seconds (5 – 600) | `30` |

4. Click **Submit**. The integration will create a device and all associated entities automatically.

---

## Changing the Poll Interval After Setup

The polling interval can be updated at any time without removing and re-adding the integration:

1. Go to **Settings > Devices & Services**.
2. Find the **Stratasys Printer** integration and click **Configure**.
3. Update the scan interval and save.

---

## Notes

- When the printer is offline or unreachable, all entities will become unavailable and polling will automatically slow to once every 5 minutes to reduce network overhead. Normal polling resumes as soon as the printer responds.
- This integration has been tested against a **Stratasys Dimension 768**. Other Stratasys FDM models using the same local protocol are expected to work but have not been verified.
- If you encounter a model that does not work or behaves unexpectedly, please open an issue at the [issue tracker](https://github.com/bnevets27/HA-Stratasys-Monitor/issues).

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

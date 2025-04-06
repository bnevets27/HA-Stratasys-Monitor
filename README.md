# Stratasys 3D Printer Integration for Home Assistant

This custom integration connects your Stratasys 3D printer to Home Assistant and provides real-time sensors for printer status, temperatures, job progress, and more.

## Features

- Printer Online/Offline status
- Print job name, progress, and completion status
- Head, support, and chamber temperatures
- Material consumption tracking
- Configurable polling interval (default 30 seconds)

## Installation

1. Copy the `stratasys` folder into your Home Assistant `custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via Settings > Devices & Services > "Stratasys Printer".
4. Enter your printer’s IP address, port, and polling interval.

## HACS Installation (Recommended)

1. Add this repository as a custom repository in HACS.
2. Install the Stratasys Printer integration.
3. Restart Home Assistant.
4. Set up via the UI.

## License

This project is licensed under the MIT License.

## Links

- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [HACS Documentation](https://hacs.xyz/docs/)

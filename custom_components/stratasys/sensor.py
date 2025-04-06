from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .printer import StratasysMonitor

SCAN_INTERVAL = timedelta(seconds=30)

def seconds_to_hhmm(seconds):
    """Convert seconds into HH:MM format."""
    if seconds is None:
        return None
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Stratasys sensors based on a config entry."""
    monitor: StratasysMonitor = hass.data[DOMAIN][entry.entry_id]
    
    coordinator = PrinterDataCoordinator(hass, monitor)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        # Core Sensors
        PrinterStatusSensor(coordinator),
        BuildHeadTempSensor(coordinator),
        SupportHeadTempSensor(coordinator),
        ChamberTempSensor(coordinator),
        CurrentLayerSensor(coordinator),
        TotalLayersSensor(coordinator),
        DoorOpenSensor(coordinator),
        LightsOnSensor(coordinator),

        # New Time and Temp Sensors
        ElapsedBuildTimeSensor(coordinator),
        EstimatedBuildTimeSensor(coordinator),
        BuildTimeSensor(coordinator),
        RunTimeOdometerSensor(coordinator),
        BuildTimeOdometerSensor(coordinator),
        StartTimeSensor(coordinator),

        # Additional Temp Sensors
        PartCurrentTempSensor(coordinator),
        SupportCurrentTempSensor(coordinator),
        EnvelopeCurrentTempSensor(coordinator),
        PartSetTempSensor(coordinator),
        SupportSetTempSensor(coordinator),
        EnvelopeSetTempSensor(coordinator),

        # Job Info
        JobNameSensor(coordinator),
        CompletionStatusSensor(coordinator),
        PartMaterialNameSensor(coordinator),
        SupportMaterialNameSensor(coordinator),
        PartConsumedSensor(coordinator),
        SupportConsumedSensor(coordinator),
        PackSensor(coordinator),
    ]

    async_add_entities(sensors, update_before_add=True)

class PrinterDataCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from the printer."""

    def __init__(self, hass: HomeAssistant, monitor: StratasysMonitor):
        """Initialize."""
        super().__init__(
            hass,
            logger=hass.logger,
            name="Stratasys Printer Data",
            update_interval=SCAN_INTERVAL,
        )
        self.monitor = monitor

    async def _async_update_data(self):
        """Fetch data from the printer."""
        try:
            return await self.monitor.get_status()
        except Exception as ex:
            raise Exception(f"Error updating printer data: {ex}")

class StratasysBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for all Stratasys sensors."""

    def __init__(self, coordinator, name, icon, unit=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "stratasys_printer")},
            "name": "Stratasys 3D Printer",
            "manufacturer": "Stratasys",
            "model": "Unknown Model",
        }

# Core Sensors
class PrinterStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Printer Status", "mdi:printer-3d")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("modelerStatus", "Unknown")

class BuildHeadTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Build Head Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildHeadTemp")

class SupportHeadTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Support Head Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildSuptTemp")

class ChamberTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Chamber Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildChamberTemp")

class CurrentLayerSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Current Layer", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("currentLayer")

class TotalLayersSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Total Layers", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("totalLayers")

class DoorOpenSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Door Open", "mdi:door-open")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("doorOpen")

class LightsOnSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Lights On", "mdi:lightbulb-on")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("lightsOn")

# Time and Odometer Sensors
class ElapsedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Elapsed Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("general", {}).get("elapsedBuildTime")
        return seconds_to_hhmm(seconds)

class EstimatedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Estimated Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("currentJob", {}).get("estimatedBuildTime")
        return seconds_to_hhmm(seconds)

class BuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("currentJob", {}).get("buildTime")
        return seconds_to_hhmm(seconds)

class RunTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Run Time Odometer", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("mariner", {}).get("runTimeOdometer")
        return seconds_to_hhmm(seconds)

class BuildTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Build Time Odometer", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("mariner", {}).get("buildTimeOdometer")
        return seconds_to_hhmm(seconds)

class StartTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Start Time", "mdi:clock-start")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("general", {}).get("startTime")
        if seconds and seconds > 0:
            return datetime.utcfromtimestamp(seconds).isoformat()
        return None

# Additional Temp Sensors
class PartCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Part Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partCurrentTemp")

class SupportCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Support Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportCurrentTemp")

class EnvelopeCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Envelope Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeCurrentTemp")

class PartSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Part Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partSetTemp")

class SupportSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Support Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportSetTemp")

class EnvelopeSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Envelope Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeSetTemp")

# Job Information Sensors
class JobNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Current Job Name", "mdi:format-title")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("jobName")

class CompletionStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Job Completion Status", "mdi:check-decagram")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("completionStatus")

class PartMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Part Material Name", "mdi:label")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partMatlName")

class SupportMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Support Material Name", "mdi:label")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportMatlName")

class PartConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Part Material Consumed", "mdi:weight-gram", "g")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partConsumed")

class SupportConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Support Material Consumed", "mdi:weight-gram", "g")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportConsumed")

class PackSensor(StratasysBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Pack", "mdi:package-variant")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("pack")

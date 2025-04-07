"""Sensor platform for the Stratasys 3D Printer integration."""

from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import PrinterDataCoordinator
from homeassistant.util import slugify

def seconds_to_hhmm(seconds):
    """Convert seconds into HH:MM format."""
    if seconds is None:
        return None
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Stratasys sensors based on a config entry."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        OnlineStatusSensor(coordinator, entry),
        PrinterStatusSensor(coordinator, entry),
        BuildHeadTempSensor(coordinator, entry),
        SupportHeadTempSensor(coordinator, entry),
        ChamberTempSensor(coordinator, entry),
        CurrentLayerSensor(coordinator, entry),
        TotalLayersSensor(coordinator, entry),
        DoorOpenSensor(coordinator, entry),
        LightsOnSensor(coordinator, entry),
        ElapsedBuildTimeSensor(coordinator, entry),
        EstimatedBuildTimeSensor(coordinator, entry),
        BuildTimeSensor(coordinator, entry),
        RunTimeOdometerSensor(coordinator, entry),
        BuildTimeOdometerSensor(coordinator, entry),
        StartTimeSensor(coordinator, entry),
        PartCurrentTempSensor(coordinator, entry),
        SupportCurrentTempSensor(coordinator, entry),
        EnvelopeCurrentTempSensor(coordinator, entry),
        PartSetTempSensor(coordinator, entry),
        SupportSetTempSensor(coordinator, entry),
        EnvelopeSetTempSensor(coordinator, entry),
        JobNameSensor(coordinator, entry),
        CompletionStatusSensor(coordinator, entry),
        PartMaterialNameSensor(coordinator, entry),
        SupportMaterialNameSensor(coordinator, entry),
        PartConsumedSensor(coordinator, entry),
        SupportConsumedSensor(coordinator, entry),
        PackSensor(coordinator, entry),
        ModelerExplanationSensor(coordinator, entry),
    ]

    async_add_entities(sensors, update_before_add=True)

class StratasysBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for all Stratasys sensors."""

    def __init__(self, coordinator, entry, name, icon, unit=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = entry
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_{slugify(name)}"

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Return device info to group sensors under the device."""
        model = self.coordinator.data.get("general", {}).get("modelerType", "Unknown Model")
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Stratasys 3D Printer",
            "manufacturer": "Stratasys",
            "model": model,
        }


# ---------------- Sensor classes ---------------- #

class OnlineStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Printer Online Status", "mdi:lan-connect")

    @property
    def native_value(self):
        return "online" if self.available else "offline"

class PrinterStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Printer Status", "mdi:printer-3d")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("modelerStatus", "Unknown")

class BuildHeadTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Build Head Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildHeadTemp")

class SupportHeadTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Head Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildSuptTemp")

class ChamberTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Chamber Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildChamberTemp")

class CurrentLayerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current Layer", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("currentLayer")

class TotalLayersSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Total Layers", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("totalLayers")

class DoorOpenSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Door Open", "mdi:door-open")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("doorOpen")

class LightsOnSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Lights On", "mdi:lightbulb-on")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("lightsOn")

class ElapsedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Elapsed Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("general", {}).get("elapsedBuildTime")
        return seconds_to_hhmm(seconds)

class EstimatedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Estimated Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("currentJob", {}).get("estimatedBuildTime")
        return seconds_to_hhmm(seconds)

class BuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Build Time", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("currentJob", {}).get("buildTime")
        return seconds_to_hhmm(seconds)

class RunTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Run Time Odometer", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("mariner", {}).get("runTimeOdometer")
        return seconds_to_hhmm(seconds)

class BuildTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Build Time Odometer", "mdi:clock-time-eight-outline")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("mariner", {}).get("buildTimeOdometer")
        return seconds_to_hhmm(seconds)

class StartTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Start Time", "mdi:clock-start")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("general", {}).get("startTime")
        if seconds and seconds > 0:
            return datetime.utcfromtimestamp(seconds).isoformat()
        return None

class PartCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Part Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partCurrentTemp")

class SupportCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportCurrentTemp")

class EnvelopeCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Envelope Current Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeCurrentTemp")

class PartSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Part Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partSetTemp")

class SupportSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportSetTemp")

class EnvelopeSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Envelope Set Temperature", "mdi:thermometer", "°C")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeSetTemp")

class JobNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current Job Name", "mdi:format-title")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("jobName")

class CompletionStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Completion Status", "mdi:check-decagram")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("completionStatus")

class PartMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Part Material Name", "mdi:label")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partMatlName")

class SupportMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Material Name", "mdi:label")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportMatlName")

class PartConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Part Material Consumed", "mdi:weight-gram", "g")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partConsumed")

class SupportConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Material Consumed", "mdi:weight-gram", "g")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportConsumed")

class PackSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Pack", "mdi:package-variant")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("pack")

class ModelerExplanationSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Modeler Explanation", "mdi:information")

    @property
    def native_value(self):
        explanation = self.coordinator.data.get("general", {}).get("modelerExplanation")
        if isinstance(explanation, list):
            return " ".join(explanation)
        return None

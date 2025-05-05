"""Sensor platform for the Stratasys 3D Printer integration."""

from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorDeviceClass

from .const import DOMAIN
from .coordinator import PrinterDataCoordinator
from homeassistant.util import slugify

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up Stratasys sensors based on a config entry."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        #  Printer Status
        OnlineStatusSensor(coordinator, entry),
        PrinterStatusSensor(coordinator, entry),
        InternalStateSensor(coordinator, entry),
        ModelerExplanationSensor(coordinator, entry),
        CurrentLayerSensor(coordinator, entry),
        TotalLayersSensor(coordinator, entry),
        PercentageDoneSensor(coordinator, entry),
        ElapsedBuildTimeSensor(coordinator, entry),
        EstimatedBuildTimeSensor(coordinator, entry),
        EstimatedCompletionTimeSensor(coordinator, entry),
        CompletionStatusSensor(coordinator, entry),
        #  Machine Info
        ModelTypeSensor(coordinator, entry),
        ControllerVersionSensor(coordinator, entry),
        CompatibleCMBVersionSensor(coordinator, entry),
        ProductSerialSensor(coordinator, entry),
        ProductVersionSensor(coordinator, entry),
        #  Temperature Readings
        PartCurrentTempSensor(coordinator, entry),
        PartSetTempSensor(coordinator, entry),
        StandbyHeadTempSensor(coordinator, entry),
        SupportCurrentTempSensor(coordinator, entry),
        SupportSetTempSensor(coordinator, entry),
        StandbySupportTempSensor(coordinator, entry),
        EnvelopeCurrentTempSensor(coordinator, entry),
        EnvelopeSetTempSensor(coordinator, entry),
        StandbyChamberTempSensor(coordinator, entry),
        #  Mechanical Positioning & States
        XYHomedSensor(coordinator, entry),
        ZHomedSensor(coordinator, entry),
        XYReadySensor(coordinator, entry),
        DoorOpenSensor(coordinator, entry),
        DoorLatchedSensor(coordinator, entry),
        LightsOnSensor(coordinator, entry),
        ZFoamSensor(coordinator, entry),
        TipOffsetXSensor(coordinator, entry),
        TipOffsetYSensor(coordinator, entry),
        ZOffsetSensor(coordinator, entry),
        CurrentXPositionSensor(coordinator, entry),
        CurrentYPositionSensor(coordinator, entry),
        CurrentZPositionSensor(coordinator, entry),
        CurrentCurveSensor(coordinator, entry),
        #  Head & Tip Details
        PartTipSensor(coordinator, entry),
        SupportTipSensor(coordinator, entry),
        ModelInHeadSensor(coordinator, entry),
        SupportInHeadSensor(coordinator, entry),
        ModelLatchedSensor(coordinator, entry),
        SupportLatchedSensor(coordinator, entry),
        ModelMotorEnabledSensor(coordinator, entry),
        SupportMotorEnabledSensor(coordinator, entry),
        ModelCartMotorRunningSensor(coordinator, entry),
        SupportCartMotorRunningSensor(coordinator, entry),
        ModelHeaterPWMSensor(coordinator, entry),
        SupportHeaterPWMSensor(coordinator, entry),
        ChamberHeaterSensor(coordinator, entry),
        #  Materials
        Cassette1TypeSensor(coordinator, entry),
        Cassette2TypeSensor(coordinator, entry),
        PartTotalMatSensor(coordinator, entry),
        SupportTotalMatSensor(coordinator, entry),
        PartConsumedSensor(coordinator, entry),
        SupportConsumedSensor(coordinator, entry),
        #  Current Job
        JobNameSensor(coordinator, entry),
        JobOwnerSensor(coordinator, entry),
        JobIdSensor(coordinator, entry),
        StartTimeSensor(coordinator, entry),
        SubmitTimeSensor(coordinator, entry),
        PartMaterialNameSensor(coordinator, entry),
        SupportMaterialNameSensor(coordinator, entry),
        JobCommentSensor(coordinator, entry),
        PackSensor(coordinator, entry),
        ProducerSensor(coordinator, entry),
        #  Odometer Readings
        RunTimeOdometerSensor(coordinator, entry),
        BuildTimeOdometerSensor(coordinator, entry),
        TipTimeOdometerSensor(coordinator, entry),
        #  Previous Job
        PreviousJobNameSensor(coordinator, entry),
    ]

    async_add_entities(sensors, update_before_add=True)

def seconds_to_hhmm(seconds):
    """Convert seconds into HH:MM format."""
    if seconds is None:
        return None
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}"

def clean_list(raw):
    """If raw is a list of strings, strip out commas and join with spaces; else return as-is."""
    if isinstance(raw, list):
        return " ".join(item.replace(",", "") for item in raw)
    return raw

class StratasysBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for all Stratasys sensors."""

    def __init__(self, coordinator, entry, name, icon, unit=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = entry
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_{slugify(name)}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        model = self.coordinator.data.get("general", {}).get("modelerType", "Unknown")
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
        raw = self.coordinator.data.get("general", {}).get("modelerStatus", "Unknown")
        return clean_list(raw)


class InternalStateSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Internal State", "mdi:state-machine")

    @property
    def native_value(self):
        state = self.coordinator.data.get("mariner", {}).get("internalState")
        if isinstance(state, str) and state.startswith("stt"):
            return state[3:]
        return state


class ModelerExplanationSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Modeler Explanation", "mdi:information")

    @property
    def native_value(self):
        exp = self.coordinator.data.get("general", {}).get("modelerExplanation")
        if isinstance(exp, list):
            return " ".join(exp)
        return exp


class CurrentLayerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Current Layer", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("currentLayer")


class TotalLayersSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Total Layers", "mdi:layers-triple")

    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("totalLayers")


class PercentageDoneSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Percentage Done", "mdi:percent", "%")

    @property
    def native_value(self):
        data = self.coordinator.data.get("currentJob", {})
        cur = data.get("currentLayer")
        tot = data.get("totalLayers")
        if tot:
            return round((cur or 0) / tot * 100, 1)
        return None


class ElapsedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Job Elapsed Build Time",
            "mdi:clock-time-eight-outline",
        )

    @property
    def native_value(self):
        secs = self.coordinator.data.get("general", {}).get("elapsedBuildTime")
        return seconds_to_hhmm(secs)

class EstimatedBuildTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Job Estimated Build Time",
            "mdi:clock-time-eight-outline",
        )

    @property
    def native_value(self):
        secs = self.coordinator.data.get("currentJob", {}).get("estimatedBuildTime")
        return seconds_to_hhmm(secs)

class EstimatedCompletionTimeSensor(StratasysBaseSensor):
    """Calculated finish time = startTime + estimatedBuildTime."""

    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Estimated Completion Time",
            "mdi:clock-end",
        )
        # Tell HA this is a timestamp so it gets formatted nicely
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        data = self.coordinator.data.get("currentJob", {})
        start = data.get("startTime")
        est   = data.get("estimatedBuildTime")
        if start and est is not None:
            finish_ts = start + est
            return datetime.utcfromtimestamp(finish_ts).isoformat()
        return None

class CompletionStatusSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Job Completion Status",
            "mdi:check-decagram",
        )

    @property
    def native_value(self):
        raw = self.coordinator.data.get("currentJob", {}).get("completionStatus")
        return clean_list(raw)

class ModelTypeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Type", "mdi:shape")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("modelerType")


class ControllerVersionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Controller Version", "mdi:chip")

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("controllerVersion")


class CompatibleCMBVersionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Compatible CMB Version",
            "mdi:application-cog",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("compatibleCMBVersion")


class ProductSerialSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Product Serial", "mdi:barcode")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("productSerialNumber")


class ProductVersionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Product Version", "mdi:package-variant")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("productVersion")


class PartCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator, entry, "Model Current Temperature", "mdi:thermometer", "°C"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partCurrentTemp")


class PartSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator, entry, "Model Build Target Temperature", "mdi:thermometer", "°C"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("partSetTemp")


class StandbyHeadTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator, entry, "Model Standby Temperature", "mdi:thermometer", "°C"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("standbyHeadTemp")


class SupportCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Support Current Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportCurrentTemp")


class SupportSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Support Build Target Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("supportSetTemp")


class StandbySupportTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Support Standby Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("standbySuptTemp")


class EnvelopeCurrentTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Chamber Current Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeCurrentTemp")


class EnvelopeSetTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Chamber Build Target Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("general", {}).get("envelopeSetTemp")


class StandbyChamberTempSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Chamber Standby Temperature",
            "mdi:thermometer",
            "°C",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("standbyChamberTemp")


class XYHomedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "XY Homed", "mdi:crosshairs-gps")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("xyHomed")


class ZHomedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Z Homed", "mdi:axis-z")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("zHomed")


class XYReadySensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "XY Ready", "mdi:terrain")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("xyReady")


class DoorOpenSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Door Open", "mdi:door-open")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("doorOpen")


class DoorLatchedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Door Latched", "mdi:door")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("doorLatch")


class LightsOnSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Lights On", "mdi:lightbulb-on")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("lightsOn")


class ZFoamSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Z Foam Detected", "mdi:water")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("zFoam")


class TipOffsetXSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Tip Offset X", "mdi:axis-x", None)

    @property
    def native_value(self):
        tip = self.coordinator.data.get("mariner", {}).get("tipOffset", [])
        return tip[0] if isinstance(tip, (list, tuple)) and len(tip) >= 1 else None


class TipOffsetYSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Tip Offset Y", "mdi:axis-y", None)

    @property
    def native_value(self):
        tip = self.coordinator.data.get("mariner", {}).get("tipOffset", [])
        return tip[1] if isinstance(tip, (list, tuple)) and len(tip) >= 2 else None


class ZOffsetSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Z Offset", "mdi:axis-z", None)

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("zOffset")


class CurrentXPositionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current X Position", "mdi:crosshairs")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("currentXPosition")


class CurrentYPositionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current Y Position", "mdi:crosshairs")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("currentYPosition")


class CurrentZPositionSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current Z Position", "mdi:crosshairs")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("currentZPosition")


class CurrentCurveSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Current Curve", "mdi:chart-line")

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("currentCurve")

# 🔩 Head & Tip Details -------------------

class PartTipSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Tip", "mdi:tooltip-text")
    @property
    def native_value(self):
        return (
            self.coordinator.data.get("general", {}).get("partTip")
            or self.coordinator.data.get("currentJob", {}).get("partTip")
        )

class SupportTipSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Tip", "mdi:tooltip-text")
    @property
    def native_value(self):
        return (
            self.coordinator.data.get("general", {}).get("supportTip")
            or self.coordinator.data.get("currentJob", {}).get("supportTip")
        )

class ModelInHeadSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model in Head", "mdi:printer-3d")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("modelInHead")

class SupportInHeadSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support in Head", "mdi:printer-3d")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("supportInHead")

class ModelLatchedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Latched", "mdi:lock-check")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("modelLatched")

class SupportLatchedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Latched", "mdi:lock-check")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("supportLatched")

class ModelMotorEnabledSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Motor Enabled", "mdi:cogs")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("modelMotorEn")

class SupportMotorEnabledSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Motor Enabled", "mdi:cogs")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("supportMotorEn")

class ModelCartMotorRunningSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Cart Motor Running", "mdi:run")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("modelCartMotorRunning")

class SupportCartMotorRunningSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Cart Motor Running", "mdi:run")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("supportCartMotorRunning")

class ModelHeaterPWMSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Heater PWM", "mdi:flash", "%")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("headHeater_pwm")

class SupportHeaterPWMSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Heater PWM", "mdi:flash", "%")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("suptHeater_pwm")

class ChamberHeaterSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Chamber Heater", "mdi:fire")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("chamberHeater")


#  Materials -------------------

class Cassette1TypeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Cassette 1 Type", "mdi:package-variant")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("cassette1Type")

class Cassette2TypeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Cassette 2 Type", "mdi:package-variant")
    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("cassette2Type")

class PartTotalMatSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Material Available", "mdi:weight-gram", "g")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partTotalMatl")

class SupportTotalMatSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Material Available", "mdi:weight-gram", "g")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportTotalMatl")

class PartConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Material Consumed", "mdi:weight-gram", "g")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partConsumed")

class SupportConsumedSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Material Consumed", "mdi:weight-gram", "g")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportConsumed")


#  Current Job -------------------

class JobNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Name", "mdi:format-title")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("jobName")

class JobOwnerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Owner", "mdi:account")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("owner")

class JobIdSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job ID", "mdi:identifier")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("jobId")

class StartTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Start Time", "mdi:clock-start")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
    @property
    def native_value(self):
        secs = self.coordinator.data.get("currentJob", {}).get("startTime")
        if secs and secs > 0:
            return datetime.utcfromtimestamp(secs).isoformat()
        return None

class SubmitTimeSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Submit Time", "mdi:clock-end")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
    @property
    def native_value(self):
        secs = self.coordinator.data.get("currentJob", {}).get("submitTime")
        if secs and secs > 0:
            return datetime.utcfromtimestamp(secs).isoformat()
        return None

class PartMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Model Material Name", "mdi:label")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("partMatlName")

class SupportMaterialNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Support Material Name", "mdi:label")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("supportMatlName")

class JobCommentSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Comment", "mdi:comment-text")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("comment")

class PackSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Pack", "mdi:package-variant")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("currentJob", {}).get("pack")
        return clean_list(raw)


class ProducerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Job Producer", "mdi:account-cog")
    @property
    def native_value(self):
        return self.coordinator.data.get("currentJob", {}).get("producer")


#  Odometer Readings -------------------

class RunTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Odometer Run Time",
            "mdi:counter",
            "s"
        )
        self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("runTimeOdometer")


class BuildTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Odometer Build Time",
            "mdi:counter",
            "s"
        )
        self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("buildTimeOdometer")


class TipTimeOdometerSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator,
            entry,
            "Odometer Tip Time",
            "mdi:counter",
            "s"
        )
        self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self):
        return self.coordinator.data.get("mariner", {}).get("tipTimeOdometer")


#  Previous Job -------------------

class PreviousJobNameSensor(StratasysBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Previous Job Name", "mdi:history")
    @property
    def native_value(self):
        name = self.coordinator.data.get("previousJob", {}).get("jobName")
        return name if name else None

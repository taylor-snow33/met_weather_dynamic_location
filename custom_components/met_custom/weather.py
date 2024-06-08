"""Support for Met.no weather service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TIME,
    ATTR_WEATHER_CLOUD_COVERAGE,
    ATTR_WEATHER_DEW_POINT,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_GUST_SPEED,
    ATTR_WEATHER_WIND_SPEED,
    DOMAIN as WEATHER_DOMAIN,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, sun
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.unit_system import METRIC_SYSTEM

from . import MetWeatherConfigEntry
from .const import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_SUNNY,
    ATTR_MAP,
    CONDITIONS_MAP,
    CONF_TRACK_HOME,
    DOMAIN,
    FORECAST_MAP,
)
from .coordinator import MetDataUpdateCoordinator

DEFAULT_NAME = "Met.no"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MetWeatherConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a weather entity from a config_entry."""
    coordinator = config_entry.runtime_data
    entity_registry = er.async_get(hass)

    name: str | None
    is_metric = hass.config.units is METRIC_SYSTEM
    if config_entry.data.get(CONF_TRACK_HOME, False):
        name = hass.config.location_name
    else:
        name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)
        if TYPE_CHECKING:
            assert isinstance(name, str)

    if coordinator:
        async_add_entities(
            [
                MetWeather(
                    coordinator,
                    name,
                    hass.config.latitude,
                    hass.config.longitude,
                    is_metric,
                )
            ]
        )


class MetWeather(SingleCoordinatorWeatherEntity):
    """Implementation of a Met.no weather condition."""

    def __init__(
        self,
        coordinator: MetDataUpdateCoordinator,
        name: str,
        latitude: float,
        longitude: float,
        is_metric: bool,
    ) -> None:
        """Initialise the platform with a data instance and site."""
        super().__init__(coordinator)
        self._attr_name = name
        self._latitude = latitude
        self._longitude = longitude
        self._attr_unique_id = f"{latitude}_{longitude}"
        self._attr_is_metric = is_metric

    @property
    def location_name(self) -> str:
        """Return the name of the location."""
        return self._attr_name

    @property
    def native_temperature(self) -> float | None:
        """Return the platform temperature."""
        return self.coordinator.data.current_weather_data.get(ATTR_MAP[ATTR_WEATHER_TEMPERATURE])

    # Ensure to define other weather properties similarly
    # ...

    def _forecast(self, hourly: bool) -> list[Forecast] | None:
        """Return the forecast array."""
        if hourly:
            met_forecast = self.coordinator.data.hourly_forecast
        else:
            met_forecast = self.coordinator.data.daily_forecast
        required_keys = {"temperature", ATTR_FORECAST_TIME}
        ha_forecast: list[Forecast] = []
        for met_item in met_forecast:
            if not set(met_item).issuperset(required_keys):
                continue
            ha_item = {
                k: met_item[v]
                for k, v in FORECAST_MAP.items()
                if met_item.get(v) is not None
            }
            if ha_item.get(ATTR_FORECAST_CONDITION):
                ha_item[ATTR_FORECAST_CONDITION] = format_condition(
                    ha_item[ATTR_FORECAST_CONDITION]
                )
            ha_forecast.append(ha_item)  # type: ignore[arg-type]
        return ha_forecast

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast(False)

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units."""
        return self._forecast(True)

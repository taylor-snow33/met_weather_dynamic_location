"""The Met Dynamic component."""
from __future__ import annotations

import logging
from typing import TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .coordinator import MetDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["weather"]

class MetWeatherConfigEntry(TypedDict):
    """Config entry for Met Weather."""

    track_home: bool


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Met Dynamic as config entry."""
    if config_entry.data.get("track_home", False) and (
        (not hass.config.latitude and not hass.config.longitude)
        or (
            hass.config.latitude == 52.3731339
            and hass.config.longitude == 4.8903147
        )
    ):
        _LOGGER.warning(
            "Skip setting up Met Weather Dynamic Location integration; No Home location has been set"
        )
        return False

    coordinator = MetDataUpdateCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    if config_entry.data.get("track_home", False):
        coordinator.track_home()

    config_entry.runtime_data = coordinator

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    config_entry.async_on_unload(coordinator.untrack_home)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    async def handle_refresh_service(call: ServiceCall):
        """Handle the service call to refresh data."""
        await coordinator.async_request_refresh()

    async_register_admin_service(hass, DOMAIN, "refresh", handle_refresh_service)

    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data
    if coordinator:
        coordinator.untrack_home()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Data collection service for smart home data crowsourcing."""
from datetime import timedelta
import logging

import async_timeout

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.config_entries import ConfigEntry

# from homeassistant.const import ()
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry

# from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

# from homeassistant.util.dt import now, parse_datetime


_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """
    Deprecated.
    """
    _LOGGER.warning("Loading IPMA via platform config is deprecated")

    async_add_entities([Collector()], True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """TODO"""

    # Migrate old unique_id
    @callback
    def _async_migrator(entity_entry: entity_registry.RegistryEntry):
        # Reject if new unique_id
        if entity_entry.unique_id.count(",") == 2:
            return None

        new_unique_id = "crowsourcerer_data_collector"

        _LOGGER.info(
            "Migrating unique_id from [%s] to [%s]",
            entity_entry.unique_id,
            new_unique_id,
        )
        return {"new_unique_id": new_unique_id}

    await entity_registry.async_migrate_entries(
        hass, config_entry.entry_id, _async_migrator
    )

    async_add_entities([Collector()], True)


class Collector(SwitchEntity):
    """TODO"""

    def __init__(self):
        _LOGGER.debug("init")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """TODO"""
        async with async_timeout.timeout(10):
            _LOGGER.debug("update")

    @property
    def unique_id(self) -> str:
        """Return a unique id."""
        return "crowsourcerer_data_collector"

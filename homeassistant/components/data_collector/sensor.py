"""Data collection service for smart home data crowsourcing."""
from datetime import timedelta, datetime
import logging
from typing import Optional

# from urllib import response
from requests import get

import async_timeout
from homeassistant.components.recorder import history
from homeassistant.components.recorder.util import session_scope

from homeassistant.config_entries import ConfigEntry

# from homeassistant.const import ()
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as ConfigType, entity_registry
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

# from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from homeassistant.components.history import HistoryPeriodView
from homeassistant.util import dt as dt_util

# from homeassistant.util.dt import now, parse_datetime
from homeassistant.const import (
    HTTP_BEARER_AUTHENTICATION,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=24)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """
    Deprecated.
    """
    async_add_entities([Collector(hass)], True)


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
        new_unique_id = "crowsourcerer_data_collector_2"
        _LOGGER.info(
            "Migrating unique_id from [%s] to [%s]",
            entity_entry.unique_id,
            new_unique_id,
        )
        return {"new_unique_id": new_unique_id}

    await entity_registry.async_migrate_entries(
        hass, config_entry.entry_id, _async_migrator
    )
    async_add_entities([Collector(hass)], True)


class Collector(Entity):
    """TODO"""

    def __init__(self, hass):
        super().__init__()
        self.hass = hass
        self._name = "Home"
        # self._state = "..."
        self._available = True
        _LOGGER.debug("init")

    @property
    def name(self) -> str:
        """Returns name of the entity"""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """TODO"""

        url = "http://localhost:8123/api/history/period"
        headers = {
            "Authorization": f"Bearer {HTTP_BEARER_AUTHENTICATION}",
            "content-type": "application/json",
        }

        # response = await self.hass.async_add_executor_job(
        #    lambda: get(url, headers=headers)
        # )
        start_date = dt_util.utcnow() - SCAN_INTERVAL

        test = history.state_changes_during_period(
            start_time=start_date, hass=self.hass
        )
        # response = self._get_data_from_history()
        # _LOGGER.debug(response)
        _LOGGER.debug("\n\n\nAAAAAAAAAAAAAAAAAA\n\n\n %s", test)
        print("\n\n\nAAAAAAAAAAAAAAAAAA\n\n\n %s", test)
        async with async_timeout.timeout(10):
            _LOGGER.debug("update")

    @property
    def unique_id(self) -> str:
        """Return a unique id."""
        return "crowsourcerer_data_collector"

    def _get_data_from_history(self):
        """Fetch significant stats from the database as json."""

        with session_scope(hass=self.hass) as session:
            result = self.hass.async_add_executor_job(
                history.get_significant_states_with_session,
                self.hass,
                session,
            )

        result = list(result.result())
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Extracted %d states", sum(map(len, result)))

        return result

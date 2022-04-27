"""Data collection service for smart home data crowsourcing."""
from datetime import timedelta
import logging
from sys import api_version
import requests

import async_timeout
from homeassistant.components.recorder import history
from homeassistant.components.recorder.util import session_scope

from homeassistant.config_entries import ConfigEntry

# from homeassistant.const import ()
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as ConfigType, entity_registry
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

# from homeassistant.components.history import HistoryPeriodView
from homeassistant.util import dt as dt_util


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

BLACKLIST = ["person"]


async def send_data_to_api(local_data):
    api_url = ""  # TODO : gib url
    r = requests.post(api_url, data=local_data)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback  # ,
    # discovery_info: Optional[DiscoveryInfoType] = None,
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
    """Add sensor entity from a config_entry"""
    # Migrate old unique_id
    @callback
    def _async_migrator(entity_entry: entity_registry.RegistryEntry):
        # Reject if new unique_id
        if entity_entry.unique_id == "crowsourcerer_data_collector":
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
    async_add_entities([Collector(hass)], True)


class Collector(Entity):
    """Entity for periodic data collection, anonimization and sending"""

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

    # Ocasionally runs this code.
    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Main execution flow"""

        start_date = dt_util.utcnow() - SCAN_INTERVAL

        raw_data = history.state_changes_during_period(
            start_time=start_date, hass=self.hass
        )

        sensor_data = {}
        for key, value in raw_data.items():
            # print(key, value)
            lst = [key.find(s) for s in BLACKLIST]
            # If one item on the list is not -1, then a blacklisted word was found
            # TODO: check for sensitive information such as location data, names, etc
            if lst.count(-1) != len(lst):
                continue
            sensor_data[key] = [state.as_dict() for state in value]

        print(sensor_data)
        # TODO: check for sensitive information in attributes

        # TODO: send data to API
        # TODO : uncomment this later \/
        # send_data_to_api(VARIABLE_WITH_THE_DATA _TO_SEND)

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

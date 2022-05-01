"""Data collection service for smart home data crowsourcing."""
from datetime import timedelta
import logging
from sys import api_version
import requests

import async_timeout
from homeassistant import config_entries
from homeassistant.components.data_collector.const import TIME_INTERVAL
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
from .const import BLACKLIST, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=TIME_INTERVAL)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


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

    # something = hass.data[DOMAIN][config_entry.data[""]]
    # print(something)

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

        disallowed = []
        entries = self.hass.config_entries.async_entries()
        for entry in entries:
            entry = entry.as_dict()
            print(entry)
            if entry["domain"] == "data_collector":
                for category in entry["options"]:
                    if not entry["options"][category]:
                        disallowed.append(category)
                break
        print(f"Disallow List: {disallowed}")
        start_date = dt_util.utcnow() - SCAN_INTERVAL
        raw_data = history.state_changes_during_period(
            start_time=start_date, hass=self.hass
        )

        sensor_data = {}

        filtered_data = raw_data.copy()
        for key in raw_data.keys():
            if key.split(".")[0] in disallowed:
                filtered_data.pop(key)
        for key, value in filtered_data.items():
            sensor_data[key] = [state.as_dict() for state in value]

        # for key, value in raw_data.items():
        #    # print(key, value)
        #    lst = [key.find(s) for s in BLACKLIST]
        #    # If one item on the list is not -1, then a blacklisted word was found
        #    # TODO: check for sensitive information such as location data, names, etc
        #    if lst.count(-1) != len(lst):
        #        continue
        #    sensor_data[key] = [state.as_dict() for state in value]

        print(filtered_data)

        # TODO: check for sensitive information in attributes

        # TODO: send data to API
        # TODO : uncomment this later \/
        # send_data_to_api(VARIABLE_WITH_THE_DATA _TO_SEND)

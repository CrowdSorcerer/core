"""Data collection service for smart home data crowsourcing."""
import bz2
from copyreg import pickle
from datetime import timedelta
import logging
import lzma
from sys import api_version
import sys
import time
import requests
import json
import zlib
import uuid

import async_timeout
from homeassistant import config_entries
from homeassistant.components import sensor
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
from .const import BLACKLIST, DOMAIN, API_URL

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=TIME_INTERVAL)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


async def compress_data_zlib(data):
    bdata = data.encode("utf-8")
    return zlib.compress(bdata)


async def compress_data_bz2(data):
    bdata = data.encode("utf-8")
    return bz2.compress(bdata)


async def compress_data_lzma(data):
    bdata = data.encode("utf-8")
    return lzma.compress(bdata)


def send_data_to_api(local_data, user_uuid):
    api_url = API_URL  # TODO : gib url
    # print(user_uuid)
    if user_uuid == None:
        return
    r = requests.post(
        api_url,
        data=local_data,
        verify=False,
        headers={"Home-UUID": user_uuid, "Content-Type": "application/octet-stream"},
    )
    # print(r.text)


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
        self.uuid = None

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
            # print(entry)
            if entry["domain"] == "data_collector" and entry["title"] == "options":
                for category in entry["data"]:
                    # print(f"cat: {category}")
                    if category == "uuid":
                        self.uuid = entry["data"][category]
                        # print(f"Uuid is {self.uuid}")

                    elif not entry["data"][category]:
                        # print(f" filtering on {category}")
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

        # print(filtered_data)
        print(sensor_data)

        # json_data = json.dumps(sensor_data.as_dict())
        json_data = json.dumps(sensor_data)

        # end = time.time()
        print(f"Size before compression: {sys.getsizeof(json_data)}")
        # start = time.time()
        compressed = await compress_data_zlib(json_data)
        # end = time.time()
        #
        # print(f"zlib - Size after compression: {sys.getsizeof(compressed)}")
        # print(end - start)
        #
        # start = time.time()
        #
        # compressed = await compress_data_bz2(json_data)
        # end = time.time()
        #
        # print(f"bz2 - Size after compression: {sys.getsizeof(compressed)}")
        # print(end - start)
        #
        # start = time.time()
        #
        # compressed = await compress_data_lzma(json_data)
        # end = time.time()
        #
        # print(f"lzma - Size after compression: {sys.getsizeof(compressed)}")
        # print(end - start)

        # TODO: check for sensitive information in attributes

        # TODO: send data to API
        # TODO : uncomment this later \/

        await self.hass.async_add_executor_job(send_data_to_api, compressed, self.uuid)

    # await send_data_to_api(compressed)

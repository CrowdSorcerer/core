"""Data collection service for smart home data crowdsourcing."""

import functools
import json
from datetime import timedelta, datetime
import logging
import os
import sys
import zlib
from time import time
import regex as re
import requests
import scrubadub
from scrubadub.filth.postalcode import PostalCodeFilth
from random import randint
from homeassistant.components import persistent_notification

import homeassistant.components.recorder as recorder

from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as ConfigType
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import Throttle, dt as dt_util
from homeassistant.helpers.event import (
    async_track_time_change,
)

from .const import API_URL, TIME_INTERVAL, logger

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=TIME_INTERVAL)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})
PT_NAME_LIST = [
    {
        "match": name.strip("\n"),
        "filth_type": "name",
        "ignore_case": True,
        "ignore_partial_word_matches": True,
    }
    for name in open(os.path.join(os.path.dirname(__file__), "pt_names.txt"), "r+")
]
EN_NAME_LIST = [
    {
        "match": name.strip("\n"),
        "filth_type": "name",
        "ignore_case": True,
        "ignore_partial_word_matches": True,
    }
    for name in open(os.path.join(os.path.dirname(__file__), "en_names.txt"), "r+")
]

PT_LOCATION_LIST = [
    {
        "match": name.strip("\n"),
        "filth_type": "name",
        "ignore_case": True,
    }
    for name in open(os.path.join(os.path.dirname(__file__), "locations_pt.txt"), "r+")
]
COUNTRY_LIST = [
    {
        "match": name.strip("\n"),
        "filth_type": "name",
        "ignore_case": True,
        "ignore_partial_word_matches": True,
    }
    for name in open(os.path.join(os.path.dirname(__file__), "countries.txt"), "r+")
]
CUSTOM_BLACKLIST = [
    {
        "match": name.strip("\n"),
        "filth_type": "name",
        "ignore_case": True,
        "ignore_partial_word_matches": True,
    }
    for name in open(
        os.path.join(os.path.dirname(__file__), "custom_blacklist.txt"), "r+"
    )
]

FILTERS = (
    EN_NAME_LIST + PT_NAME_LIST + COUNTRY_LIST + CUSTOM_BLACKLIST + PT_LOCATION_LIST
)  # + PT_LOCATION_LIST TODO : THIS IS THE GUILTY BASTARD - FIND OUT WHY IT NOT WORKING - MAYBE MULTIPLE WORDS PER LINE?

FILTERED_KEYS = ["user_id", "latitude", "longitude", "lon", "lat"]


class PIIReplacer(scrubadub.post_processors.PostProcessor):
    name = "pii_replacer"

    def process_filth(self, filth_list):
        for filth in filth_list:
            filth.replacement_string = "{{REDACTED}}"
        return filth_list


async def compress_data(data):
    return zlib.compress(data.encode("utf-8"))


async def filter_data(data):
    """Filters PII from the data collected"""

    async def custom_filter_keys(data):
        """Filters based on key names"""
        if isinstance(data, dict):
            for key in data:
                if key in FILTERED_KEYS:
                    data[key] = "{{REDACTED}}"
                if isinstance(data[key], (dict, list)):
                    await custom_filter_keys(data[key])

        elif isinstance(data, list):
            for it in data:
                await custom_filter_keys(it)

        return data

    def custom_filter_reg(data):
        """Filters based on Regex Expressions"""
        data = re.sub(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "{{REDACTED}}", data)
        data = re.sub(r"\d{4}[\-]\d{3}", "{{REDACTED}}", data)
        return data

    test = {
        "name": "Joseph Joestar",
        "postal_code": "1234-254",
        "tt": "@handlegoesheere",
        "ph": "3518844228",
        "ip": "127.0.0.1",
        "longitude": "12.34564",
        "latitude": "9328475.3",
        "lon": "1234",
        "lat": "984.2",
    }

    logger.info("Filtering out PII from data.")
    await custom_filter_keys(data)

    scrubber = scrubadub.Scrubber(post_processor_list=[PIIReplacer()])
    scrubber.add_detector(scrubadub.detectors.UserSuppliedFilthDetector(FILTERS))
    data = scrubber.clean(json.dumps(data))

    data = custom_filter_reg(data)

    # Sanitizes data for the Data Lake
    logger.info("Sanitizing the data for Data Lake consumption.")
    data = (
        data.replace(".", "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("*", "_")
        .replace(".", "_")
        .replace("#", "_")
        .replace("%", "_")
        .replace("&", "_")
        .replace("\\\\", "_")
        .replace("+", "_")
        .replace("?", "_")
        .replace("/", "_")
    )
    data = data.replace(" _ ", ":")
    data = re.sub(r"(?<=\d)_(?=\d)", ".", data)
    data = json.loads(data)
    return data


def send_data_to_api(local_data, user_uuid):
    """Sends the data to remote Ingest API"""
    api_url = API_URL

    if (
        local_data != {}
        and local_data != b"{}"
        and local_data != "{}"
        and local_data != b"x\x9c\xab\xae\x05\x00\x01u\x00\xf9"  # I don't know anymore
        and local_data != None
    ):
        if user_uuid == None:
            logger.error(
                "UUID is null - Something's very wrong. Please reinstall the data collector and contact the codeowners!"
            )

            return
        data_size = sys.getsizeof(local_data)
        logger.info("Data Collector is sending data. Size: %d", data_size)
        r = requests.post(
            api_url,
            data=local_data,
            #            verify=False,
            headers={
                "Home-UUID": user_uuid,
                "Content-Type": "application/octet-stream",
            },
        )
        logger.info("Response: %d", r.status_code)
    else:
        logger.info("No data to send.")


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
    async_add_entities([Collector(hass)], True)


class Collector(Entity):
    """Entity for periodic data collection, anonimization and uploading"""

    def __init__(self, hass):
        super().__init__()
        self.hass = hass
        self._name = "Crowdsourcerer"
        self._state = "Idle"
        self._attr_extra_state_attributes = {"test_key": "test_val"}
        self._available = True
        _LOGGER.debug("init")
        self.uuid = None
        self.random_time = [randint(0, 6), randint(0, 59), randint(0, 59)]
        schedule = async_track_time_change(
            self.hass,
            self.async_collect_data,
            self.random_time[0],
            self.random_time[1],
            self.random_time[2],
            # second=40,
        )
        logger.info(
            "Data Collector will run at %dh %dmin %ds",
            self.random_time[0],
            self.random_time[1],
            self.random_time[2],
        )

    @property
    def name(self) -> str:
        """Returns name of the entity"""
        return self._name

    @property
    def state(self) -> str:
        """Returns state of the entity"""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return state attributes"""
        return self._attr_extra_state_attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @callback
    async def async_collect_data(self, *_):
        self._state = "Collecting"
        """Main execution flow"""
        start = time()

        try:
            self.last_ran
        except AttributeError:
            # Should only happen the very first time it's ran.
            # Why not on init? It'd reset the time everytime HA was restarted.
            # Like this we lose one cycle but persist through restarts.
            self.last_ran = dt_util.start_of_local_day()

        logger.info("Data Collector is collecting data, This may take a little bit.")

        allowed = []
        entries = self.hass.config_entries.async_entries()
        for entry in entries:
            entry = entry.as_dict()
            if entry["domain"] == "data_collector" and entry["title"] == "options":
                for category in entry["data"]:
                    if category == "uuid":
                        self.uuid = entry["data"][category]
                        self._attr_extra_state_attributes["uuid"] = entry["data"][
                            category
                        ]
                    elif entry["data"][category]:
                        allowed.append(category)
                break

        if "None" in allowed:
            logger.info("Data Collector is not collecting data due to user choices.")
            return
        elif "All" in allowed:
            allowed = ["All"]
            logger.info(
                "Data Collector is collecting data from all sensors due to user choices."
            )

        logger.info(f"Sending data from the following goups: %s ", str(allowed))

        start_date = self.last_ran

        raw_data = await recorder.get_instance(self.hass).async_add_executor_job(
            functools.partial(
                state_changes_during_period, start_time=start_date, hass=self.hass
            )
        )

        sensor_data = {}
        filtered_data = raw_data.copy()

        for key in raw_data.keys():
            if (
                key.split(".")[0] not in allowed and "All" not in allowed
            ):  # and not key == f"sensor.{self._name.lower()}":
                filtered_data.pop(key)

        for key, value in filtered_data.items():
            sensor_data[key] = [state.as_dict() for state in value]

        if sensor_data == {}:
            logger.warn("No Data found for this time interval.")
            return

        with open(os.path.join(os.path.dirname(__file__), "unclean.json"), "w+") as f:
            f.write(str(sensor_data))

        filtered = await filter_data(sensor_data)

        with open(os.path.join(os.path.dirname(__file__), "clean.json"), "w+") as f:
            f.write(str(filtered))
        json_data = json.dumps(filtered)
        self._attr_extra_state_attributes["last_sent_data"] = json_data

        logger.info("Data Collector is compressing the data")
        compressed = await compress_data(json_data)

        compressed_size = sys.getsizeof(compressed)
        self._attr_extra_state_attributes["last_sent_size"] = round(
            compressed_size / 1000, 3
        )
        total_size = self._attr_extra_state_attributes.get("total_sent_size", 0)
        self._attr_extra_state_attributes["total_sent_size"] = round(
            total_size + compressed_size / 1000, 3
        )

        curr_day = datetime.today().strftime("%Y-%m-%d")
        self._attr_extra_state_attributes["last_sent_date"] = curr_day
        if "first_sent_date" not in self._attr_extra_state_attributes:
            self._attr_extra_state_attributes["first_sent_date"] = curr_day

        self.last_ran = dt_util.now()
        await self.hass.async_add_executor_job(send_data_to_api, compressed, self.uuid)
        end = time()
        logger.info("Entire process took %d s", (end - start))
        persistent_notification.create(
            self.hass,
            (
                f"Data Collector has sent data to the Data Lake.<br />"
                f"There were {json_data.count('{{REDACTED}}')} pieces of redacted data."
            ),
            title="Data Collector: Data Sent",
            notification_id="data_collector_notification",
        )
        self._state = "Idle"

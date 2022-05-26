"""Data collection service for smart home data crowdsourcing."""

import json
from datetime import timedelta, datetime
import logging
import os
import sys
import zlib

import regex as re
import requests
import scrubadub


from homeassistant.components.data_collector.const import TIME_INTERVAL
from homeassistant.components.recorder import history
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as ConfigType
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import Throttle, dt as dt_util

from .const import API_URL

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
        "ignore_partial_word_matches": True,
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
# CUSTOM_FILTER = [{"match": ', "user_id', "filth_type": "name", "match_end": ","}]

FILTERS = EN_NAME_LIST + PT_NAME_LIST  #  + CUSTOM_FILTER
FILTERED_KEYS = ["user_id", "last_changed", "last_updated"]


class PIIReplacer(scrubadub.post_processors.PostProcessor):

    name = "pii_replacer"

    def process_filth(self, filth_list):

        for filth in filth_list:
            filth.replacement_string = "REDACTED"

        return filth_list


async def compress_data(data):
    bdata = data.encode("utf-8")
    return zlib.compress(bdata)


async def filter_data(data):
    async def custom_filter_keys(data):
        if isinstance(data, dict):
            for key in data:

                if not isinstance(data[key], str):
                    if isinstance(data[key], dict):

                        await custom_filter_keys(data[key])
                    if isinstance(data[key], list):
                        for el in data[key]:
                            await custom_filter_keys(el)
                else:

                    if key in FILTERED_KEYS:
                        # print("redacting")
                        data[key] = "{{REDACTED}}"
        else:
            if isinstance(data, list):
                for it in data:

                    await custom_filter_keys(it)
            else:

                if data in FILTERED_KEYS:
                    print("redacting")
                    data[key] = """{{REDACTED}}"""
        return data

    async def sanitize(data, to_replace):
        if isinstance(data, dict):
            for key in data:
                if key.contains(":"):
                    to_replace[key] = key.replace(":", "_")

                if not isinstance(data[key], str):
                    if isinstance(data[key], dict):
                        if data[key].contains(":"):

                            to_replace[data[key]] = data[key].replace(":", "_")

                        await sanitize(data[key], to_replace)
                    if isinstance(data[key], list):
                        for el in data[key]:
                            if el.contains(":"):
                                to_replace[el] = el.replace(":", "_")

                            await sanitize(el, to_replace)
                else:
                    if el.contains(":"):
                        to_replace[el] = el.replace(":", "_")
        else:
            if isinstance(data, list):
                for it in data:
                    if el.contains(":"):
                        to_replace[el] = el.replace(":", "_")

                    await sanitize(it, to_replace)
            else:
                if el.contains(":"):
                    to_replace[el] = el.replace(":", "_")

        return to_replace

    def custom_filter_reg():
        ip = r"/^[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+$/"
        postal_PT = r"\d{4}([\-]\d{3})?"

    # For filter testing (checks if working in nested lists/dicts)
    ## meantest = [
    #    {
    #        "eter": [
    #            {"a": "aaaa"},
    #            {
    #                "user_id": "asd",
    #                "test": {
    #                    "user_id": "das",
    #                    "tertert": [
    #                        {"user_id": "dasdasd"},
    #                        {"asdasd": {"asdasd": "2324", "user_id": "234245456"}},
    #                    ],
    #                },
    #            },
    #        ]
    #    }
    # ]

    # it = (
    #                    it.replace(".", "_")
    #                    .replace("<", "_")
    #                    .replace(">", "_")
    #                    .replace("*", "_")
    #                    .replace("#", "_")
    #                    .replace("%", "_")
    #                    .replace("&", "_")
    #                    .replace(":", "_")
    #                    .replace("\\\\", "_")
    #                    .replace("+", "_")
    #                    .replace("?", "_")
    #                    .replace("/", "_")
    #                )

    data = await custom_filter_keys(data)
    # print("data before scrub")
    # print(data)
    scrubber = scrubadub.Scrubber(post_processor_list=[PIIReplacer()])

    test = {
        "name": "Joseph Joestar",
        "postal_code": "1234-254",
        "tt": "@handlegoesheere",
        "ph": "3518844228",
    }

    scrubber.add_detector(scrubadub.detectors.UserSuppliedFilthDetector(FILTERS))

    # TODO Check if we can use this detector -> dependency has a
    # v e r y large file size!
    # scrubber.add_detector(scrubadub_spacy.detectors.AddressDetector)
    data = scrubber.clean(json.dumps(data))

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
    print(data)

    data = data.replace(" _ ", ":")
    data = re.sub(r"(?<=\d)_(?=\d)", ".", data)

    print("replaced")
    print(data)
    data = json.loads(data)
    # to_replace = await sanitize(data, {})
    print("CLEANED UP")
    print(data)
    print("to repl:")
    #    print(to_replace)

    return data


def send_data_to_api(local_data, user_uuid):
    api_url = API_URL  # TODO : gib url
    print("\nSENDING DATA\n\n")
    print(user_uuid)
    if user_uuid == None:
        return
    r = requests.post(
        api_url,
        data=local_data,
        verify=False,
        headers={"Home-UUID": user_uuid, "Content-Type": "application/octet-stream"},
    )
    print(r.text)


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
        self._name = "Crowdsourcerer"
        self._state = "Collecting"
        self._attr_extra_state_attributes = {"test_key": "test_val"}
        self._available = True
        _LOGGER.debug("init")
        self.uuid = None

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
                        self._attr_extra_state_attributes["uuid"] = entry["data"][
                            category
                        ]
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
            if key.split(".")[0] in disallowed or key == f"sensor.{self._name.lower()}":
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
        filtered = await filter_data(sensor_data)

        self._attr_extra_state_attributes["last_sent_data"] = filtered

        json_data = json.dumps(filtered)

        # end = time.time()
        print(f"Size before compression: {sys.getsizeof(json_data)}")
        # start = time.time()
        compressed = await compress_data(json_data)
        # TODO: check for sensitive information in attributes
        print("DAta type:")
        print(type(compressed))

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

        print("current entity uuid:", self._attr_extra_state_attributes["uuid"])
        print("last sent data:", self._attr_extra_state_attributes["last_sent_data"])

        await self.hass.async_add_executor_job(send_data_to_api, compressed, self.uuid)

    # await send_data_to_api(compressed)

"""Config flow for Crowdsourcerer integration."""
from __future__ import annotations

from datetime import timedelta
import functools
import logging
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.components.recorder as recorder
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

# from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector, config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN, TIME_INTERVAL, logger

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=TIME_INTERVAL)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # generates the ui
        vol.Required("name"): str,
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Optional("SomeOption"): bool,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crowdsourcerer."""

    VERSION = 1

    def __init__(self):
        """Init ConfigFlowHandler."""
        self._errors = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        logger.info("Data Collector is being setup")

        return CollectorOptionsFlow(config_entry)

    # entrypoint always here
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            logger.info("Data Collector starting config flow")

            start_date = dt_util.utcnow() - SCAN_INTERVAL

            raw_data = await recorder.get_instance(self.hass).async_add_executor_job(
                functools.partial(
                    state_changes_during_period, start_time=start_date, hass=self.hass
                )
            )
            sensor_data = {}

            for key, value in raw_data.items():
                sensor_data[key] = [state.as_dict() for state in value]

            sensors = ["All", "None"] + [
                key
                for key in sensor_data
                if (
                    key != "sensor.crowdsourcerer"
                    and key != "persistent_notification.data_collector_notification"
                )
            ]

            data_schema = vol.Schema(
                {
                    vol.Optional(
                        str("Info") + "_desc"
                    ): "Select below from which entities to send data. This can be changed later via integration options (here)! \n Please keep in mind that 'None' and 'All' override other options, with 'None' taking precedence.",
                    vol.Optional(
                        "sensors",
                    ): cv.multi_select({item: None for item in sensors}),
                }
            )

            return self.async_show_form(step_id="user", data_schema=data_schema)

        errors = {}

        if user_input is not None:
            data = {}
            data["sensors"] = user_input["sensors"]
            data["uuid"] = str(uuid.uuid4())
            print(data)
            return self.async_create_entry(title="options", data=data)

        # should never get here
        self._errors[
            CONF_NAME
        ] = "This configuration has already taken place. You can change your settings in the integration options panel."

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CollectorOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:

            print("Selected Sensors:")
            print(user_input)

            user_uuid = None
            entries = self.hass.config_entries.async_entries()
            for entry in entries:
                entry_d = entry.as_dict()
                if (
                    entry_d["domain"] == "data_collector"
                    and entry_d["title"] == "options"
                ):
                    old_entry = entry
                    for category in entry_d["data"]:
                        if category == "uuid":
                            user_uuid = entry_d["data"][category]
                            break
            user_input["uuid"] = user_uuid

            self.hass.config_entries.async_update_entry(old_entry, data=user_input)
            return self.async_create_entry(title="options", data=user_input)

        start_date = dt_util.utcnow() - SCAN_INTERVAL

        raw_data = await recorder.get_instance(self.hass).async_add_executor_job(
            functools.partial(
                state_changes_during_period, start_time=start_date, hass=self.hass
            )
        )
        sensor_data = {}

        for key, value in raw_data.items():
            sensor_data[key] = [state.as_dict() for state in value]

        sensors = ["All", "None"] + [
            key
            for key in sensor_data
            if key != "sensor.crowdsourcerer"
            and key != "persistent_notification.data_collector_notification"
        ]
        if "persistent_notification.data_collector_notification" in sensors:
            sensors.pop("persistent_notification.data_collector_notification")

        if "sensor.crowdsourcerer" in sensors:
            sensors.pop("sensor.crowdsourcerer")
        prev_config = []

        entries = self.hass.config_entries.async_entries()
        for entry in entries:
            entry = entry.as_dict()
            if entry["domain"] == "data_collector" and entry["title"] == "options":
                # logger.info(entry)
                prev_config = entry["data"]["sensors"]
                break

        data_schema = vol.Schema(
            {
                vol.Optional(
                    str("Info") + "_desc"
                ): "Select below from which entities to send data. Please keep in mind that 'All' and 'None' override all other options, with 'None' taking precedence.",
                vol.Optional(
                    "sensors",
                    description={"suggested_value": prev_config},
                ): cv.multi_select({item: None for item in sensors}),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


# selector.selector( {"select": {"options": sensors}}

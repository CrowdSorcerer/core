"""Config flow for Crowdsourcerer integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import history

# from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .const import BLACKLIST, DOMAIN, TIME_INTERVAL

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
        return CollectorOptionsFlow(config_entry)

    # entrypoint always here
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            start_date = dt_util.utcnow() - SCAN_INTERVAL

            raw_data = history.state_changes_during_period(
                start_time=start_date, hass=self.hass
            )
            sensor_data = {}

            for key, value in raw_data.items():
                sensor_data[key] = [state.as_dict() for state in value]

            sensors = [key.split(".")[0] for key in sensor_data]

            config_schema_list = {}
            for item in sensors:
                config_schema_list[vol.Optional(str(item) + "_desc")] = item

                config_schema_list[
                    vol.Required(item, description={"suggested_value": ""})
                ] = bool
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(config_schema_list),
            )

        errors = {}

        # try:
        #    info = await validate_input(self.hass, user_input)
        # except CannotConnect:
        #    errors["base"] = "cannot_connect"
        # except InvalidAuth:
        #    errors["base"] = "invalid_auth"
        # except Exception:  # pylint: disable=broad-except
        #    _LOGGER.exception("Unexpected exception")
        #    errors["base"] = "unknown"
        # else:
        #    return self.async_create_entry(title=info["title"], data=user_input)

        if user_input is not None:
            print(f"user input: {user_input}")
            # if user_input[CONF_NAME] not in self.hass.config_entries.async_entries(
            #    DOMAIN
            # ):
            user_input["uuid"] = str(uuid.uuid4())
            print(f"User input: {user_input}")
            # self.hass.data[DOMAIN]["UUID"] = uuid.uuid4()
            return self.async_create_entry(title="options", data=user_input)

        # should never get here, unsure how to solve?
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
            bl = []
            for entry in user_input:
                if not user_input[entry]:
                    bl.append(entry)

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
                        print(f"cat: {category}")
                        if category == "uuid":
                            user_uuid = entry_d["data"][category]
                        break
            user_input["uuid"] = user_uuid
            self.hass.config_entries.async_update_entry(old_entry, data=user_input)
            return self.async_create_entry(title="options", data=user_input)

        start_date = dt_util.utcnow() - SCAN_INTERVAL

        raw_data = history.state_changes_during_period(
            start_time=start_date, hass=self.hass
        )
        sensor_data = {}

        for key, value in raw_data.items():
            sensor_data[key] = [state.as_dict() for state in value]

        sensors = [key.split(".")[0] for key in sensor_data]

        config_schema_list = {}
        for item in sensors:
            config_schema_list[vol.Optional(str(item) + "_desc")] = item

            config_schema_list[
                vol.Required(item, description={"suggested_value": ""})
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(config_schema_list),
        )

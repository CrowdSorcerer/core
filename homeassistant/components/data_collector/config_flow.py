"""Config flow for Crowdsourcerer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries

# from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crowdsourcerer."""

    VERSION = 1

    def __init__(self):
        """Init ConfigFlowHandler."""
        self._errors = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
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
            if user_input[CONF_NAME] not in self.hass.config_entries.async_entries(
                DOMAIN
            ):
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

            self._errors[CONF_NAME] = "name_exists"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

"""Constants for the Crowdsourcerer integration."""
import logging

DOMAIN = "data_collector"

TIME_INTERVAL = 3600  # In seconds (An hour)
BLACKLIST = []
API_URL = "https://smarthouse.av.it.pt/api/ingest/data"
# API_URL = "https://172.18.0.1:8080/api/ingest/data"
logger = logging.getLogger(__package__)

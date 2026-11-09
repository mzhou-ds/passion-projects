"""Retry failed HTTP probes once, with http:// fallback and longer timeout."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
import requests
sys.path.insert(0, "src")
from collect import cdn_from_headers  # noqa

# cdn_from_headers lives in collect.py's main scope; re-define here to avoid import side effects

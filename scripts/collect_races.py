import os
import re
import json
import time
import math
from datetime import datetime, timedelta
import urllib.parse
import requests
from bs4 import BeautifulSoup
from google import genai

os.makedirs("data", exist_ok=True)

HORSES_DB_PATH = "data/horses_db.json"
if os.path.exists(HORSES_DB_PATH):
    try:
        with open(HORSES_DB_PATH, "r", encoding="utf-8") as f:
            horses_db = json.load(f)
    except Exception:
        horses_db = {}
else:
    horses_db = {}

STATS_DB_PATH = "data/stats_db.json"
if os.path.exists(STATS_DB_PATH):
    try:
        with open(STATS_DB_PATH, "r", encoding="utf-8") as f:
            stats_db = json.load(f)
    except Exception:
        stats_db = {}
else:
    stats_db = {}

# 軸馬の信頼度を固定
axis_horse = honmei

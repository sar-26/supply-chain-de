"""Unified Ops Command app — one port, four views, every view stays in its own file.

It imports the four view modules UNCHANGED, harvests their /api routes into one app,
and serves the four pages. A single shared nav bar is swapped into each page at serve
time, so the tabs always match and you never edit the page files for navigation.

Files expected in the same folder as this one:
    db.py
    cockpit_api.py  + cockpit.html
    home_api.py     + home.html
    lists_api.py    + lists.html
    net_api.py      + network.html

Run:   uvicorn app:app --port 8000
Open:  http://localhost:8000   (Home)    /cockpit   /lists   /network
"""
import os
import re
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import cockpit_api   # /api/cockpit/*
import home_api      # /api/home/*
import lists_api     # /api/warehouses, /api/darkstores, /api/open_pos
import net_api       # /api/net/*

app = FastAPI(title="Ops Command")

# Harvest only the /api routes (distinct prefixes, so no collisions). Skipping the
# modules' own "/" and their /docs, /openapi.json keeps this app's own versions.
for mod in (cockpit_api, home_api, lists_api, net_api):
    for route in mod.app.router.routes:
        if getattr(route, "path", "").startswith("/api/"):
            app.router.routes.append(route)

_HERE = os.path.dirname(os.path.abspath(__file__))
_TABS = [("Home", "/home"), ("Cockpit", "/cockpit"), ("Lists", "/lists"), ("Network", "/network")]
_NAV_RE = re.compile(r'<div class="nav">.*?</div>', re.S)   # first (top) nav only


def _nav(active):
    links = "".join(
        f'<a class="on" href="{href}">{label}</a>' if href == active else f'<a href="{href}">{label}</a>'
        for label, href in _TABS)
    return f'<div class="nav">{links}</div>'


def _page(filename, active):
    with open(os.path.join(_HERE, filename), encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(_NAV_RE.sub(lambda _m: _nav(active), html, count=1))


@app.get("/",        response_class=HTMLResponse)
def root():    return _page("home.html", "/home")
@app.get("/home",    response_class=HTMLResponse)
def home():    return _page("home.html", "/home")
@app.get("/cockpit", response_class=HTMLResponse)
def cockpit(): return _page("cockpit.html", "/cockpit")
@app.get("/lists",   response_class=HTMLResponse)
def lists():   return _page("lists.html", "/lists")
@app.get("/network", response_class=HTMLResponse)
def network(): return _page("network.html", "/network")

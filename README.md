# 🚛 Relo-Prep — Free Moving Trip Planner

A free, open-source moving trip planning dashboard built with Python and Streamlit.  
No account required. No ads. No data collected. Works in any browser.

**[▶ Launch the Live App](https://tripplanningapp.streamlit.app/)**

---

## What Is This?

Relo-Prep is a personal moving trip planner designed to take the stress out of a long-distance move with a rental truck and trailer. It was built for real-world use — planning fuel stops, managing cargo weight, tracking weather, and figuring out how much space your stuff actually takes up.

Everything in this app runs on **free, public, open-source data**. No API keys. No subscriptions. No catch.

---

## What It Does

### 🗺️ Route Map
- Enter any origin and destination — the map updates instantly
- Route follows **actual roads and highways** via OSRM (OpenStreetMap routing engine)
- Plots your full route with labeled Safe-Haven stops (truck stops, rest areas, pet parks)
- Toggle a **live NOAA weather radar overlay** directly on the map
- Toggle **live fuel station markers** pulled from OpenStreetMap — filter by:
  - Truck stops only (Love's, Pilot, Flying J, TA, Petro)
  - All gas stations
  - Custom brand selection
  - Corridor width (how far off the highway to search)
  - Mile range (only show stations between mile X and mile Y)

### ⚖️ Load Master
- 60/40 tongue weight calculator — enter your total cargo weight and see exactly how to distribute it front-to-rear on the trailer to prevent sway
- Recommended load zones for every item type
- Live sway risk indicator (green / red)

### 📋 Packing Guard
- Room-by-room guide for where every category of item belongs in the truck and trailer
- Three pre-load checklists: Before You Pack / Loading the Truck / Loading the Trailer
- Vibration risk table by zone — know where your electronics and fragile items are safest

### 📍 Stop Details
- Full stop-by-stop breakdown with rolling fuel tank simulation
- Set your own fuel strategy: refuel at 50% tank, hard limit at 75% used, etc.
- Live fuel level at every stop, automatic ⛽ FILL and ⚠️ TOP OFF flags
- Pet break tracker based on your patience timer setting
- Updates live when you change MPG, fuel price, or destination

### 🌦️ Weather
- Live current conditions at every stop along the route (temperature, wind, precipitation)
- Pulls from Open-Meteo — free weather API, no key required
- Automatic wind advisories: yellow (≥25 mph) and red (≥40 mph) alerts
- Kansas crosswind guide — what to do at each wind speed range

### 📦 Storage Tetris
- 12 room categories, 100+ items with real cubic footage estimates
- Covers everything in a typical 3-bed/2-bath home: all bedrooms, living room, dining room, kitchen, office, bathrooms, laundry, hobby/craft space, pets, and garage
- Packing efficiency slider (accounts for real-world wasted space)
- Live capacity bars for your 26' truck and 6×12 trailer
- Automatically calculates how many **10×20 storage units** you'd need for any overflow

---

## How To Use It

**Online (easiest):**  
Just click the link at the top of this page. No install, no login, no setup.

**Run it locally:**
```bash
# 1. Clone the repo
git clone https://github.com/clanielh/Trip-planner-app.git
cd Trip-planner-app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
streamlit run app.py
```
Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Sidebar Controls

| Control | What it does |
|---|---|
| **Destination** | Type any city, address, or zip — geocodes instantly |
| **Engine MPG** | U-Haul 26' V10 spec is 8–10 loaded; drop for headwind |
| **Regular Gasoline ($/gal)** | Current pump price — updates fuel cost everywhere |
| **Pet Patience Level** | Hours between pet breaks — flags stops in the table |
| **Refuel when tank reaches %** | Your target refuel level (default: 50% = half tank) |
| **Hard limit % used** | Never-exceed threshold — triggers warning flags |
| **Headwind Mode** | Drops MPG to 5.0 for Kansas crosswind conditions |

---

## Vehicle Reference

This app is modeled on the **U-Haul 26' moving truck** towing a **U-Haul 6×12 enclosed trailer**.

| Vehicle | Fuel | Tank | Est. Loaded MPG | Cargo |
|---|---|---|---|---|
| U-Haul 26' truck | Regular 87-oct gasoline | 60 gal | 8–10 mpg | 1,682 cu ft |
| U-Haul 6×12 trailer | — (towed) | — | — | ~375 cu ft |
| **Combined** | | | | **~2,057 cu ft** |
| 10×20 storage unit | — | — | — | 1,600 cu ft |

---

## Data Sources & Tech Stack

Everything used in this app is free, open-source, or public domain.

| Component | Source | License |
|---|---|---|
| App framework | [Streamlit](https://streamlit.io) | Apache 2.0 |
| Maps | [Folium](https://python-visualization.github.io/folium/) + [streamlit-folium](https://github.com/randyzwitch/streamlit-folium) | MIT |
| Map tiles | [CARTO Dark Matter](https://carto.com/basemaps/) via OpenStreetMap | © CARTO / ODbL |
| Road routing | [OSRM](http://project-osrm.org/) (Open Source Routing Machine) | BSD 2-Clause — Free, no key |
| Geocoding | [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap) | ODbL — Free |
| Distance math | [geopy](https://geopy.readthedocs.io/) geodesic | MIT |
| Weather data | [Open-Meteo](https://open-meteo.com/) | CC-BY 4.0 — Free, no key |
| Weather radar | [NOAA / NWS WMS](https://opengeo.ncep.noaa.gov/) | US Public Domain |
| Fuel stations | [OpenStreetMap via Overpass API](https://overpass-api.de/) | ODbL — Free, no key |
| Data tables | [pandas](https://pandas.pydata.org/) | BSD 3-Clause |

**No API keys. No accounts. No cost. No data collected from users.**

---

## Philosophy

This tool was built on the belief that useful software should be free, transparent, and accessible to everyone — not locked behind subscriptions or accounts. Every data source here is either run by a nonprofit (OpenStreetMap Foundation), a government agency (NOAA/NWS), or an open-source community project.

If you find it useful, the best thing you can do is share it.

---

## Contributing

Found a bug? Have a feature idea? Pull requests and issues are welcome.  
Fork the repo, make your changes, and open a PR.

---

## License

MIT License — free to use, modify, and share. See [LICENSE](LICENSE) for details.

---

*Built with Python · Streamlit · OpenStreetMap · NOAA · Open-Meteo*  
*© OpenStreetMap contributors · © CARTO*

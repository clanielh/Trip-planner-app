import math
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

st.set_page_config(
    page_title="Relo-Prep Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .metric-card {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #4fc3f7; }
    .metric-label { font-size: 0.8rem; color: #9e9e9e; text-transform: uppercase; letter-spacing: 1px; }
    .alert-hot { background: #3b1f1f; border-left: 4px solid #ef5350; padding: 10px 14px; border-radius: 6px; margin: 6px 0; }
    .alert-warn { background: #2d2200; border-left: 4px solid #ffb300; padding: 10px 14px; border-radius: 6px; margin: 6px 0; }
    .alert-ok  { background: #1b2f1b; border-left: 4px solid #66bb6a; padding: 10px 14px; border-radius: 6px; margin: 6px 0; }
    div[data-testid="stSidebarContent"] { background-color: #161b27; }
    .tetris-bar-bg { background: #1e2130; border-radius: 6px; height: 22px; width: 100%; }
    .tetris-bar-fill { border-radius: 6px; height: 22px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
TANK_GALLONS = 60
ORIGIN = {"name": "Aurora, CO", "lat": 39.6935, "lon": -104.9847}

TRUCK_CU_FT    = 1682   # 26' truck interior
TRAILER_CU_FT  = 375    # 6×12 enclosed trailer interior
STORAGE_CU_FT  = 1600   # 10×20 unit (200 sq ft × 8' ceiling)

SAFE_HAVENS = [
    {"name": "Strasburg, CO — Sinclair",          "mile": 54,  "lat": 39.7248, "lon": -104.3247,
     "color": "red",    "icon": "tint",     "type": "Fuel",
     "notes": "First easy fuel east of Aurora. Small stop — top off if you didn't start full."},
    {"name": "Limon, CO — Loves Travel Stop",     "mile": 90,  "lat": 39.2647, "lon": -103.6916,
     "color": "red",    "icon": "tint",     "type": "Fuel + Pet",
     "notes": "Full truck stop, pet area, truck lanes. HUB TOUCH STOP — check wheel temps here."},
    {"name": "Burlington, CO — Pilot Flying J",   "mile": 163, "lat": 39.3009, "lon": -102.2693,
     "color": "red",    "icon": "tint",     "type": "Fuel",
     "notes": "Full-service Pilot. Truck lanes. Last CO stop before KS state line."},
    {"name": "Colby, KS — Loves + Dog Park",      "mile": 190, "lat": 39.3958, "lon": -101.0524,
     "color": "green",  "icon": "paw",      "type": "Fuel + Pet",
     "notes": "Loves truck stop with fenced off-leash dog park at Exit 53."},
    {"name": "Oakley, KS — Loves Travel Stop",    "mile": 223, "lat": 39.1281, "lon": -100.8601,
     "color": "red",    "icon": "tint",     "type": "Fuel",
     "notes": "Good backup fuel stop. Truck lanes. Quieter than Colby."},
    {"name": "WaKeeney, KS — I-70 Rest Area",     "mile": 263, "lat": 38.9960, "lon": -99.8770,
     "color": "blue",   "icon": "pause",    "type": "Rest Area",
     "notes": "Picnic tables, pet walk area. No fuel — stretch break only."},
    {"name": "Hays, KS — Loves Travel Stop",      "mile": 330, "lat": 38.8794, "lon": -99.3268,
     "color": "red",    "icon": "tint",     "type": "Fuel + Pet",
     "notes": "Fenced pet area, truck lanes, fuel. Peak Kansas crosswind zone — adjust MPG."},
    {"name": "Russell, KS — Casey's / Cenex",     "mile": 358, "lat": 38.8978, "lon": -98.8584,
     "color": "red",    "icon": "tint",     "type": "Fuel",
     "notes": "Smaller stop with truck parking. Good emergency fuel if needed."},
    {"name": "Ellsworth, KS — I-70 Rest Area",    "mile": 388, "lat": 38.7328, "lon": -98.2280,
     "color": "blue",   "icon": "pause",    "type": "Rest Area",
     "notes": "Rest area with pet walk. No fuel. Good mid-Kansas stretch stop."},
    {"name": "Salina, KS — Petro / Iron Skillet", "mile": 403, "lat": 38.8317, "lon": -97.6500,
     "color": "orange", "icon": "utensils", "type": "Fuel + Food",
     "notes": "Full truck plaza, hot food counter. Recommended full sit-down break."},
    {"name": "Salina, KS — Bill Burke Park",      "mile": 410, "lat": 38.8403, "lon": -97.6114,
     "color": "blue",   "icon": "tree",     "type": "Pet",
     "notes": "Grass fields, great pet break. RALLY POINT for chase vehicles."},
    {"name": "Abilene, KS — Flying J",            "mile": 470, "lat": 38.9178, "lon": -97.2169,
     "color": "red",    "icon": "tint",     "type": "Fuel",
     "notes": "Flying J truck stop. Last major I-70 fuel before heading south toward Fredonia."},
]

# ── Fuel station brand lists ───────────────────────────────────────────────────
TRUCK_STOP_BRANDS = [
    "Love's", "Love's Travel Stop", "Love's Travel Stops",
    "Pilot", "Flying J", "Pilot Flying J",
    "TA", "TravelCenters of America", "TA Travel Center",
    "Petro", "Petro Stopping Centers",
    "Sapp Bros", "Ambest",
]
ALL_FUEL_BRANDS = TRUCK_STOP_BRANDS + [
    "Casey's", "Casey's General Store",
    "Phillips 66", "Conoco", "Sinclair", "Shell", "BP", "Cenex",
    "Kwik Trip", "Kwik Star", "Maverik", "Crossroads", "Valero",
    "Circle K", "Kum & Go", "Stripes", "Pump & Pantry",
]

WMO_CODES = {
    0: ("Clear", "☀️"), 1: ("Mostly Clear", "🌤️"), 2: ("Partly Cloudy", "⛅"), 3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"), 48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy Drizzle", "🌧️"),
    61: ("Light Rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Heavy Rain", "🌧️"),
    71: ("Light Snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy Snow", "❄️"),
    80: ("Showers", "🌦️"), 81: ("Rain Showers", "🌧️"), 82: ("Heavy Showers", "🌧️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Storm + Hail", "⛈️"), 99: ("Severe Storm", "⛈️"),
}

FURNITURE_CATEGORIES = {
    "🛏️ Master Bedroom": [
        ("King Bed Frame",                  45),
        ("King Mattress",                   60),
        ("Queen Bed Frame",                 35),
        ("Queen Mattress",                  40),
        ("Dresser — Large (6-drawer)",      30),
        ("Dresser — Small (4-drawer)",      15),
        ("Chest of Drawers",                20),
        ("Nightstand (each)",                5),
        ("Armoire / Wardrobe",              50),
        ("Vanity + Mirror",                 20),
        ("Bedroom Bench / Ottoman",         10),
        ("Floor / Full-Length Mirror",       8),
        ("Headboard (standalone)",          15),
    ],
    "🛏️ Spare / Guest Bedroom": [
        ("Queen Bed Frame",                 35),
        ("Queen Mattress",                  40),
        ("Twin Bed Frame",                  20),
        ("Twin Mattress",                   18),
        ("Dresser — Small",                 15),
        ("Nightstand (each)",                5),
        ("Bookshelf — Short",               12),
    ],
    "👔 Walk-In Closet": [
        ("Wardrobe Box (hanging clothes)",  15),
        ("Shoe Rack — Large",                8),
        ("Shoe Rack — Small",                4),
        ("Hanging Organizer System",        12),
        ("Storage Ottoman / Bench",         15),
        ("Storage Bins / Baskets (each)",    3),
        ("Hat / Accessory Box",              2),
    ],
    "🛋️ Living Room": [
        ("Sectional Sofa — Large",         120),
        ("Sofa / Couch (3-seat)",           70),
        ("Loveseat",                        45),
        ("Recliner / La-Z-Boy",             25),
        ("Accent Chair",                    20),
        ("Rocking Chair",                   15),
        ("Coffee Table",                    15),
        ("End Table (each)",                 5),
        ("Entertainment Center — Large",    40),
        ("TV Stand / Media Console",        20),
        ("TV — 65\"+ (boxed)",              18),
        ("TV — 55\" (boxed)",              12),
        ("TV — Under 50\" (boxed)",          8),
        ("Bookshelf — Tall",                25),
        ("Bookshelf — Short",               12),
        ("Floor Lamp (each)",                5),
        ("Area Rug — Large (rolled)",       15),
        ("Area Rug — Small (rolled)",        6),
        ("Wall Art / Framed Prints (box)",   5),
    ],
    "🍽️ Dining Room": [
        ("Dining Table — Large (6+ seat)",  45),
        ("Dining Table — Small (4 seat)",   25),
        ("Dining Chair (each)",              8),
        ("Buffet / Sideboard",              30),
        ("China Cabinet / Hutch",           50),
        ("Bar Cart",                        10),
        ("Bar Stool (each)",                 8),
    ],
    "🍳 Kitchen": [
        ("Refrigerator — Full Size",        40),
        ("Refrigerator — Mini / Bar",       10),
        ("Stove / Range",                   20),
        ("Dishwasher (portable/countertop)", 18),
        ("Microwave",                        5),
        ("Kitchen Island / Cart",           20),
        ("Kitchen Table (small)",           15),
        ("Dish Pack Box (fragile)",          5),
        ("Small Appliance Box (toaster, blender, etc.)", 3),
        ("Pantry / Food Staples Box",        3),
        ("Pots, Pans & Cookware Box",        4),
        ("Knife Block + Utensils Box",       2),
    ],
    "🚿 Bathrooms": [
        ("Bathroom Vanity (freestanding)",  15),
        ("Linen Tower / Cabinet",           12),
        ("Medicine Cabinet",                 3),
        ("Towels & Linens Box",              3),
        ("Bathroom Accessories Box",         2),
    ],
    "💼 Office": [
        ("Desk — L-Shape / Large",          50),
        ("Desk — Standard",                 30),
        ("Office Chair",                    15),
        ("Bookshelf — Tall",                25),
        ("Filing Cabinet — 4-drawer",       20),
        ("Filing Cabinet — 2-drawer",       10),
        ("Monitor + Stand (boxed, each)",    5),
        ("Computer Tower",                   3),
        ("Printer / Scanner",                3),
        ("Office Supply Box",                2),
        ("Desk Lamp (each)",                 2),
    ],
    "🧺 Laundry / Utility": [
        ("Washer",                          28),
        ("Dryer",                           28),
        ("Laundry Sorter / Hamper (each)",   5),
        ("Iron + Ironing Board",             5),
        ("Vacuum — Upright",                 5),
        ("Vacuum — Canister / Robot",        3),
        ("Steam Mop / Mop + Bucket",         3),
        ("Cleaning Supply Box",              3),
        ("Broom / Mop Bundle",               2),
    ],
    "🖨️ Hobby — 3D Printing & Minis": [
        ("3D Printer — Large (Creality, etc.)", 8),
        ("3D Printer — Medium",              5),
        ("Resin Printer (MSLA/DLP)",         5),
        ("Resin Wash & Cure Station",        4),
        ("Filament Spool Box (per 10)",      4),
        ("Resin Bottles Box (sealed)",       3),
        ("Warhammer Figure Bin (each)",      3),
        ("Paint Rack + Supplies Box",        3),
        ("Hobby Work Mat + Tools Box",       2),
        ("Carrying Cases / Display Cases",   5),
    ],
    "✂️ Hobby — Leatherwork & Craft": [
        ("Leather Arbor / Book Press",      15),
        ("Leather Press — Large Clamp",     12),
        ("Craft / Cutting Table",           35),
        ("Sewing Machine",                   5),
        ("Sewing Table",                    20),
        ("Leather Hides Roll (each)",        4),
        ("Thread / Notions Box",             2),
        ("Craft Supply Bin (each)",          4),
        ("Yarn / Fabric Storage Bin (each)", 4),
        ("Art Supply Box",                   3),
        ("Pegboard + Hung Tools (flat)",    10),
    ],
    "🐾 Pets": [
        ("XL Dog Crate / Kennel",           20),
        ("Large Dog Crate",                 14),
        ("Medium Dog Crate",                10),
        ("Small Dog / Cat Crate",            5),
        ("Dog Bed — Large (each)",           8),
        ("Dog Bed — Small (each)",           3),
        ("Cat Tree / Scratcher — Tall",     18),
        ("Cat Tree — Small",                 8),
        ("Litter Box + Mat + Supplies",      5),
        ("Aquarium — 75+ gallon (empty)",   40),
        ("Aquarium — 55 gallon (empty)",    28),
        ("Aquarium — 30 gallon (empty)",    15),
        ("Aquarium — 10 gallon (empty)",     8),
        ("Aquarium Stand",                  20),
        ("Pet Food Storage Bin",             5),
        ("Pet Toy Bin (each)",               3),
        ("Pet Carrier (each)",               5),
        ("Pet Supply Box",                   3),
    ],
    "🔧 Garage & Tools": [
        ("Workbench — Large",               50),
        ("Tool Chest / Cabinet — Large",    30),
        ("Tool Cabinet — Small Rolling",    15),
        ("Metal Shelving Unit (each)",      20),
        ("Riding Lawn Mower",               50),
        ("Push Mower",                      15),
        ("Weed Eater / Leaf Blower (each)", 5),
        ("Bike (each)",                     15),
        ("Extension Ladder (20-ft)",        20),
        ("Step Ladder (6-ft, each)",        10),
        ("Generator",                       15),
        ("Air Compressor — Large",          20),
        ("Air Compressor — Small Pancake",   8),
        ("Shop Vac",                         8),
        ("Power Tool Box (each)",            5),
        ("Hand Tool Box",                    5),
        ("Garden Hose + Reel",               5),
        ("Storage Tote — Large (each)",      5),
        ("Gas Cans (empty, each)",           2),
        ("Lumber / PVC / Pipe (bundle)",    10),
    ],
    "📦 Boxes & Packing": [
        ("Book Box (~1.5 cu ft)",            2),
        ("Small Box (~2 cu ft)",             2),
        ("Medium Box (~3 cu ft)",            3),
        ("Large Box (~4.5 cu ft)",           5),
        ("X-Large Box (~6 cu ft)",           6),
        ("Wardrobe Box (hanging clothes)",  15),
        ("Dish Pack / Fragile Box",          5),
        ("Mirror / Artwork Box",             8),
        ("Mattress Bag (bagged flat)",       5),
        ("Oddly Shaped / Misc Box",          4),
    ],
}

# ── Cached API calls ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def geocode_destination(place: str):
    geolocator = Nominatim(user_agent="relo_prep_personal_moving_planner/1.0")
    try:
        loc = geolocator.geocode(place, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception:
        pass
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather(lat: float, lon: float):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,wind_speed_10m,wind_direction_10m,precipitation,weather_code"
        "&wind_speed_unit=mph&temperature_unit=fahrenheit&forecast_days=1"
    )
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return r.json().get("current", {})
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fuel_stations(south: float, west: float, north: float, east: float):
    query = (
        f"[out:json][timeout:30];"
        f'node["amenity"="fuel"]({south:.4f},{west:.4f},{north:.4f},{east:.4f});'
        f"out body;"
    )
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]:
        try:
            r = requests.post(url, data={"data": query}, timeout=35)
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception:
            continue
    return []

def filter_fuel_stations(raw, route_points_latlon, buffer_mi, mile_range, brand_whitelist):
    out = []
    for s in raw:
        lat, lon = s.get("lat"), s.get("lon")
        if lat is None or lon is None:
            continue
        tags  = s.get("tags", {})
        brand = tags.get("brand") or tags.get("name") or "Unknown"
        name  = tags.get("name") or brand

        # Brand filter
        if brand_whitelist:
            match = any(w.lower() in brand.lower() or w.lower() in name.lower()
                        for w in brand_whitelist)
            if not match:
                continue

        # Distance from route corridor
        min_dist = min(geodesic((lat, lon), pt).miles for pt in route_points_latlon)
        if min_dist > buffer_mi:
            continue

        # Approximate mile position: closest route waypoint mile
        closest = min(route_points_latlon, key=lambda pt: geodesic((lat, lon), pt).miles)
        approx_mile = closest[2]  # mile marker stored as 3rd element
        if not (mile_range[0] <= approx_mile <= mile_range[1]):
            continue

        out.append({"lat": lat, "lon": lon, "brand": brand, "name": name,
                    "mile": approx_mile, "dist_mi": round(min_dist, 1)})
    return out

def wind_dir_label(deg):
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]

def weather_row(label, lat, lon):
    w = fetch_weather(lat, lon)
    if not w:
        return {"Stop": label, "Temp (°F)": "—", "Wind": "—", "Precip (in)": "—", "Conditions": "Unavailable"}
    code = w.get("weather_code", 0)
    desc, emoji = WMO_CODES.get(code, ("Unknown", "❓"))
    wind = w.get("wind_speed_10m", 0)
    wdir = wind_dir_label(w.get("wind_direction_10m", 0))
    return {
        "Stop": label,
        "Temp (°F)": f"{w.get('temperature_2m', '—'):.0f}°",
        "Wind": f"{wind:.0f} mph {wdir}",
        "Precip (in)": f"{w.get('precipitation', 0):.2f}\"",
        "Conditions": f"{emoji} {desc}",
        "_wind_raw": wind,
    }

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗺️ Route")
    st.text_input("Origin", value=ORIGIN["name"], disabled=True)
    dest_input = st.text_input(
        "Destination",
        value="Fredonia, KS",
        placeholder="City, State or full address",
        help="Type any destination and press Enter.",
    )

    st.markdown("---")
    st.markdown("## 🚛 Vehicle")
    st.markdown("""
<div style="background:#1e2130;border:1px solid #2d3250;border-radius:8px;padding:10px 14px;font-size:0.82rem;line-height:1.7">
<b>U-Haul 26' Moving Truck</b><br>
Engine: Ford 6.8L V10 · <b>Gasoline</b><br>
Tank: <b>60 gal</b> · Regular 87-octane<br>
Est. loaded MPG: <b>8–10</b> (8 with trailer)<br>
Cargo: 1,682 cu ft interior
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## ⚙️ Trip Parameters")
    mpg = st.slider("Engine MPG", min_value=4.0, max_value=12.0, value=8.0, step=0.5,
                    help="U-Haul V10 spec: 8–10 MPG loaded. Drop to 5–6 for headwind + heavy trailer.")
    fuel_price = st.slider("Regular Gasoline ($/gal)", min_value=3.00, max_value=6.00, value=4.20, step=0.05)
    patience_hours = st.slider("Pet Patience Level (hrs between stops)", min_value=1, max_value=4, value=2)

    st.markdown("**⛽ Fuel Strategy**")
    fuel_at_pct  = st.slider("Refuel when tank reaches (%)", min_value=25, max_value=60, value=50,
                              help="50% = half-tank rule. Stop and top off at any fuel stop once you hit this level.")
    max_pct_used = st.slider("Hard limit — never exceed (% used)", min_value=60, max_value=85, value=75,
                              help="75% used = 25% remaining. Forces a stop even at non-preferred stops.")

    st.markdown("---")
    st.markdown("## 🌬️ Headwind Mode")
    headwind = st.checkbox("Active headwind (drop to 5 MPG)", value=False)
    if headwind:
        mpg = 5.0
        st.warning(f"MPG overridden to {mpg} for crosswind conditions.")

    st.markdown("---")
    st.markdown("## 📋 Pre-Trip Checklist")
    for c in [
        "Trailer hitch pin + safety chains",
        "Running lights & brake lights",
        "Tire pressure (steer/drive/trailer)",
        "Hub touch at first stop (Limon)",
        "Chase vehicles in radio contact",
        "Emergency kit + water for pets",
    ]:
        st.checkbox(c, key=f"check_{c}")

# ── Resolve destination ────────────────────────────────────────────────────────
with st.spinner(f'Looking up "{dest_input}"…'):
    geo = geocode_destination(dest_input.strip())

if geo:
    dest_lat, dest_lon, dest_address = geo
    straight_miles = geodesic((ORIGIN["lat"], ORIGIN["lon"]), (dest_lat, dest_lon)).miles
    TOTAL_MILES = round(straight_miles * 1.10)
    dest_label = dest_input.strip()
    geocode_ok = True
else:
    dest_lat, dest_lon = 37.5239, -95.8274   # Fredonia, KS fallback
    dest_address = "Fredonia, KS (fallback)"
    TOTAL_MILES = 490
    dest_label = "Fredonia, KS"
    geocode_ok = False

# ── Derived fuel calculations ──────────────────────────────────────────────────
range_per_tank     = TANK_GALLONS * mpg
half_tank_miles    = (TANK_GALLONS * fuel_at_pct / 100) * mpg   # miles before preferred refuel
fuel_stops_needed  = max(0, math.ceil(TOTAL_MILES / half_tank_miles) - 1)
total_gallons      = TOTAL_MILES / mpg
total_fuel_cost    = total_gallons * fuel_price

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🚛 Relo-Prep Dashboard")
st.markdown(f"### {ORIGIN['name']} → {dest_label} · ~{TOTAL_MILES} miles")
if not geocode_ok:
    st.warning(f'Could not find "{dest_input}" — showing default route to Fredonia, KS.')

# ── Top metrics ────────────────────────────────────────────────────────────────
def metric_card(col, label, value, sub=""):
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        + (f'<div style="font-size:0.75rem;color:#78909c;margin-top:4px">{sub}</div>' if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )

c1, c2, c3, c4, c5 = st.columns(5)
metric_card(c1, "Total Miles",    f"~{TOTAL_MILES}")
metric_card(c2, "Current MPG",    f"{mpg:.1f}")
metric_card(c3, "Range / Tank",   f"{range_per_tank:.0f} mi")
metric_card(c4, "Fuel Cost",      f"${total_fuel_cost:.0f}", f"{total_gallons:.1f} gal total")
metric_card(c5, "Fuel Stops",     f"{fuel_stops_needed}", f"{fuel_at_pct}% rule · 60-gal gas · V10")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_map, tab_load, tab_packing, tab_stops, tab_weather, tab_tetris = st.tabs([
    "🗺️ Route Map", "⚖️ Load Master", "📋 Packing Guard",
    "📍 Stop Details", "🌦️ Weather", "📦 Storage Tetris",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ROUTE MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    st.subheader(f"Route: {ORIGIN['name']} → {dest_label}")

    # ── Map overlay toggles ────────────────────────────────────────────────
    ov1, ov2 = st.columns(2)
    show_radar    = ov1.toggle("Show NWS Weather Radar", value=False,
                               help="Live NOAA base-reflectivity radar overlay.")
    show_stations = ov2.toggle("Show Fuel Stations", value=False,
                               help="Query OpenStreetMap for gas stations along the route.")

    # ── Fuel station filters (visible only when toggle is on) ──────────────
    station_filter = {}
    if show_stations:
        with st.expander("⛽ Fuel Station Filters", expanded=True):
            fc1, fc2, fc3 = st.columns([2, 1, 1])

            station_mode = fc1.radio(
                "Station type",
                ["Truck stops only", "All gas stations", "Custom brands"],
                horizontal=True,
            )

            buffer_mi = fc2.slider(
                "Corridor width (mi from route)", min_value=1, max_value=25, value=8,
                help="How far off the highway to search for stations.",
            )

            mile_range = fc3.slider(
                "Route section (mile markers)",
                min_value=0, max_value=TOTAL_MILES,
                value=(0, TOTAL_MILES),
                help="Only show stations between these mile markers.",
            )

            if station_mode == "Custom brands":
                selected_brands = st.multiselect(
                    "Select brands to show",
                    options=ALL_FUEL_BRANDS,
                    default=["Love's", "Pilot", "Flying J", "TA", "Petro"],
                )
                brand_whitelist = selected_brands
            elif station_mode == "Truck stops only":
                brand_whitelist = TRUCK_STOP_BRANDS
                st.caption(f"Filtering to: {', '.join(TRUCK_STOP_BRANDS[:6])} + more")
            else:
                brand_whitelist = []  # empty = no brand filter = show all
                st.caption("Showing all gas stations within the corridor.")

            station_filter = {
                "buffer_mi":     buffer_mi,
                "mile_range":    mile_range,
                "brand_whitelist": brand_whitelist,
            }

    # ── Build route points list with mile markers ──────────────────────────
    route_points_latlon = (
        [(ORIGIN["lat"], ORIGIN["lon"], 0)]
        + [(s["lat"], s["lon"], s["mile"]) for s in SAFE_HAVENS]
        + [(dest_lat, dest_lon, TOTAL_MILES)]
    )

    # ── Bounding box for Overpass query ────────────────────────────────────
    all_lats = [p[0] for p in route_points_latlon]
    all_lons = [p[1] for p in route_points_latlon]
    PAD = 0.25  # ~17 miles padding around the bounding box
    bbox = (min(all_lats)-PAD, min(all_lons)-PAD,
            max(all_lats)+PAD, max(all_lons)+PAD)

    # ── Build map ──────────────────────────────────────────────────────────
    center_lat = (ORIGIN["lat"] + dest_lat) / 2
    center_lon = (ORIGIN["lon"] + dest_lon) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB dark_matter")

    if show_radar:
        folium.WmsTileLayer(
            url="https://opengeo.ncep.noaa.gov/geoserver/conus/conus_bref_qcd/ows?",
            name="NWS Base Reflectivity",
            fmt="image/png",
            layers="conus_bref_qcd",
            transparent=True,
            opacity=0.55,
            attr="NOAA / NWS",
        ).add_to(m)
        folium.LayerControl().add_to(m)

    # Route line
    route_coords = [[p[0], p[1]] for p in route_points_latlon]
    folium.PolyLine(route_coords, color="#4fc3f7", weight=3, opacity=0.8, dash_array="8").add_to(m)

    # Origin / destination markers
    folium.Marker(
        [ORIGIN["lat"], ORIGIN["lon"]],
        popup=f"<b>START: {ORIGIN['name']}</b>",
        tooltip=ORIGIN["name"],
        icon=folium.Icon(color="green", icon="home", prefix="fa"),
    ).add_to(m)
    folium.Marker(
        [dest_lat, dest_lon],
        popup=f"<b>DESTINATION: {dest_label}</b><br><small>{dest_address}</small>",
        tooltip=f"Destination: {dest_label}",
        icon=folium.Icon(color="purple", icon="flag", prefix="fa"),
    ).add_to(m)

    # Safe-Haven markers
    for stop in SAFE_HAVENS:
        folium.Marker(
            [stop["lat"], stop["lon"]],
            popup=folium.Popup(
                f"<b>{stop['name']}</b><br>Mile {stop['mile']}<br>{stop['notes']}", max_width=250),
            tooltip=f"Mile {stop['mile']} — {stop['name']}",
            icon=folium.Icon(color=stop["color"], icon=stop["icon"], prefix="fa"),
        ).add_to(m)

    # ── Fuel station markers (OSM / Overpass) ─────────────────────────────
    if show_stations and station_filter:
        with st.spinner("Fetching fuel stations from OpenStreetMap…"):
            raw_stations = fetch_fuel_stations(*bbox)

        filtered = filter_fuel_stations(
            raw_stations,
            route_points_latlon,
            station_filter["buffer_mi"],
            station_filter["mile_range"],
            station_filter["brand_whitelist"],
        )

        # Color-code by type
        def station_color(brand):
            b = brand.lower()
            if any(x in b for x in ["love", "pilot", "flying j", "ta ", "petro", "sapp", "ambest"]):
                return "darkred"
            return "gray"

        for st_node in filtered:
            folium.CircleMarker(
                location=[st_node["lat"], st_node["lon"]],
                radius=5,
                color=station_color(st_node["brand"]),
                fill=True,
                fill_opacity=0.85,
                popup=folium.Popup(
                    f"<b>{st_node['name']}</b><br>"
                    f"Brand: {st_node['brand']}<br>"
                    f"~Mile {st_node['mile']} · {st_node['dist_mi']} mi off route",
                    max_width=220,
                ),
                tooltip=f"⛽ {st_node['name']} (~mi {st_node['mile']})",
            ).add_to(m)

        st.caption(
            f"Found **{len(filtered)}** station(s) matching filters "
            f"({len(raw_stations)} total in corridor). "
            f"🔴 Truck stops  ⚫ General stations  — data © OpenStreetMap contributors"
        )

    st_folium(m, width="100%", height=520)
    st.markdown("> **Hub Touch Protocol** — At Limon (Mile 90), touch each trailer hub. Warm = ✅  Hot = 🚨 Stop.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LOAD MASTER
# ══════════════════════════════════════════════════════════════════════════════
with tab_load:
    st.subheader("⚖️ Load Master — 60/40 Rule Calculator")
    st.markdown("60% of cargo weight must sit **forward of the trailer axle** to prevent highway sway.")

    col_a, col_b = st.columns(2)
    with col_a:
        total_weight    = st.number_input("Total Cargo Weight (lbs)", min_value=0, max_value=20000, value=8000, step=100)
        tongue_weight_pct = st.slider("Front Zone Target (%)", min_value=50, max_value=70, value=60)
    front_target = total_weight * tongue_weight_pct / 100
    rear_target  = total_weight - front_target
    with col_b:
        st.markdown("### Load Distribution")
        st.metric("Front of Axle (tongue weight)", f"{front_target:,.0f} lbs", delta=f"{tongue_weight_pct}% of load")
        st.metric("Rear of Axle",                  f"{rear_target:,.0f} lbs",  delta=f"{100-tongue_weight_pct}% of load")

    st.markdown("---")
    st.markdown("### 📦 Recommended Load Zones")
    st.dataframe(pd.DataFrame([
        {"Zone": "Mom's Attic (cab overhead)", "Items": "Electronics, monitors, fragile boxes", "Reason": "Lowest vibration — best protection for valuables"},
        {"Zone": "Truck Front",               "Items": "Appliances, tool chests, filing cabinets", "Reason": "Weight over front axle stabilizes steering"},
        {"Zone": "Truck Center / Rear",       "Items": "Furniture, mattresses, medium boxes", "Reason": "Largest zone — heaviest on bottom, fill gaps"},
        {"Zone": "Trailer Front (≥60%)",      "Items": "Heavy totes, dressers, garage bins", "Reason": "Tongue weight prevents trailer sway in crosswinds"},
        {"Zone": "Trailer Rear (≤40%)",       "Items": "Soft goods, pillows, rugs, bags",    "Reason": "Light items only — rear-heavy trailers fishtail"},
    ]), use_container_width=True, hide_index=True)

    st.markdown("---")
    if tongue_weight_pct >= 60:
        st.markdown('<div class="alert-ok">✅ <b>Sway Risk: LOW</b> — Tongue weight is within safe range.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-hot">🚨 <b>Sway Risk: HIGH</b> — Increase front loading before departure.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PACKING GUARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_packing:
    st.subheader("📋 Packing Guard — Where Does It Go?")
    st.markdown("Use Storage Tetris to count your cubic footage, then use this tab to decide *where* each category lives in the truck and trailer.")

    # ── Zone reference ──────────────────────────────────────────────────────
    st.markdown("### 🗂️ Zone Guide")
    st.dataframe(pd.DataFrame([
        {"Zone": "🚛 Mom's Attic (cab overhead)",
         "Best Items": "Electronics, monitors, small fragile boxes, valuables, documents",
         "Why": "Lowest road vibration, climate-adjacent, stays dry"},
        {"Zone": "🚛 Truck Front (behind cab)",
         "Best Items": "Heavy appliances (washer, dryer), tool chests, filing cabinets",
         "Why": "Weight over front axle = stable steering; hard floor, no bounce"},
        {"Zone": "🚛 Truck Center / Rear",
         "Best Items": "Furniture, mattresses, dressers, shelving, medium boxes",
         "Why": "Largest zone; stack heaviest on bottom, fill gaps with soft goods"},
        {"Zone": "🚐 Trailer Front (≥60% of load)",
         "Best Items": "Heavy totes, dressers, bookcases, garage bins, pet crates",
         "Why": "Tongue weight prevents sway — keep this zone heavy"},
        {"Zone": "🚐 Trailer Rear (≤40%)",
         "Best Items": "Soft goods, pillows, rugs, bags, lightweight boxes",
         "Why": "Lightest items only — rear-heavy trailers fishtail at speed"},
    ]), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Room-by-room quick ref ──────────────────────────────────────────────
    st.markdown("### 🏠 Room-by-Room Placement")
    st.dataframe(pd.DataFrame([
        {"Room / Category":  "Master Bedroom",   "Furniture": "Bed frame, dresser, nightstands",
         "Goes In": "Truck Center / Trailer Front", "Notes": "Disassemble bed frame; bundle slats, label hardware bags"},
        {"Room / Category":  "Mattresses",        "Furniture": "King, queen, twin",
         "Goes In": "Truck side-wall (vertical)", "Notes": "Stand on edge against wall — never lay flat under load"},
        {"Room / Category":  "Walk-In Closet",    "Furniture": "Wardrobe boxes, shoe racks, bins",
         "Goes In": "Trailer Rear",               "Notes": "Wardrobe boxes stay vertical; lighter end of trailer"},
        {"Room / Category":  "Living Room",       "Furniture": "Sofa, recliner, coffee table, TV",
         "Goes In": "Truck Center",               "Notes": "Sofa on end if possible; wrap TV in blankets before boxing"},
        {"Room / Category":  "Dining Room",       "Furniture": "Table, chairs, hutch",
         "Goes In": "Truck Center / Trailer Front","Notes": "Table top off; chairs stacked seat-to-seat; hutch on its back"},
        {"Room / Category":  "Kitchen",           "Furniture": "Appliances, dish packs, pantry",
         "Goes In": "Truck Front (appliances) / Center (boxes)", "Notes": "Dish packs upright always; fridge doors bungeed open"},
        {"Room / Category":  "Office",            "Furniture": "Desk, monitors, filing cabinets",
         "Goes In": "Mom's Attic (monitors) / Truck Front (cabinets)", "Notes": "Monitors in original boxes or foam-wrapped; files locked or banded"},
        {"Room / Category":  "Hobby & Craft",     "Furniture": "Craft table, bins, supplies",
         "Goes In": "Truck Center / Trailer Front", "Notes": "Heavy presses over axle; small bins fill gaps around furniture"},
        {"Room / Category":  "Electronics",       "Furniture": "Printers, computers, speakers",
         "Goes In": "Mom's Attic",                "Notes": "Original boxes preferred; bubble wrap all ports and screens"},
        {"Room / Category":  "Pets",              "Furniture": "Crates, beds, aquariums",
         "Goes In": "Trailer Front (tanks) / Trailer Rear (soft beds)", "Notes": "Empty all tanks; crates load last for chase-vehicle access"},
        {"Room / Category":  "Garage",            "Furniture": "Tools, mower, shelving",
         "Goes In": "Trailer (over axle for heavy)",  "Notes": "Drain fuel from mowers/equipment before loading"},
        {"Room / Category":  "Boxes — Books",     "Furniture": "Book boxes (heavy)",
         "Goes In": "Truck / Trailer Floor first", "Notes": "Heaviest boxes always on bottom, never stacked on furniture"},
        {"Room / Category":  "Boxes — Clothing",  "Furniture": "Medium/large boxes, wardrobe boxes",
         "Goes In": "Trailer Rear / Top of stack", "Notes": "Good gap-fillers around furniture; light enough to stack high"},
    ]), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Packing checklists ──────────────────────────────────────────────────
    st.markdown("### ✅ Pre-Load Checklist")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**📦 Before You Pack**")
        for item in [
            "Gather all packing tape & markers",
            "Label every box: room + contents",
            "Photograph each room before clearing",
            "Disassemble all bed frames",
            "Remove drawers from dressers",
            "Drain fuel from all power equipment",
            "Empty and defrost refrigerator (24 hrs)",
            "Bungee fridge doors open for transit",
        ]:
            st.checkbox(item, key=f"pre_{item}")

    with col_b:
        st.markdown("**🚛 Loading the Truck**")
        for item in [
            "Load heaviest items to truck front first",
            "Mattresses vertical against side wall",
            "Sofas on end if space allows",
            "Fill all vertical gaps with soft goods",
            "Fragile boxes on top only, never crushed",
            "Tie-down straps across each load section",
            "Electronics in Mom's Attic — padded",
            "Hardware bags taped to their furniture",
        ]:
            st.checkbox(item, key=f"truck_{item}")

    with col_c:
        st.markdown("**🚐 Loading the Trailer**")
        for item in [
            "Heaviest items at trailer tongue (front 60%)",
            "Verify tongue weight before departing",
            "Secure all items with ratchet straps",
            "Nothing loose that can shift in turns",
            "Aquariums and tanks: front, empty, padded",
            "Soft goods fill the rear 40%",
            "Side-to-side weight balanced left/right",
            "Check trailer lights before pulling out",
        ]:
            st.checkbox(item, key=f"trail_{item}")

    st.markdown("---")
    st.markdown("### ⚠️ Vibration Risk by Zone")
    st.dataframe(pd.DataFrame({
        "Zone":            ["Mom's Attic", "Truck Front", "Truck Center", "Truck Rear",
                            "Trailer Front", "Trailer Rear"],
        "Vibration":       ["Lowest", "Low", "Medium", "Medium-High", "Medium", "High"],
        "Best For":        ["Electronics, valuables", "Appliances, tool chests",
                            "Furniture, mattresses", "Soft goods, boxes",
                            "Heavy totes, dressers", "Pillows, rugs, bags"],
        "Avoid":           ["Heavy items (floor stress)", "Fragile / breakable",
                            "Loose items (fill gaps)", "Heavy machinery",
                            "Soft goods (wastes tongue weight)", "Anything heavy"],
    }), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STOP DETAILS
# ══════════════════════════════════════════════════════════════════════════════
with tab_stops:
    st.subheader("📍 Stop-by-Stop Breakdown")

    avg_speed   = 60
    pet_stop_mi = patience_hours * avg_speed

    fuel_trigger = fuel_at_pct / 100
    hard_limit   = 1 - (max_pct_used / 100)

    st.info(
        f"Strategy: fill up when tank hits **{fuel_at_pct}% remaining** (~{TANK_GALLONS * fuel_trigger:.0f} gal left). "
        f"Hard limit: never exceed **{max_pct_used}% used** (~{TANK_GALLONS * hard_limit:.0f} gal remaining)."
    )

    # Build stop rows with rolling tank simulation
    all_stops = SAFE_HAVENS + [
        {"name": f"{dest_label} — DESTINATION", "mile": TOTAL_MILES,
         "lat": dest_lat, "lon": dest_lon, "type": "Destination",
         "notes": "You made it. Park, unhitch, pet the dogs."}
    ]

    rows      = []
    prev_mile = 0
    tank      = float(TANK_GALLONS)   # start full
    total_spent = 0.0

    for stop in all_stops:
        gap          = stop["mile"] - prev_mile
        gal_used_leg = gap / mpg
        tank        -= gal_used_leg
        tank         = max(tank, 0.0)

        tank_pct_remaining = tank / TANK_GALLONS * 100
        cost_leg           = gal_used_leg * fuel_price

        # Decide if this is a fuel stop (only at fuel-capable stops)
        stop_type   = stop.get("type", "")
        can_fuel    = any(x in stop_type for x in ("Fuel", "Food"))
        is_dest     = stop_type == "Destination"

        fill_amount = 0.0
        fuel_flag   = ""
        if can_fuel and not is_dest:
            if tank_pct_remaining <= (fuel_at_pct):     # at or below target
                fill_amount  = TANK_GALLONS - tank
                fill_cost    = fill_amount * fuel_price
                total_spent += fill_cost
                tank         = float(TANK_GALLONS)
                fuel_flag    = f"⛽ FILL +{fill_amount:.1f} gal (${fill_cost:.2f})"
            elif tank_pct_remaining <= (100 - max_pct_used + 10):  # approaching hard limit
                fill_amount  = TANK_GALLONS - tank
                fill_cost    = fill_amount * fuel_price
                total_spent += fill_cost
                tank         = float(TANK_GALLONS)
                fuel_flag    = f"⚠️ TOP OFF +{fill_amount:.1f} gal (${fill_cost:.2f})"

        # Warning if tank dangerously low at a non-fuel stop
        low_flag = ""
        if not can_fuel and tank_pct_remaining < (100 - max_pct_used) and not is_dest:
            low_flag = f"🚨 LOW ({tank_pct_remaining:.0f}%)"

        pet_flag = "🐾" if gap >= pet_stop_mi and not is_dest else ""

        rows.append({
            "Stop":            stop["name"],
            "Mile":            stop["mile"],
            "Gap (mi)":        gap,
            "Tank After Leg":  f"{tank_pct_remaining:.0f}% ({tank:.1f} gal)",
            "Fuel Action":     fuel_flag or low_flag or ("—" if not is_dest else "🏁"),
            "Stop Type":       stop_type,
            "Pet":             pet_flag,
            "Notes":           stop["notes"],
        })

        prev_mile = stop["mile"]

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Total Miles",     f"~{TOTAL_MILES}")
    col_s2.metric("Total Gallons",   f"{total_gallons:.1f} gal")
    col_s3.metric("Est. Fuel Cost",  f"${total_fuel_cost:.2f}")
    col_s4.metric("Headwind",        "🌬️ Active" if headwind else "Off")

    st.markdown("---")
    st.markdown("""
**Fuel Stop Legend**
| Symbol | Meaning |
|---|---|
| ⛽ FILL | Tank at or below your target % — top off here |
| ⚠️ TOP OFF | Approaching hard limit — don't skip this stop |
| 🚨 LOW | No fuel here but tank is critically low — plan ahead |
| 🐾 | Pet break recommended (patience timer reached) |
| — | No action needed at this stop |
""")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WEATHER
# ══════════════════════════════════════════════════════════════════════════════
with tab_weather:
    st.subheader("🌦️ Current Conditions Along the Route")
    st.caption("Live data from Open-Meteo · refreshes every 30 min · no API key required")

    weather_points = (
        [(s["name"], s["lat"], s["lon"]) for s in SAFE_HAVENS]
        + [(f"{dest_label} (Destination)", dest_lat, dest_lon)]
    )

    with st.spinner("Fetching weather for each stop…"):
        wx_rows = [weather_row(name, lat, lon) for name, lat, lon in weather_points]

    # Wind alerts
    high_wind_stops = [r["Stop"] for r in wx_rows if r.get("_wind_raw", 0) >= 25]
    severe_stops    = [r["Stop"] for r in wx_rows if r.get("_wind_raw", 0) >= 40]

    if severe_stops:
        st.markdown(
            f'<div class="alert-hot">🚨 <b>HIGH WIND WARNING</b> — Winds ≥40 mph at: {", ".join(severe_stops)}.<br>'
            f'Reduce speed, widen following distance, and adjust MPG slider in sidebar.</div>',
            unsafe_allow_html=True)
    elif high_wind_stops:
        st.markdown(
            f'<div class="alert-warn">⚠️ <b>Wind Advisory</b> — Winds ≥25 mph at: {", ".join(high_wind_stops)}.<br>'
            f'Consider adjusting MPG slider for headwind fuel loss.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-ok">✅ <b>Wind conditions normal</b> — No active wind advisories along the route.</div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    display_rows = [{k: v for k, v in r.items() if k != "_wind_raw"} for r in wx_rows]
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("""
**Kansas Crosswind Guide**
| Wind Speed | Impact | Action |
|---|---|---|
| < 20 mph | Minimal | Normal driving |
| 20–30 mph | Noticeable sway | Reduce speed 5–10 mph, firm grip |
| 30–40 mph | Significant | Drop MPG slider to 5.0, extra fuel buffer |
| > 40 mph | Dangerous | Consider delaying departure or stopping |
""")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — STORAGE TETRIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tetris:
    st.subheader("📦 Storage Tetris — Cubic Footage Calculator")

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("#### Select Your Items")
        st.caption("Open a room category, set quantities, then check the summary on the right.")

        item_totals = {}
        for category, items in FURNITURE_CATEGORIES.items():
            with st.expander(category, expanded=False):
                for item_name, cu_ft in items:
                    qty = st.number_input(
                        f"{item_name}  ·  {cu_ft} cu ft each",
                        min_value=0, max_value=99, value=0, step=1,
                        key=f"tetris_{category}_{item_name}",
                    )
                    if qty > 0:
                        label = f"{category.split(' ', 1)[1]} → {item_name}"
                        item_totals[label] = qty * cu_ft

        total_cu_ft = sum(item_totals.values())

    with col_right:
        st.markdown("#### Capacity Summary")

        packing_eff = st.slider("Packing Efficiency", min_value=60, max_value=95, value=75,
                                help="Real-world usable space after odd shapes & wasted corners") / 100

        truck_usable   = TRUCK_CU_FT   * packing_eff
        trailer_usable = TRAILER_CU_FT * packing_eff
        total_vehicle  = truck_usable + trailer_usable

        st.markdown("---")

        def capacity_bar(label, used, capacity, color="#4fc3f7"):
            pct = min(used / capacity * 100, 100) if capacity else 0
            overflow = used > capacity
            bar_color = "#ef5350" if overflow else color
            st.markdown(
                f"**{label}** — {used:,.0f} / {capacity:,.0f} cu ft "
                f"({'⚠️ OVER' if overflow else f'{pct:.0f}% full'})",
            )
            st.markdown(
                f'<div class="tetris-bar-bg"><div class="tetris-bar-fill" '
                f'style="width:{min(pct,100):.0f}%;background:{bar_color};"></div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

        truck_load   = min(total_cu_ft, truck_usable)
        trailer_load = min(max(total_cu_ft - truck_usable, 0), trailer_usable)
        overflow_cu  = max(total_cu_ft - total_vehicle, 0)

        capacity_bar("26' Truck",     truck_load,   truck_usable,   "#4fc3f7")
        capacity_bar("6×12 Trailer",  trailer_load, trailer_usable, "#81c784")

        st.markdown("---")
        st.metric("Your Total Load",     f"{total_cu_ft:,} cu ft")
        st.metric("Vehicle Capacity",    f"{total_vehicle:,.0f} cu ft usable",
                  delta=f"{packing_eff*100:.0f}% packing efficiency")

        if overflow_cu > 0:
            units_needed = -(-int(overflow_cu) // STORAGE_CU_FT)  # ceiling division
            st.markdown("---")
            st.markdown(
                f'<div class="alert-warn">📦 <b>{overflow_cu:,.0f} cu ft won\'t fit in the vehicles.</b><br>'
                f'You\'ll need approximately <b>{units_needed} × 10×20 storage unit'
                f'{"s" if units_needed > 1 else ""}</b> for the overflow.</div>',
                unsafe_allow_html=True)
        elif total_cu_ft > 0:
            leftover = total_vehicle - total_cu_ft
            st.markdown(
                f'<div class="alert-ok">✅ <b>Everything fits!</b> '
                f'You\'ll have ~{leftover:,.0f} cu ft to spare in the vehicles.</div>',
                unsafe_allow_html=True)
        else:
            st.info("Add items on the left to see your load analysis.")

        if item_totals:
            st.markdown("---")
            st.markdown("#### Selected Items")
            st.dataframe(
                pd.DataFrame([
                    {"Item": k, "Cu Ft": v} for k, v in sorted(item_totals.items(), key=lambda x: -x[1])
                ]),
                use_container_width=True, hide_index=True,
            )

        st.markdown("---")
        st.markdown("""
**Vehicle Reference**
| Vehicle | Interior | Usable @ 75% |
|---|---|---|
| 26' Truck | 1,682 cu ft | ~1,262 cu ft |
| 6×12 Trailer | 375 cu ft | ~281 cu ft |
| **Combined** | **2,057 cu ft** | **~1,543 cu ft** |
| 10×20 Storage Unit | 1,600 cu ft | — |
""")

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
import os
import ast

# --- Environment & Page Configuration ---
load_dotenv()
st.set_page_config(
    page_title="Train Ticket Finder",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants ---
IRCTC_URL = "https://www.irctc.co.in/nget/train-search"
ALL_CLASSES = {
    "1A": "First AC", "2A": "Second AC", "3A": "Third AC",
    "SL": "Sleeper", "CC": "AC Chair Car", "3E": "Third AC Economy",
    "2S": "Second Seating", "EA": "Executive Anubhuti", "EC": "Executive Chair Car"
}

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .badge {
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: bold;
        color: white;
    }
    .not-available-badge { background: #ef4444; }
</style>
""", unsafe_allow_html=True)

# --- Core Functions ---
@st.cache_data(ttl=timedelta(minutes=15))
def fetch_train_data(source, destination, date_str):
    params = {
        "from": source, "to": destination, "dateOfJourney": date_str,
        "action": "train_between_station", "controller": "train_ticket_tbs",
        "device_type_id": "6", "from_code": source, "journey_date": date_str,
        "journey_quota": "GN", "to_code": destination, "authentication_token": "",
        "v_code": "null", "user_id": os.getenv("USER_ID")
    }
    try:
        headers_raw = os.getenv("HEADERS", "{}")
        headers = ast.literal_eval(headers_raw)
    except:
        st.error("Headers in .env file are malformed.")
        return None

    url = os.getenv("URL")
    if not url:
        st.error("API URL not configured.")
        return None

    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None

def process_train_data(data, selected_classes):
    if not data or ('train_between_stations' not in data and 'alternate_trains' not in data):
        return pd.DataFrame()

    all_trains = data.get('train_between_stations', []) + data.get('alternate_trains', [])
    expanded_rows = []
    for train in all_trains:
        sa_data = train.get('sa_data', [])
        if not isinstance(sa_data, list):
            continue
        for item in sa_data:
            booking_class = item.get("booking_class")
            if booking_class in selected_classes:
                availability = item.get("availibility", "NOT AVAILABLE").strip()
                if availability.startswith("AVAILABLE") or availability == 'WL1' or availability == 'WL2':
                    
                    seat_info = item.get('seat_availibility')
                    ticket_fare = seat_info[0].get('ticket_fare') if isinstance(seat_info, list) and seat_info else None

                    expanded_rows.append({
                        'train_number': train.get('train_number'),
                        'train_name': train.get('extended_train_name'),
                        'from_station': train.get('from_station_name'),
                        'to_station': train.get('to_station_name'),
                        'departure_time': train.get('from_sta'),
                        'arrival_time': train.get('to_sta'),
                        'duration': train.get('duration'),
                        'train_date': train.get('train_date'),
                        'booking_class': booking_class,
                        'availability': availability,
                        'ticket_fare': ticket_fare,
                        'last_updated': seat_info[0].get('cache_text') if seat_info else 'N/A',
                    })
    return pd.DataFrame(expanded_rows)

def apply_filters_and_sort(df, time_pref, sort_pref, max_duration_hours, selected_date, show_nearby):
    if df.empty:
        return df

    df['ticket_fare'] = pd.to_numeric(df['ticket_fare'], errors='coerce')
    df.dropna(subset=['ticket_fare', 'departure_time', 'duration'], inplace=True)
    df = df[df['ticket_fare'] > 0]  # Remove zero/negative fares

    df = df[df['availability'].str.startswith(("AVAILABLE", "WL1", "WL2"))]  # Filter availability

    if not show_nearby:
        df = df[df['train_date'] == selected_date]  # Exact date match

    df['departure_time_obj'] = pd.to_datetime(df['departure_time'], format='%H:%M', errors='coerce').dt.time
    df['duration_minutes'] = df['duration'].apply(lambda d: sum(int(x) * 60 ** i for i, x in enumerate(reversed(d.split(':')))))

    if max_duration_hours:
        df = df[df['duration_minutes'] <= max_duration_hours * 60]

    time_filters = {
        "Early Morning (5am - 9am)": (time(5, 0), time(9, 0)),
        "Morning (9am - 1pm)": (time(9, 0), time(13, 0)),
        "Noon (12pm - 5pm)": (time(12, 0), time(17, 0)),
        "Evening (5pm - 8pm)": (time(17, 0), time(20, 0)),
    }
    if time_pref in time_filters:
        start, end = time_filters[time_pref]
        df = df[df['departure_time_obj'].between(start, end)]
    elif time_pref == "Late Night (8pm - 5am)":
        df = df[(df['departure_time_obj'] >= time(20, 0)) | (df['departure_time_obj'] <= time(5, 0))]

    if sort_pref == "💰 Cheapest First":
        df = df.sort_values(by=['ticket_fare', 'duration_minutes'])
    else:
        df = df.sort_values(by=['duration_minutes', 'ticket_fare'])

    return df

def display_train_card(row):

    badge_class = "green"
    
    from datetime import datetime

    # Convert time string to datetime object
    dep_time_obj = datetime.strptime(row['departure_time'], "%H:%M")  # adjust format if needed
    hour = dep_time_obj.hour
    dep_badge_class = "violet"

    # Categorize based on hour
    if 5 <= hour < 12:
        dep_period = "Morning"
    elif 12 <= hour < 17:
        dep_period = "Afternoon"
    elif 17 <= hour < 21:
        dep_period = "Evening"
    else:
        dep_period = "Night"



    with st.expander(f"🚂 {row['train_name']} ({row['train_number']}) - ₹{row['ticket_fare']:.0f}", expanded=True):

        col1, col2 =st.columns(2)
        with col1:
            st.write(f"From: {row['from_station']} @ {row['departure_time']}")
            st.write(f"To: {row['to_station']} @ {row['arrival_time']}")
            st.header(f"₹{row['ticket_fare']:.0f}")
        with col2:
            st.write(f"Duration: {row['duration']} | Date: {row['train_date']}" )
            st.markdown(    f":{badge_class}-badge[:material/star: {row['booking_class']}] :{badge_class}-badge[{row['availability']}] ")
            st.markdown(f":{dep_badge_class}-badge[Departs in {dep_period}]")  # New badge


        st.caption(f"Last Updated: {row['last_updated']}")

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>🚂 Train Ticket Finder</h1>
    <p>Find the best train tickets for your next journey • Built by <strong>Abdul Ahad Rauf</strong></p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🚉 Route & Date")

    source_code = st.text_input("From (Station Code)", "NDLS").strip().upper()
    destination_code = st.text_input("To (Station Code)", "CNB").strip().upper()
    show_nearby = st.checkbox("Show Nearby Date Trains", value=False)

    journey_date = st.date_input("📅 Date of Journey", datetime.now() + timedelta(days=1))
    date_str = journey_date.strftime('%Y-%m-%d')


    with st.expander("Filters & Sorting", expanded=True):
        selected_classes = st.multiselect(
            "Select preferred classes",
            options=list(ALL_CLASSES.keys()),
            default=["CC", "3A", "3E"]
        )
        time_preference = st.selectbox(
            "Preferred Departure Time",
            ["Any Time", "Early Morning (5am - 9am)", "Morning (9am - 1pm)",
             "Noon (12pm - 5pm)", "Evening (5pm - 8pm)", "Late Night (8pm - 5am)"]
        )
        max_duration_hours = st.slider(
            "Maximum Journey Duration (Hours)", 1, 48, 24
        )
        sort_preference = st.radio(
            "Sort by", ["💰 Cheapest First", "⚡ Fastest First"], horizontal=True
        )

    search_button = st.button("🔍 Search Trains", type="primary", use_container_width=True)

# --- Main ---
if search_button:
    raw_data = fetch_train_data(source_code, destination_code, date_str)
    if raw_data:
        df_processed = process_train_data(raw_data, selected_classes)
        df_final = apply_filters_and_sort(df_processed, time_preference, sort_preference, max_duration_hours, date_str, show_nearby)

        if not df_final.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Lowest Fare", f"₹{df_final['ticket_fare'].min():.0f}")
            with col2:
                st.metric("Average Fare", f"₹{df_final['ticket_fare'].mean():.0f}")
            with col3:
                st.metric("Highest Fare", f"₹{df_final['ticket_fare'].max():.0f}")
            with col4:
                st.metric("Fastest Journey", df_final.loc[df_final['duration_minutes'].idxmin(), 'duration'])
            for _, row in df_final.iterrows():
                display_train_card(row)
        else:
            st.warning("⚠️ No trains found matching your filters.")
    else:
        st.error("❌ Could not retrieve data.")
else:
    st.info("👈 Enter your journey details and click 'Search Trains'.")

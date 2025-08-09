import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
from dotenv import load_dotenv
import os
load_dotenv() 
# --- Page Configuration ---
st.set_page_config(
    page_title="Train Ticket Finder",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Reusable Functions from your backend script ---
def fetch_train_data(source, destination, date):
    params = {
        "from": source, "to": destination, "dateOfJourney": date,
        "action": "train_between_station", "controller": "train_ticket_tbs",
        "device_type_id": "6", "from_code": source, "journey_date": date,
        "journey_quota": "GN", "to_code": destination, "authentication_token": "",
        "v_code": "null", "user_id": os.getenv("USER_ID")
    }

    import ast
    headers_raw = os.getenv("HEADERS", "{}")
    headers = ast.literal_eval(headers_raw)
    url = os.getenv("URL")

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None


def process_train_data(data, selected_classes):
    """
    Processes the raw train data to extract and filter relevant information.
    """
    if not data:
        return pd.DataFrame()

    all_trains = data.get('train_between_stations', []) + data.get('alternate_trains', [])
    if not all_trains:
        return pd.DataFrame()

    expanded_rows = []
    for train in all_trains:
        sa_data = train.get('sa_data', [])
        if not isinstance(sa_data, list): continue

        for item in sa_data:
            booking_class = item.get("booking_class")
            if booking_class in selected_classes:
                availability = item.get("availibility", "").strip()
                if availability.startswith("AVAILABLE") or any(wl in availability for wl in ["WL1", "WL2"]):
                    seat_info = item.get('seat_availibility')
                    ticket_fare = seat_info[0].get('ticket_fare') if isinstance(seat_info, list) and seat_info else None
                    cache_text = seat_info[0].get('cache_text') if isinstance(seat_info, list) and seat_info else None

                    expanded_rows.append({
                        'train_number': train.get('train_number'), 'train_name': train.get('extended_train_name'),
                        'from_station': train.get('from_station_name'), 'to_station': train.get('to_station_name'),
                        'departure_time': train.get('from_sta'), 'arrival_time': train.get('to_sta'),
                        'duration': train.get('duration'), 'train_date': train.get('train_date'),
                        'booking_class': booking_class, 'availability': availability,
                        'ticket_fare': ticket_fare, 'last_updated': cache_text,
                    })
    return pd.DataFrame(expanded_rows)

# --- Streamlit UI ---

st.title("🚂 Train Ticket Finder")
st.markdown("Find the best train tickets for your next journey. Built by Abdul Ahad Rauf.")

# --- Search Form in the Sidebar ---
with st.sidebar:
    st.header("Search Parameters")
    with st.form(key="search_form"):
        source_station = st.text_input("From Station Code", "NDLS")
        destination_station = st.text_input("To Station Code", "CNB")
        journey_date = st.date_input("Date of Journey", datetime(2025, 8, 15))
        selected_classes = st.multiselect(
            "Select Class",
            ["1A", "2A", "3A", "SL", "CC", "3E"],
            default=["CC", "3A", "3E"]
        )
        how_do_you_want = st.radio("How to filter by first", ["ticket_fare", "duration"])
        
        print(how_do_you_want)
        # --- NEW: Time preference selector ---
        time_preference = st.selectbox(
            "Departure Time",
            [
                "Any Time",
                "Early Morning (3am - 9am)",
                "Morning (9am - 1pm)",
                "Noon (12pm - 5pm)",
                "Evening (5pm - 8pm)",
                "Late Night (8pm - 6am)"
            ],
            key="time_pref"
        ) # <-- NEW
        submit_button = st.form_submit_button(label="Search Trains", use_container_width=True)

# --- Main Content Area ---
if submit_button:
    st.subheader(f"Results for {source_station} → {destination_station} on {journey_date.strftime('%Y-%m-%d')}")

    with st.spinner("Finding the best routes for you..."):
        raw_data = fetch_train_data(source_station, destination_station, journey_date.strftime('%Y-%m-%d'))

        if raw_data:
            final_df = process_train_data(raw_data, selected_classes)

            if not final_df.empty:
                # --- NEW: Time-based filtering logic ---
                # Convert departure_time string to a comparable time object
                final_df['departure_time_obj'] = pd.to_datetime(final_df['departure_time'], format='%H:%M').dt.time

                if time_preference != "Any Time":
                    if time_preference == "Early Morning (3am - 9am)":
                        final_df = final_df[final_df['departure_time_obj'].between(time(3, 0), time(9, 0))]
                    elif time_preference == "Morning (9am - 1pm)":
                        final_df = final_df[final_df['departure_time_obj'].between(time(9, 0), time(13, 0))]
                    elif time_preference == "Noon (12pm - 5pm)":
                        final_df = final_df[final_df['departure_time_obj'].between(time(12, 0), time(17, 0))]
                    elif time_preference == "Evening (5pm - 8pm)":
                        final_df = final_df[final_df['departure_time_obj'].between(time(17, 0), time(20, 0))]
                    elif time_preference == "Late Night (8pm - 6am)":
                        # This handles the overnight case by checking two separate ranges
                        final_df = final_df[
                            (final_df['departure_time_obj'] >= time(20, 0)) |
                            (final_df['departure_time_obj'] <= time(6, 0))
                        ]
                # --- END of new filtering logic ---

                if not final_df.empty: # Check if dataframe is still populated after filtering
                    # Clean and sort the data
                    final_df['ticket_fare'] = pd.to_numeric(final_df['ticket_fare'], errors='coerce')
                    final_df.dropna(subset=['ticket_fare'], inplace=True)
                    final_df['duration_td'] = pd.to_timedelta(final_df['duration'].apply(lambda x: f"{x}:00" if len(x.split(':')) == 2 else '00:00:00'))
                    
                    if how_do_you_want == "ticket_fare":
                        df_sorted = final_df.sort_values(by=['ticket_fare', 'duration_td'], ascending=[True, True])
                    else:
                        df_sorted = final_df.sort_values(by=['duration_td','ticket_fare'], ascending=[True, True])

                    # Display results as cards
                    for _, row in df_sorted.iterrows():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{row['train_name']}** ({row['train_number']})")
                            st.markdown(
                                f"<span style='font-size: 1.1em;'>**{row['departure_time']}**</span> "
                                f"<small>({row['from_station']})</small> → "
                                f"<span style='font-size: 1.1em;'>**{row['arrival_time']}**</span> "
                                f"<small>({row['to_station']})</small>",
                                unsafe_allow_html=True
                            )
                            st.markdown(f"🕒 Duration: **{row['duration']}** | 📅 Date: **{row['train_date']}**")
                        with col2:
                            st.metric(label=row['booking_class'], value=f"₹{row['ticket_fare']:.2f}")
                            st.markdown(f"<p style='color: green; font-weight: bold;'>{row['availability'].replace('-', ' ')}</p>", unsafe_allow_html=True)

                        st.markdown(f"<small>Last Updated: {row['last_updated']}</small>", unsafe_allow_html=True)
                        st.button("Book Now", key=f"book_{row['train_number']}_{row['booking_class']}", use_container_width=True)
                        st.divider()
                else: # <-- MODIFIED to handle empty results after time filter
                    st.warning("No trains found for the selected time slot. Please try a different time or 'Any Time'.")
            else:
                st.warning("No trains found matching your criteria. Please try a different search.")
        else:
            st.error("Could not retrieve train data. Please try again later.")
else:
    st.info("Please enter your journey details in the sidebar and click 'Search Trains'.")

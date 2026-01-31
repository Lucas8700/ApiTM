import streamlit as st
from DataBaseUtils2 import GameDatabase
from dotenv import load_dotenv
from nadeo_api.auth import get_token
from nadeo_api import auth
import os
from nadeo_api_class import NadeoOAuthAPI
from datetime import datetime

# Set wide mode
st.set_page_config(layout="wide")

# Load environment
load_dotenv()
EMAIL = os.getenv("UBISOFT_EMAIL")
PASSWORD = os.getenv("UBISOFT_PASSWORD")

# Get tokens
tokenCore = get_token(
    audience=auth.audience_oauth,
    username='bdb0007074994c7fda87',
    password='ac8de4fc2da739a81fb98336554b6d6cf13f4d71',
)

# API
apiCore = NadeoOAuthAPI(tokenCore)

# Initialize database
db = GameDatabase()

# Custom CSS to make buttons look like white text without underline
st.markdown("""
<style>
.stButton>button {
    border: none;
    background: none;
    color: white;
    text-decoration: none;
    font-size: inherit;
    padding: 0;
    margin: 0;
}
.stButton {
    display: inline;
}
</style>
""", unsafe_allow_html=True)

def format_time(ms):
    if ms is None:
        return "N/A"
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{minutes}:{seconds:02d}:{millis:03d}"

def tm2020_to_html(text):
    html = ""
    i = 0
    while i < len(text):
        if text[i] == '$':
            if i+1 < len(text):
                code = text[i+1].lower()
                if code == 'z':
                    html += '</span>'
                elif len(code) == 3 and all(c in '0123456789abcdef' for c in code):
                    r = int(code[0], 16) * 17
                    g = int(code[1], 16) * 17
                    b = int(code[2], 16) * 17
                    html += f'<span style="color: rgb({r},{g},{b});">'
                # Ignore other codes
            i += 2
        else:
            html += text[i]
            i += 1
    return html

# Initialize database
db = GameDatabase()

# Title
st.title("TOTD Author Ranking")

# Get total maps
total_maps = db.get_total_maps()

# Session state for view
if 'view' not in st.session_state:
    st.session_state.view = 'ranking'
if 'player_id' not in st.session_state:
    st.session_state.player_id = None
if 'page' not in st.session_state:
    st.session_state.page = 0
if 'search_query' not in st.session_state:
    st.session_state.search_query = ''

# Search bar
search_query = st.text_input("Search players by name", value=st.session_state.search_query)
if search_query != st.session_state.search_query:
    st.session_state.search_query = search_query
    st.session_state.page = 0
    st.session_state.view = 'ranking'

if st.session_state.view == 'ranking':
    if search_query:
        players = db.search_players(search_query)
        st.subheader(f"Search results for '{search_query}'")
    else:
        limit = 50
        offset = st.session_state.page * limit
        if offset >= 10000:
            offset = 9999 - limit  # Adjust to not exceed 10000
        players = db.get_players_by_author_count(limit=limit, offset=offset)

    if players:
        # Get display names
        account_ids = [name for _, name, _ in players]
        if account_ids:
            df_names = apiCore.get_display_names(account_ids)
            id_to_display = dict(zip(df_names["accountId"], df_names["displayName"]))
        else:
            id_to_display = {}

        # Column headers
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
        with col1:
            st.write("**Rank**")
        with col2:
            st.write("**Player**")
        with col3:
            st.write("**Author medals**")
        with col4:
            st.write("**Missing medals**")

        for i, (player_id, account_id, author_count) in enumerate(players, start=1 + offset if not search_query else 1):
            display_name = id_to_display.get(account_id, account_id)
            missing = total_maps - (author_count or 0)
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            with col1:
                st.write(f"#{i}")
            with col2:
                if st.button(display_name, key=f"player_{player_id}"):
                    st.session_state.view = 'player'
                    st.session_state.player_id = player_id
                    st.rerun()
            with col3:
                subcol1, subcol2 = st.columns([4, 1])
                with subcol1:
                    st.markdown(f"<center>{author_count or 0}</center>", unsafe_allow_html=True)
                with subcol2:
                    st.image("medalAuthor.png", width=20)
            with col4:
                st.markdown(f"<center>{missing}</center>", unsafe_allow_html=True)

        if not search_query:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Previous", disabled=st.session_state.page == 0):
                    st.session_state.page -= 1
                    st.rerun()
            with col2:
                if st.button("Next", disabled=len(players) < limit or offset + limit >= 10000):
                    st.session_state.page += 1
                    st.rerun()
    else:
        st.write("No players found.")

elif st.session_state.view == 'player':
    player_id = st.session_state.player_id
    player_account = db.get_player_name(player_id)
    # Get fresh display name
    df_single = apiCore.get_display_names([player_account])
    player_display_name = df_single.iloc[0]["displayName"] if not df_single.empty else player_account
    st.subheader(f"Maps for {player_display_name}")

    if st.button("Back to Ranking"):
        st.session_state.view = 'ranking'
        st.session_state.player_id = None
        st.rerun()

    maps = db.get_player_maps(player_id)

    # Get display names for authors
    authors = list(set(row[2] for row in maps))  # map_author
    if authors:
        df_authors = apiCore.get_display_names(authors)
        author_to_display = dict(zip(df_authors["accountId"], df_authors["displayName"]))
    else:
        author_to_display = {}

    # Sort option
    if 'sort_desc' not in st.session_state:
        st.session_state.sort_desc = True
    maps_sorted = sorted(maps, key=lambda x: x[3] or 0, reverse=st.session_state.sort_desc)

    # Column headers
    col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 1, 2, 2])
    with col1:
        st.write("**Date**")
    with col2:
        st.write("**Map**")
    with col3:
        st.write("**Author**")
    with col4:
        st.write("**# ATs**")
        if st.button("🔄", key="sort_at"):
            st.session_state.sort_desc = not st.session_state.sort_desc
            st.rerun()
    with col5:
        st.write("**Author time**")
    with col6:
        st.write("**Player time**")

    current_month = None
    for release_date, map_name, map_author, author_count, author_time, player_time in maps_sorted:
        # Format date
        date_obj = datetime.strptime(release_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d-%m-%Y')
        
        month = release_date[:7]  # YYYY-MM
        if month != current_month:
            if current_month is not None:
                st.write("")  # Gap
            current_month = month
        
        author_display = author_to_display.get(map_author, map_author)
        author_time_str = format_time(author_time)
        player_time_str = format_time(player_time) if player_time else "No time"
        
        col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 1, 2, 2])
        with col1:
            st.write(formatted_date)
        with col2:
            st.markdown(tm2020_to_html(map_name), unsafe_allow_html=True)
        with col3:
            st.write(author_display)
        with col4:
            st.write(author_count or 0)
        with col5:
            st.write(author_time_str)
        with col6:
            if player_time and player_time <= author_time:
                st.write(f"🏆 {player_time_str}")
            else:
                st.write(player_time_str)
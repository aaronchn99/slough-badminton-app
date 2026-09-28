import streamlit as st
import pandas as pd
import random
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Slough Badminton Club (Monday)", page_icon="🏸", layout="wide")

# HARDCODED USER ACCOUNTS (Admin access 24/7)
USER_DATABASE = {
    "admin": {"password": "4dm1n776&", "role": "admin"},
    "Musa": {"password": "4dmiN786&", "role": "admin"},
    "Simon": {"password": "4dm1nh3ll0", "role": "admin"},
    "Shoj": {"password": "playerpass123", "role": "player"}
}

# --- TIME-BASED PERMISSION CHECK ---
def is_session_active():
    """Returns True ONLY on Mondays between 20:00 (8 PM) and 22:00 (10 PM) UK time."""
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    
    is_monday = now_uk.weekday() == 0  # 0 represents Monday
    is_session_time = 20 <= now_uk.hour < 22  # 20:00 to 21:59
    
    return is_monday and is_session_time

# Session State Setup
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

if "current_session_num" not in st.session_state:
    st.session_state.current_session_num = 1

if "active_players" not in st.session_state:
    st.session_state.active_players = []
if "session_scores" not in st.session_state:
    st.session_state.session_scores = {}
if "league_standings" not in st.session_state:
    st.session_state.league_standings = {}
if "play_counts" not in st.session_state:
    st.session_state.play_counts = {}

if "courts_state" not in st.session_state:
    st.session_state.courts_state = {}

if "registered_users" not in st.session_state:
    st.session_state.registered_users = {}

# Clean SVG Badge Vector Graphic
RAW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 260" width="260" height="260">
    <circle cx="130" cy="130" r="120" fill="#1E4867" stroke="#F9F8F3" stroke-width="6"/>
    <path id="archPath" d="M 35,130 A 95,95 0 1,1 225,130" fill="none" />
    <text fill="#F9F8F3" font-size="15" font-weight="900" font-family="Arial, sans-serif" letter-spacing="2">
        <textPath href="#archPath" startOffset="50%" text-anchor="middle">BADMINTON MONDAYS</textPath>
    </text>
    <text x="130" y="145" font-size="44" text-anchor="middle">🏸</text>
    <text x="130" y="172" font-size="13" fill="#F9F8F3" text-anchor="middle" letter-spacing="2">⭐⭐⭐⭐⭐</text>
    <text x="130" y="195" font-size="11" font-weight="bold" fill="#F9F8F3" text-anchor="middle" font-family="Arial, sans-serif">8PM - 10PM</text>
    <text x="130" y="212" font-size="11" font-weight="bold" fill="#F9F8F3" text-anchor="middle" font-family="Arial, sans-serif">DITTON PARK, SLOUGH</text>
</svg>"""

SVG_URL = "data:image/svg+xml;utf8," + urllib.parse.quote(RAW_SVG)

# --- LOGIN & SIGNUP SCREEN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(SVG_URL, width=220)
        st.title("Slough Badminton Club (Monday)")
        
        login_tab, signup_tab = st.tabs(["🔒 Log In", "📝 Sign Up"])
        
        with login_tab:
            with st.form("login_form"):
                st.subheader("Log In")
                username_input = st.text_input("Username").strip()
                password_input = st.text_input("Password", type="password").strip()
                submit_button = st.form_submit_button("Log In")
                
                if submit_button:
                    db = st.session_state.registered_users
                    if username_input in USER_DATABASE and USER_DATABASE[username_input]["password"] == password_input:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.session_state.role = USER_DATABASE[username_input]["role"]
                        st.success(f"Welcome back, {username_input}!")
                        st.rerun()
                    elif username_input in db and db[username_input]["password"] == password_input:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.session_state.role = "player"
                        st.success(f"Welcome back, {username_input}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with signup_tab:
            with st.form("signup_form"):
                st.subheader("Create Account")
                new_user = st.text_input("Choose Username").strip()
                new_pass = st.text_input("Choose Password", type="password").strip()
                confirm_pass = st.text_input("Confirm Password", type="password").strip()
                signup_btn = st.form_submit_button("Create Account")
                
                if signup_btn:
                    if new_user in USER_DATABASE or new_user in st.session_state.registered_users:
                        st.error("Username already taken.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    elif not new_user or not new_pass:
                        st.error("Please fill in all fields.")
                    else:
                        st.session_state.registered_users[new_user] = {"password": new_pass, "role": "player"}
                        st.success("Account created successfully! You can now log in.")
    st.stop()

# --- DYNAMIC PERMISSION CHECK ---
session_live = is_session_active()
can_edit = session_live or (st.session_state.role == "admin")

# Sidebar Status
st.sidebar.write(f"Logged in as: *{st.session_state.username}* ({st.session_state.role.capitalize()})")
if st.session_state.role == "admin":
    st.sidebar.success("👑 *Admin User: Full Access Active 24/7*")
elif session_live:
    st.sidebar.success("🟢 *Session Active (8PM-10PM): Edit Mode Unlocked for All*")
else:
    st.sidebar.info("🔒 *Outside Session Hours: Read-Only Mode*")

if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.courts_state = {}
    st.rerun()

# Display Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(SVG_URL, width=180)
with col_title:
    st.title("Slough Badminton Club (Monday)")
    st.subheader(f"📅 Season Progress: Session {st.session_state.current_session_num} / 12")

# Tabs
if can_edit:
    tabs = st.tabs(["🎾 Live Courts & Matchmaker", "📊 Today's Leaderboard", "🏆 12-Session League", "⚙️ Season Management"])
else:
    tabs = st.tabs(["📊 Today's Leaderboard", "🏆 12-Session League"])

# Helper function to get available resting players
def get_resting_players():
    currently_playing = set()
    for c, match in st.session_state.courts_state.items():
        if match:
            currently_playing.update(match["team1"])
            currently_playing.update(match["team2"])
            
    resting = [p for p in st.session_state.active_players if p not in currently_playing]
    return sorted(resting, key=lambda p: (st.session_state.play_counts[p], random.random()))

# Helper function to assign next 4 available players to a court
def assign_next_match_to_court(court_num):
    resting = get_resting_players()
    if len(resting) >= 4:
        next_4 = resting[:4]
        for p in next_4:
            st.session_state.play_counts[p] += 1
        random.shuffle(next_4)
        st.session_state.courts_state[court_num] = {
            "team1": [next_4[0], next_4[1]],
            "team2": [next_4[2], next_4[3]]
        }
    else:
        st.session_state.courts_state[court_num] = None

# --- MATCHMAKER & SCORING (ENABLED IF MON 8-10PM OR ADMIN) ---
if can_edit:
    with tabs[0]:
        st.subheader("1. Session Setup")
        
        default_names = "Shoj\nAbdul Waheed\nAaron\nFaisal\nNaveed\nAbdulKhader\nRyan\nAbdullah sr\nYousuf\nAamer\nMohsin\nSimon\nJoe S\nHassan\nHabeeb"
        player_text = st.text_area("Enter Player Names Present Tonight (one per line):", value=default_names, height=150)
        
        num_courts = st.number_input("Number of Courts Available", min_value=1, max_value=6, value=3)
        
        if st.button("✅ Start Session / Populate Courts"):
            names = [p.strip() for p in player_text.split("\n") if p.strip()]
            st.session_state.active_players = names
            st.session_state.session_scores = {p: 0 for p in names}
            st.session_state.play_counts = {p: 0 for p in names}
            st.session_state.courts_state = {}
            
            for p in names:
                if p not in st.session_state.league_standings:
                    st.session_state.league_standings[p] = 0
            
            for c in range(1, num_courts + 1):
                assign_next_match_to_court(c)
                
            st.success(f"Session {st.session_state.current_session_num} started! Loaded {len(names)} players across {num_courts} courts.")
            st.rerun()

        st.write("---")
        
        if st.session_state.active_players:
            resting_players = get_resting_players()
            st.info(f"⏸️ *Players Resting / Queueing ({len(resting_players)}):* {', '.join(resting_players) if resting_players else 'None'}")
            st.write("---")
            
            st.subheader("2. Active Courts (Independent Scoring)")
            
            for court_num in range(1, num_courts + 1):
                match = st.session_state.courts_state.get(court_num)
                st.markdown(f"### Court {court_num}")
                
                if match:
                    col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
                    
                    with col1:
                        st.write(f"*Team A:* {match['team1'][0]} & {match['team1'][1]}")
                        s1 = st.number_input(f"Team A Score", min_value=0, max_value=30, value=0, key=f"c{court_num}_s1")
                    
                    with col2:
                        st.markdown("<h3 style='text-align: center; margin-top: 20px;'>VS</h3>", unsafe_allow_html=True)
                    
                    with col3:
                        st.write(f"*Team B:* {match['team2'][0]} & {match['team2'][1]}")
                        s2 = st.number_input(f"Team B Score", min_value=0, max_value=30, value=0, key=f"c{court_num}_s2")
                        
                    with col4:
                        st.write("")
                        st.write("")
                        if st.button(f"💾 Finish Court {court_num}", key=f"btn_{court_num}"):
                            if s1 > s2:
                                for p in match["team1"]:
                                    st.session_state.session_scores[p] += 2
                                    st.session_state.league_standings[p] += 2
                            elif s2 > s1:
                                for p in match["team2"]:
                                    st.session_state.session_scores[p] += 2
                                    st.session_state.league_standings[p] += 2
                            
                            assign_next_match_to_court(court_num)
                            st.success(f"Court {court_num} score recorded & new match generated!")
                            st.rerun()
                else:
                    st.write("No active match on this court.")
                    if st.button(f"⚡ Start Match on Court {court_num}", key=f"start_{court_num}"):
                        assign_next_match_to_court(court_num)
                        st.rerun()
                st.write("---")

    # SEASON & SESSION CONTROLS TAB
    with tabs[3]:
        st.subheader("⚙️ Session & Season Controls")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### End Current Session")
            st.write("Locks in today's session scores, clears the active courts, and advances the session counter to the next week.")
            if st.button("🏁 End Current Session", type="primary"):
                if st.session_state.current_session_num < 12:
                    st.session_state.current_session_num += 1
                st.session_state.courts_state = {}
                st.session_state.active_players = []
                st.session_state.session_scores = {}
                st.session_state.play_counts = {}
                st.success(f"Session ended! Moved to Session {st.session_state.current_session_num} / 12.")
                st.rerun()

        with col_b:
            st.markdown("### Reset Entire Season")
            st.write("Resets the session counter back to *Session 1 / 12* and wipes all 12-session overall league standings.")
            if st.button("🔴 End / Reset Entire Season"):
                st.session_state.current_session_num = 1
                st.session_state.league_standings = {}
                st.session_state.session_scores = {}
                st.session_state.courts_state = {}
                st.session_state.active_players = []
                st.session_state.play_counts = {}
                st.success("Season reset back to Session 1 / 12!")
                st.rerun()

# --- TODAY'S LEADERBOARD ---
today_tab = tabs[1] if can_edit else tabs[0]
with today_tab:
    st.subheader(f"Today's Session Standings (Session {st.session_state.current_session_num}/12)")
    if st.session_state.session_scores:
        df_today = pd.DataFrame([
            {"Player": k, "Points": v, "Games Played": st.session_state.play_counts.get(k, 0)}
            for k, v in st.session_state.session_scores.items()
        ]).sort_values(by="Points", ascending=False).reset_index(drop=True)
        df_today.index += 1
        st.dataframe(df_today, use_container_width=True)
    else:
        st.info("No games recorded for this session yet.")

# --- 12-SESSION LEAGUE ---
league_tab = tabs[2] if can_edit else tabs[1]
with league_tab:
    st.subheader(f"🏆 12-Session Overall League (Progress: {st.session_state.current_session_num}/12)")
    if st.session_state.league_standings:
        df_league = pd.DataFrame([
            {"Player": k, "Total Points": v}
            for k, v in st.session_state.league_standings.items()
        ]).sort_values(by="Total Points", ascending=False).reset_index(drop=True)
        df_league.index += 1
        
        st.markdown("### 🥇 Top 3 Leaderboard")
        cols = st.columns(3)
        if len(df_league) >= 1:
            cols[0].metric("🥇 1st Place", df_league.iloc[0]["Player"], f"{df_league.iloc[0]['Total Points']} pts")
        if len(df_league) >= 2:
            cols[1].metric("🥈 2nd Place", df_league.iloc[1]["Player"], f"{df_league.iloc[1]['Total Points']} pts")
        if len(df_league) >= 3:
            cols[2].metric("🥉 3rd Place", df_league.iloc[2]["Player"], f"{df_league.iloc[2]['Total Points']} pts")
            
        st.write("---")
        st.dataframe(df_league, use_container_width=True)
    else:
        st.info("No overall standings recorded yet.")

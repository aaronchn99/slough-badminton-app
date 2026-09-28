import streamlit as st
import pandas as pd
import random
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import math
import extra_streamlit_components as stx

st.set_page_config(page_title="Slough Badminton Club (Monday)", page_icon="🏸", layout="wide")

# --- COOKIE MANAGER FOR PERSISTENT LOGINS ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# --- SUPABASE DATABASE CONNECTION ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error("Could not connect to Supabase database. Please verify Streamlit secrets.")

# HARDCODED ADMIN ACCOUNTS
ADMIN_ACCOUNTS = {
    "admin": "4dm1n776&",
    "Musa": "4dmiN786&",
    "Simon": "4dm1nh3ll0"
}

# --- ELO & RATING HELPER FUNCTIONS ---
def get_letter_grade(rating):
    r = round(rating)
    if r >= 1600:
        return f"A+ ({r})"
    elif r >= 1400:
        return f"A ({r})"
    elif r >= 1300:
        return f"B+ ({r})"
    elif r >= 1150:
        return f"B ({r})"
    elif r >= 1050:
        return f"C+ ({r})"
    else:
        return f"C ({r})"

def calculate_rating_change(team1_avg, team2_avg, score1, score2, k_factor=32):
    margin = abs(score1 - score2)
    margin_multiplier = math.log(margin + 1) if margin > 0 else 1.0
    
    expected1 = 1.0 / (1.0 + 10 ** ((team2_avg - team1_avg) / 400.0))
    expected2 = 1.0 - expected1
    
    actual1 = 1.0 if score1 > score2 else (0.5 if score1 == score2 else 0.0)
    actual2 = 1.0 - actual1
    
    delta1 = round(k_factor * margin_multiplier * (actual1 - expected1))
    delta2 = round(k_factor * margin_multiplier * (actual2 - expected2))
    
    return delta1, delta2

def load_player_ratings():
    ratings = {}
    try:
        resp = supabase.table("users").select("*").execute()
        if resp.data:
            for row in resp.data:
                ratings[row["username"]] = row.get("rating") if row.get("rating") is not None else 1200
    except Exception:
        pass
    return ratings

def save_player_rating(username, new_rating):
    try:
        supabase.table("users").update({"rating": new_rating}).eq("username", username).execute()
    except Exception:
        pass

# DB Helper Functions
def get_user_role(username, password):
    if username in ADMIN_ACCOUNTS and ADMIN_ACCOUNTS[username] == password:
        return "admin"
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            return response.data[0]["role"]
    except Exception:
        pass
    return None

def register_user(username, password):
    if username in ADMIN_ACCOUNTS:
        return False, "Username reserved for Admin."
    try:
        response = supabase.table("users").select("username").eq("username", username).execute()
        if response.data:
            return False, "Username already exists."
        supabase.table("users").insert({"username": username, "password": password, "role": "player", "rating": 1200}).execute()
        return True, "Account created successfully!"
    except Exception as e:
        return False, f"Error creating account: {e}"

def log_login_event(username):
    try:
        now_uk = datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M:%S")
        supabase.table("login_logs").insert({"username": username, "login_time": now_uk}).execute()
    except Exception:
        pass

def is_session_active():
    """Returns True ONLY on Mondays between 20:00 (8 PM) and 22:00 (10 PM) UK time."""
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    return now_uk.weekday() == 0 and (20 <= now_uk.hour < 22)

# --- AUTO-RESTORE LOGIN FROM COOKIES ---
saved_username = cookie_manager.get("badminton_user")
saved_role = cookie_manager.get("badminton_role")

if "logged_in" not in st.session_state:
    if saved_username and saved_role:
        st.session_state.logged_in = True
        st.session_state.username = saved_username
        st.session_state.role = saved_role
        st.session_state.player_ratings = load_player_ratings()
    else:
        st.session_state.logged_in = False
        st.session_state.username = None
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
if "player_ratings" not in st.session_state:
    st.session_state.player_ratings = {}

if "courts_state" not in st.session_state:
    st.session_state.courts_state = {}

# Clean SVG Logo Graphic
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
                    role = get_user_role(username_input, password_input)
                    if role:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.session_state.role = role
                        st.session_state.player_ratings = load_player_ratings()
                        
                        # Save persistent cookies for 30 days
                        cookie_manager.set("badminton_user", username_input, key="cookie_user", expires_at=datetime.now().replace(year=datetime.now().year + 1))
                        cookie_manager.set("badminton_role", role, key="cookie_role", expires_at=datetime.now().replace(year=datetime.now().year + 1))
                        
                        log_login_event(username_input)
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
                    if new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    elif not new_user or not new_pass:
                        st.error("Please fill in all fields.")
                    else:
                        success, msg = register_user(new_user, new_pass)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
    st.stop()

# --- DYNAMIC PERMISSION CHECK ---
session_live = is_session_active()
can_edit = session_live or (st.session_state.role == "admin")
is_master_admin = (st.session_state.username == "admin")
can_manage_season = (st.session_state.username in ["admin", "Musa"])

# Sidebar Status
st.sidebar.write(f"Logged in as: *{st.session_state.username}* ({st.session_state.role.capitalize()})")
if st.session_state.role == "admin":
    st.sidebar.success("👑 *Admin User: Full Access Active 24/7*")
elif session_live:
    st.sidebar.success("🟢 *Session Active (8PM-10PM): Edit Mode Unlocked for All*")
else:
    st.sidebar.info("🔒 *Outside Session Hours: Read-Only Mode*")

if st.sidebar.button("Log Out"):
    cookie_manager.delete("badminton_user", key="delete_user")
    cookie_manager.delete("badminton_role", key="delete_role")
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

# Tabs Configuration
if is_master_admin:
    tabs = st.tabs(["🎾 Live Courts & Matchmaker", "📊 Today's Leaderboard", "🏆 12-Session League", "⚙️ Season Management", "👥 User Management & Logs"])
elif can_manage_season:
    tabs = st.tabs(["🎾 Live Courts & Matchmaker", "📊 Today's Leaderboard", "🏆 12-Session League", "⚙️ Season Management"])
elif can_edit:
    tabs = st.tabs(["🎾 Live Courts & Matchmaker", "📊 Today's Leaderboard", "🏆 12-Session League"])
else:
    tabs = st.tabs(["📊 Today's Leaderboard", "🏆 12-Session League"])

# Helper function to get resting players sorted by least played
def get_resting_players():
    currently_playing = set()
    for c, match in st.session_state.courts_state.items():
        if match:
            currently_playing.update(match["team1"])
            currently_playing.update(match["team2"])
            
    resting = [p for p in st.session_state.active_players if p not in currently_playing]
    return sorted(resting, key=lambda p: (st.session_state.play_counts[p], random.random()))

# Skill-Balanced Matchmaker Function
def assign_next_match_to_court(court_num):
    resting = get_resting_players()
    if len(resting) >= 4:
        next_4 = resting[:4]
        
        # Calculate ratings for balanced 2v2 pairing
        r = {p: st.session_state.player_ratings.get(p, 1200) for p in next_4}
        
        pairings = [
            (([next_4[0], next_4[1]], [next_4[2], next_4[3]]), abs((r[next_4[0]] + r[next_4[1]]) - (r[next_4[2]] + r[next_4[3]]))),
            (([next_4[0], next_4[2]], [next_4[1], next_4[3]]), abs((r[next_4[0]] + r[next_4[2]]) - (r[next_4[1]] + r[next_4[3]]))),
            (([next_4[0], next_4[3]], [next_4[1], next_4[2]]), abs((r[next_4[0]] + r[next_4[3]]) - (r[next_4[1]] + r[next_4[2]]))),
        ]
        
        best_pairing = min(pairings, key=lambda x: x[1])[0]
        
        for p in next_4:
            st.session_state.play_counts[p] += 1
            
        st.session_state.courts_state[court_num] = {
            "team1": best_pairing[0],
            "team2": best_pairing[1]
        }
    else:
        st.session_state.courts_state[court_num] = None

# --- MATCHMAKER & SCORING ---
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
            
            # Load DB ratings
            db_ratings = load_player_ratings()
            for p in names:
                if p not in st.session_state.player_ratings:
                    st.session_state.player_ratings[p] = db_ratings.get(p, 1200)
                if p not in st.session_state.league_standings:
                    st.session_state.league_standings[p] = 0
            
            for c in range(1, num_courts + 1):
                assign_next_match_to_court(c)
                
            st.success(f"Session {st.session_state.current_session_num} started! Loaded {len(names)} players across {num_courts} courts.")
            st.rerun()

        st.write("---")
        
        if st.session_state.active_players:
            resting_players = get_resting_players()
            formatted_resting = [f"{p} ({get_letter_grade(st.session_state.player_ratings.get(p, 1200))})" for p in resting_players]
            st.info(f"⏸️ *Players Queueing ({len(resting_players)}):* {', '.join(formatted_resting) if formatted_resting else 'None'}")
            st.write("---")
            
            st.subheader("2. Active Courts (Skill-Balanced Matchmaker)")
            
            for court_num in range(1, num_courts + 1):
                match = st.session_state.courts_state.get(court_num)
                st.markdown(f"### Court {court_num}")
                
                if match:
                    t1_p1, t1_p2 = match['team1'][0], match['team1'][1]
                    t2_p1, t2_p2 = match['team2'][0], match['team2'][1]
                    
                    r = st.session_state.player_ratings
                    t1_g1, t1_g2 = get_letter_grade(r.get(t1_p1, 1200)), get_letter_grade(r.get(t1_p2, 1200))
                    t2_g1, t2_g2 = get_letter_grade(r.get(t2_p1, 1200)), get_letter_grade(r.get(t2_p2, 1200))
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
                    
                    with col1:
                        st.write(f"*Team A:* {t1_p1} [{t1_g1}] & {t1_p2} [{t1_g2}]")
                        s1 = st.number_input(f"Team A Score", min_value=0, max_value=30, value=0, key=f"c{court_num}_s1")
                    
                    with col2:
                        st.markdown("<h3 style='text-align: center; margin-top: 20px;'>VS</h3>", unsafe_allow_html=True)
                    
                    with col3:
                        st.write(f"*Team B:* {t2_p1} [{t2_g1}] & {t2_p2} [{t2_g2}]")
                        s2 = st.number_input(f"Team B Score", min_value=0, max_value=30, value=0, key=f"c{court_num}_s2")
                        
                    with col4:
                        st.write("")
                        st.write("")
                        if st.button(f"💾 Finish Court {court_num}", key=f"btn_{court_num}"):
                            # 1. League points (+2 for win)
                            if s1 > s2:
                                for p in match["team1"]:
                                    st.session_state.session_scores[p] += 2
                                    st.session_state.league_standings[p] += 2
                            elif s2 > s1:
                                for p in match["team2"]:
                                    st.session_state.session_scores[p] += 2
                                    st.session_state.league_standings[p] += 2
                            
                            # 2. Dynamic Rating Grade Update
                            t1_avg = (r.get(t1_p1, 1200) + r.get(t1_p2, 1200)) / 2.0
                            t2_avg = (r.get(t2_p1, 1200) + r.get(t2_p2, 1200)) / 2.0
                            
                            d1, d2 = calculate_rating_change(t1_avg, t2_avg, s1, s2)
                            
                            for p in match["team1"]:
                                st.session_state.player_ratings[p] = max(800, st.session_state.player_ratings.get(p, 1200) + d1)
                                save_player_rating(p, st.session_state.player_ratings[p])
                            for p in match["team2"]:
                                st.session_state.player_ratings[p] = max(800, st.session_state.player_ratings.get(p, 1200) + d2)
                                save_player_rating(p, st.session_state.player_ratings[p])
                            
                            assign_next_match_to_court(court_num)
                            st.success(f"Court {court_num} score saved! Grades updated (Team A {d1:+} pts, Team B {d2:+} pts).")
                            st.rerun()
                else:
                    st.write("No active match on this court.")
                    if st.button(f"⚡ Start Match on Court {court_num}", key=f"start_{court_num}"):
                        assign_next_match_to_court(court_num)
                        st.rerun()
                st.write("---")

    # SEASON CONTROLS TAB (STRICTLY ADMIN & MUSA)
    if can_manage_season:
        with tabs[3]:
            st.subheader("⚙️ Session & Season Controls")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### End Current Session")
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
                if st.button("🔴 End / Reset Entire Season"):
                    st.session_state.current_session_num = 1
                    st.session_state.league_standings = {}
                    st.session_state.session_scores = {}
                    st.session_state.courts_state = {}
                    st.session_state.active_players = []
                    st.session_state.play_counts = {}
                    st.success("Season reset back to Session 1 / 12!")
                    st.rerun()

        # MASTER ADMIN ONLY: USER MANAGEMENT & AUDIT LOGS
        if is_master_admin:
            with tabs[4]:
                st.subheader("👥 User Backend & Activity Logs")
                
                try:
                    users_resp = supabase.table("users").select("*").execute()
                    logs_resp = supabase.table("login_logs").select("username, login_time").order("id", desc=True).limit(50).execute()
                    
                    df_users = pd.DataFrame(users_resp.data) if users_resp.data else pd.DataFrame(columns=["username", "role", "rating", "created_at"])
                    if not df_users.empty:
                        df_users["Grade"] = df_users.get("rating", 1200).apply(lambda x: get_letter_grade(x) if pd.notnull(x) else "B (1200)")
                    
                    df_logs = pd.DataFrame(logs_resp.data) if logs_resp.data else pd.DataFrame(columns=["username", "login_time"])
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Registered Players", len(df_users))
                    c2.metric("Total Login Events", len(df_logs))
                    
                    st.write("---")
                    st.markdown("### 📋 Registered Player Accounts & Grades")
                    st.dataframe(df_users, use_container_width=True)
                    
                    st.write("---")
                    st.markdown("### 🕒 Recent Login Audit Trail")
                    st.dataframe(df_logs, use_container_width=True)
                except Exception as ex:
                    st.warning(f"Database query error: {ex}")

# --- TODAY'S LEADERBOARD ---
today_idx = 1 if can_edit else 0
with tabs[today_idx]:
    st.subheader(f"Today's Session Standings (Session {st.session_state.current_session_num}/12)")
    if st.session_state.session_scores:
        df_today = pd.DataFrame([
            {
                "Player": k,
                "Grade": get_letter_grade(st.session_state.player_ratings.get(k, 1200)),
                "Session Points": v,
                "Games Played": st.session_state.play_counts.get(k, 0)
            }
            for k, v in st.session_state.session_scores.items()
        ]).sort_values(by="Session Points", ascending=False).reset_index(drop=True)
        df_today.index += 1
        st.dataframe(df_today, use_container_width=True)
    else:
        st.info("No games recorded for this session yet.")

# --- 12-SESSION LEAGUE ---
league_idx = 2 if can_edit else 1
with tabs[league_idx]:
    st.subheader(f"🏆 12-Session Overall League (Progress: {st.session_state.current_session_num}/12)")
    if st.session_state.league_standings:
        df_league = pd.DataFrame([
            {
                "Player": k,
                "Grade": get_letter_grade(st.session_state.player_ratings.get(k, 1200)),
                "Total Points": v
            }
            for k, v in st.session_state.league_standings.items()
        ]).sort_values(by="Total Points", ascending=False).reset_index(drop=True)
        df_league.index += 1
        
        st.markdown("### 🥇 Top 3 Leaderboard")
        cols = st.columns(3)
        if len(df_league) >= 1:
            cols[0].metric("🥇 1st Place", f"{df_league.iloc[0]['Player']} [{df_league.iloc[0]['Grade']}]", f"{df_league.iloc[0]['Total Points']} pts")
        if len(df_league) >= 2:
            cols[1].metric("🥈 2nd Place", f"{df_league.iloc[1]['Player']} [{df_league.iloc[1]['Grade']}]", f"{df_league.iloc[1]['Total Points']} pts")
        if len(df_league) >= 3:
            cols[2].metric("🥉 3rd Place", f"{df_league.iloc[2]['Player']} [{df_league.iloc[2]['Grade']}]", f"{df_league.iloc[2]['Total Points']} pts")
            
        st.write("---")
        st.dataframe(df_league, use_container_width=True)
    else:
        st.info("No overall standings recorded yet.")

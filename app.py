import streamlit as st
import pandas as pd
import random
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import time

st.set_page_config(page_title="Slough Badminton Club (Monday)", page_icon="🏸", layout="wide")

# Custom CSS for compact mobile card layout
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stButton button { border-radius: 8px; font-weight: bold; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -0.2rem; }
    .recap-card { background-color: #1E232F; padding: 15px; border-radius: 10px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

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

# --- SUPABASE GLOBAL SESSION PERSISTENCE HELPERS ---
def load_global_session_state():
    try:
        resp = supabase.table("session_state").select("*").eq("id", 1).execute()
        if resp.data:
            row = resp.data[0]
            st.session_state.current_session_num = row.get("current_session_num", 1)
            st.session_state.active_players = row.get("active_players", [])
            st.session_state.session_scores = row.get("session_scores", {})
            st.session_state.league_standings = row.get("league_standings", {})
            st.session_state.play_counts = row.get("play_counts", {})
            st.session_state.recap_stats = row.get("recap_stats", {})
            st.session_state.match_history = row.get("match_history", [])
    except Exception:
        pass

def save_global_session_state():
    try:
        supabase.table("session_state").upsert({
            "id": 1,
            "current_session_num": st.session_state.get("current_session_num", 1),
            "active_players": st.session_state.get("active_players", []),
            "session_scores": st.session_state.get("session_scores", {}),
            "league_standings": st.session_state.get("league_standings", {}),
            "play_counts": st.session_state.get("play_counts", {}),
            "recap_stats": st.session_state.get("recap_stats", {}),
            "match_history": st.session_state.get("match_history", [])
        }).execute()
    except Exception:
        pass

def fetch_live_courts():
    try:
        resp = supabase.table("live_courts").select("*").execute()
        courts = {}
        if resp.data:
            for row in resp.data:
                c_id = row["court_id"]
                if row.get("team_a") and row.get("team_b"):
                    courts[c_id] = {
                        "team1": row["team_a"],
                        "team2": row["team_b"]
                    }
                else:
                    courts[c_id] = None
        return courts
    except Exception:
        return {}

def update_live_court(court_num, team1=None, team2=None):
    try:
        supabase.table("live_courts").upsert({
            "court_id": court_num,
            "team_a": team1,
            "team_b": team2
        }).execute()
    except Exception:
        pass

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

def get_user_role(username, password):
    if username in ADMIN_ACCOUNTS and ADMIN_ACCOUNTS[username] == password:
        return "admin"
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data: return response.data[0]["role"]
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
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    return now_uk.weekday() == 0 and (20 <= now_uk.hour < 22)

# --- PERSISTENT LOGIN ---
query_params = st.query_params
saved_user = query_params.get("user")
saved_role = query_params.get("role")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    if saved_user and saved_role:
        st.session_state.logged_in = True
        st.session_state.username = saved_user
        st.session_state.role = saved_role
        st.session_state.player_ratings = load_player_ratings()
    else:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None

if "player_ratings" not in st.session_state:
    st.session_state.player_ratings = load_player_ratings()
    
if "last_court_time" not in st.session_state:
    st.session_state.last_court_time = {}

if "recap_stats" not in st.session_state:
    st.session_state.recap_stats = {}

if "match_history" not in st.session_state:
    st.session_state.match_history = []

load_global_session_state()

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

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(SVG_URL, width=180)
        st.title("Slough Badminton Club")
        login_tab, signup_tab = st.tabs(["🔒 Log In", "📝 Sign Up"])
        with login_tab:
            with st.form("login_form"):
                st.subheader("Log In")
                username_input = st.text_input("Username").strip()
                password_input = st.text_input("Password", type="password").strip()
                submit_button = st.form_submit_button("Log In", use_container_width=True)
                if submit_button:
                    role = get_user_role(username_input, password_input)
                    if role:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.session_state.role = role
                        st.session_state.player_ratings = load_player_ratings()
                        st.query_params["user"] = username_input
                        st.query_params["role"] = role
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
                signup_btn = st.form_submit_button("Create Account", use_container_width=True)
                if signup_btn:
                    if new_pass != confirm_pass: st.error("Passwords do not match.")
                    elif not new_user or not new_pass: st.error("Please fill in all fields.")
                    else:
                        success, msg = register_user(new_user, new_pass)
                        if success: st.success(msg)
                        else: st.error(msg)
    st.stop()

# --- DYNAMIC PERMISSION CHECK ---
session_live = is_session_active()
can_edit = session_live or (st.session_state.role == "admin")
is_master_admin = (st.session_state.username == "admin")
can_manage_season = (st.session_state.username in ["admin", "Musa"])

st.sidebar.write(f"Logged in as: *{st.session_state.username}* ({st.session_state.role.capitalize()})")
if st.session_state.role == "admin": st.sidebar.success("👑 *Admin User: Full Access Active 24/7*")
elif session_live: st.sidebar.success("🟢 *Session Active (8PM-10PM): Edit Mode Unlocked for All*")
else: st.sidebar.info("🔒 *Outside Session Hours: Read-Only Mode*")
if st.sidebar.button("Log Out", use_container_width=True):
    st.query_params.clear()
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

col_logo, col_title = st.columns([1, 4])
with col_logo: st.image(SVG_URL, width=100)
with col_title:
    st.title("Slough Badminton Club")
    st.caption(f"📅 Season Progress: Session {st.session_state.current_session_num} / 12")

# --- DYNAMIC TAB ROUTING WITH 🔥 HUB ---
tab_names = ["📊 Standings", "🔥 Hub", "🌙 Recap", "🏆 League"]
if can_edit: tab_names.insert(0, "🎾 Courts")
if can_manage_season: tab_names.append("⚙️ Season")
if is_master_admin: tab_names.append("👥 Users")

tabs = st.tabs(tab_names)
tab_courts = tabs[tab_names.index("🎾 Courts")] if "🎾 Courts" in tab_names else None
tab_standings = tabs[tab_names.index("📊 Standings")]
tab_hub = tabs[tab_names.index("🔥 Hub")]
tab_recap = tabs[tab_names.index("🌙 Recap")]
tab_league = tabs[tab_names.index("🏆 League")]
tab_season = tabs[tab_names.index("⚙️ Season")] if "⚙️ Season" in tab_names else None
tab_users = tabs[tab_names.index("👥 Users")] if "👥 Users" in tab_names else None

def get_resting_players(courts_state):
    currently_playing = set()
    for c, match in courts_state.items():
        if match:
            currently_playing.update(match["team1"])
            currently_playing.update(match["team2"])
    
    resting = [p for p in st.session_state.active_players if p not in currently_playing]
    # STRICT PURE FIFO: Sort purely by least games played, then oldest wait time
    return sorted(resting, key=lambda p: (
        st.session_state.play_counts.get(p, 0), 
        st.session_state.last_court_time.get(p, 0)
    ))

def assign_next_match_to_court(court_num, courts_state):
    resting = get_resting_players(courts_state)
    if len(resting) >= 4:
        # PURE ROTATION: Take the exact top 4 longest-waiting players without rating interference
        next_4 = resting[:4]
        
        # Split them evenly into pairs [p1, p2] vs [p3, p4]
        team1 = [next_4[0], next_4[1]]
        team2 = [next_4[2], next_4[3]]
        
        current_time = time.time()
        for p in next_4: 
            st.session_state.play_counts[p] = st.session_state.play_counts.get(p, 0) + 1
            st.session_state.last_court_time[p] = current_time 
            
        update_live_court(court_num, team1, team2)
        save_global_session_state()
        return True
    else:
        update_live_court(court_num, None, None)
        return False

# --- CALLBACK: Process Court Finish & History Log ---
def process_court_finish_callback(court_num, match, s1_key, s2_key):
    s1 = st.session_state.get(s1_key, 0)
    s2 = st.session_state.get(s2_key, 0)
    
    if s1 < 21 and s2 < 21:
        st.session_state[f"msg_{court_num}"] = ("error", f"⚠️ Court {court_num}: At least one team must reach 21 points!")
        return
    if s1 == s2:
        st.session_state[f"msg_{court_num}"] = ("error", f"⚠️ Court {court_num}: Match cannot end in a draw!")
        return
        
    r = st.session_state.player_ratings
    t1_p1, t1_p2 = match['team1'][0], match['team1'][1]
    t2_p1, t2_p2 = match['team2'][0], match['team2'][1]

    match_record = {
        "session": st.session_state.current_session_num,
        "team1": match["team1"],
        "team2": match["team2"],
        "score1": s1,
        "score2": s2
    }
    st.session_state.match_history.append(match_record)

    rs = st.session_state.recap_stats
    rs["total_matches"] = rs.get("total_matches", 0) + 1
    
    lm = rs.get("longest_match", {"s1": 0, "s2": 0})
    if (s1 + s2) > (lm.get("s1", 0) + lm.get("s2", 0)):
        rs["longest_match"] = {"t1": match["team1"], "t2": match["team2"], "s1": s1, "s2": s2}

    is_close = abs(s1 - s2) <= 2
    
    # Calculate rating changes quietly behind the scenes for profile stats
    t1_avg = (r.get(t1_p1, 1200) + r.get(t1_p2, 1200)) / 2.0
    t2_avg = (r.get(t2_p1, 1200) + r.get(t2_p2, 1200)) / 2.0
    
    margin = abs(s1 - s2)
    margin_multiplier = math.log(margin + 1) if margin > 0 else 1.0
    expected1 = 1.0 / (1.0 + 10 ** ((t2_avg - t1_avg) / 400.0))
    expected2 = 1.0 - expected1
    actual1 = 1.0 if s1 > s2 else (0.5 if s1 == s2 else 0.0)
    actual2 = 1.0 - actual1
    d1 = round(32 * margin_multiplier * (actual1 - expected1))
    d2 = round(32 * margin_multiplier * (actual2 - expected2))

    for p in match["team1"]:
        if s1 > s2:
            st.session_state.session_scores[p] = st.session_state.session_scores.get(p, 0) + 2
            st.session_state.league_standings[p] = st.session_state.league_standings.get(p, 0) + 2
            rs.setdefault("player_wins", {})[p] = rs.get("player_wins", {}).get(p, 0) + 1
        rs.setdefault("total_points", {})[p] = rs.get("total_points", {}).get(p, 0) + s1 + s2
        if is_close: rs.setdefault("close_matches", {})[p] = rs.get("close_matches", {}).get(p, 0) + 1
        rs.setdefault("rating_gains", {})[p] = rs.get("rating_gains", {}).get(p, 0) + d1
        
        st.session_state.player_ratings[p] = max(800, st.session_state.player_ratings.get(p, 1200) + d1)
        save_player_rating(p, st.session_state.player_ratings[p])

    for p in match["team2"]:
        if s2 > s1:
            st.session_state.session_scores[p] = st.session_state.session_scores.get(p, 0) + 2
            st.session_state.league_standings[p] = st.session_state.league_standings.get(p, 0) + 2
            rs.setdefault("player_wins", {})[p] = rs.get("player_wins", {}).get(p, 0) + 1
        rs.setdefault("total_points", {})[p] = rs.get("total_points", {}).get(p, 0) + s1 + s2
        if is_close: rs.setdefault("close_matches", {})[p] = rs.get("close_matches", {}).get(p, 0) + 1
        rs.setdefault("rating_gains", {})[p] = rs.get("rating_gains", {}).get(p, 0) + d2
        
        st.session_state.player_ratings[p] = max(800, st.session_state.player_ratings.get(p, 1200) + d2)
        save_player_rating(p, st.session_state.player_ratings[p])

    st.session_state.recap_stats = rs
    st.session_state.pop(s1_key, None)
    st.session_state.pop(s2_key, None)
    
    update_live_court(court_num, None, None)
    save_global_session_state()
    st.session_state[f"msg_{court_num}"] = ("success", f"Court {court_num} score saved successfully!")

# --- COURTS ---
if tab_courts:
    with tab_courts:
        if st.button("🔄 Refresh Live Courts", use_container_width=True):
            st.rerun()
            
        live_courts_state = fetch_live_courts()
        
        with st.expander("⚙️ Session Setup (Tap to expand/hide)", expanded=not bool(st.session_state.active_players)):
            default_names = "Shoj\nAbdul Waheed\nAaron\nFaisal\nNaveed\nAbdulKhader\nRyan\nAbdullah sr\nYousuf\nAamer\nMohsin\nSimon\nJoe S\nHassan\nHabeeb"
            player_text = st.text_area("Enter Player Names Present Tonight (one per line):", value=default_names, height=100)
            num_courts = st.number_input("Number of Courts Available", min_value=1, max_value=6, value=3)
            
            if st.button("✅ Start Session / Populate Courts", use_container_width=True):
                names = [p.strip() for p in player_text.split("\n") if p.strip()]
                st.session_state.active_players = names
                st.session_state.session_scores = {p: 0 for p in names}
                st.session_state.play_counts = {p: 0 for p in names}
                st.session_state.last_court_time = {p: 0 for p in names}
                st.session_state.recap_stats = {}
                st.session_state.match_history = []
                
                db_ratings = load_player_ratings()
                for p in names:
                    if p not in st.session_state.player_ratings:
                        st.session_state.player_ratings[p] = db_ratings.get(p, 1200)
                    if p not in st.session_state.league_standings:
                        st.session_state.league_standings[p] = 0
                for c in range(1, num_courts + 1):
                    update_live_court(c, None, None)
                temp_courts = {}
                for c in range(1, num_courts + 1):
                    assign_next_match_to_court(c, temp_courts)
                    temp_courts = fetch_live_courts()
                save_global_session_state()
                st.success(f"Session {st.session_state.current_session_num} started! Loaded {len(names)} players.")
                st.rerun()

        if st.session_state.active_players:
            resting_players = get_resting_players(live_courts_state)
            formatted_resting = [f"{p}" for p in resting_players]
            st.info(f"⏸️ *Queue ({len(resting_players)}):* {', '.join(formatted_resting) if formatted_resting else 'None'}")
            
            if st.button("💾 Save Everything to Database", type="secondary", use_container_width=True):
                save_global_session_state()
                st.success("Session state successfully saved to Supabase!")

            st.subheader("Live Courts")
            score_pill_options = [i for i in range(0, 31)]
            
            for court_num in range(1, num_courts + 1):
                match = live_courts_state.get(court_num)
                msg = st.session_state.pop(f"msg_{court_num}", None)
                if msg:
                    if msg[0] == "error": st.error(msg[1])
                    elif msg[0] == "success": st.success(msg[1])

                with st.container(border=True):
                    st.markdown(f"#### 🏸 Court {court_num}")
                    if match:
                        t1_p1, t1_p2 = match['team1'][0], match['team1'][1]
                        t2_p1, t2_p2 = match['team2'][0], match['team2'][1]
                        
                        st.caption("🔵 *Team A*")
                        st.write(f"• *{t1_p1}* & *{t1_p2}*")
                        st.pills("Select Team A Score", options=score_pill_options, default=0, key=f"c{court_num}_s1_pills", label_visibility="collapsed")
                        
                        st.write("---")
                        st.caption("🔴 *Team B*")
                        st.write(f"• *{t2_p1}* & *{t2_p2}*")
                        st.pills("Select Team B Score", options=score_pill_options, default=0, key=f"c{court_num}_s2_pills", label_visibility="collapsed")
                        
                        st.write("")
                        st.button(f"💾 Save & Finish Court {court_num}", key=f"btn_{court_num}", type="primary", use_container_width=True, 
                                  on_click=process_court_finish_callback, 
                                  args=(court_num, match, f"c{court_num}_s1_pills", f"c{court_num}_s2_pills"))
                    else:
                        st.caption("No active match on this court.")
                        if st.button(f"⚡ Start Next Match on Court {court_num}", key=f"start_{court_num}", use_container_width=True):
                            assigned = assign_next_match_to_court(court_num, live_courts_state)
                            if not assigned: st.warning("Not enough players in queue.")
                            st.rerun()

# --- STANDINGS ---
with tab_standings:
    st.subheader(f"Today's Session Standings (Session {st.session_state.current_session_num}/12)")
    if st.session_state.session_scores:
        df_today = pd.DataFrame([
            {"Player": k, "Session Points": v, "Games Played": st.session_state.play_counts.get(k, 0)}
            for k, v in st.session_state.session_scores.items()
        ]).sort_values(by="Session Points", ascending=False).reset_index(drop=True)
        df_today.index += 1
        st.dataframe(df_today)
    else:
        st.info("No games recorded for this session yet.")

# --- 🔥 HUB (HEAD-TO-HEAD RIVALRIES & FORM GUIDE) ---
with tab_hub:
    st.header("🔥 Club Hub & Rivalries")
    
    active_pool = st.session_state.get("active_players", [])
    if not active_pool:
        active_pool = sorted(list(st.session_state.player_ratings.keys()))
    
    if len(active_pool) >= 2:
        st.subheader("⚔️ Head-to-Head Rivalry Lookup")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p1 = st.selectbox("Select Player 1", active_pool, index=0)
        with col_p2:
            p2 = st.selectbox("Select Player 2", active_pool, index=1 if len(active_pool) > 1 else 0)
            
        if p1 == p2:
            st.warning("Please select two different players to view their rivalry stats.")
        else:
            history = st.session_state.get("match_history", [])
            p1_wins = 0
            p2_wins = 0
            meetings = 0
            
            for m in history:
                t1 = m["team1"]
                t2 = m["team2"]
                s1 = m["score1"]
                s2 = m["score2"]
                
                p1_in_t1 = p1 in t1
                p1_in_t2 = p1 in t2
                p2_in_t1 = p2 in t1
                p2_in_t2 = p2 in t2
                
                if (p1_in_t1 and p2_in_t2) or (p1_in_t2 and p2_in_t1):
                    meetings += 1
                    if p1_in_t1 and s1 > s2: p1_wins += 1
                    elif p1_in_t2 and s2 > s1: p1_wins += 1
                    elif p2_in_t1 and s1 > s2: p2_wins += 1
                    elif p2_in_t2 and s2 > s1: p2_wins += 1
                    
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{p1} Wins", p1_wins)
            c2.metric("Total Battles", meetings)
            c3.metric(f"{p2} Wins", p2_wins)
            
            if meetings == 0:
                st.info(f"No recorded matches where {p1} and {p2} played directly against each other yet.")
        
        st.write("---")
        st.subheader("⚡ Player Form Barometer")
        selected_player = st.selectbox("Inspect Player Recent Form", active_pool, key="form_player")
        
        player_matches = []
        for m in history:
            if selected_player in m["team1"] or selected_player in m["team2"]:
                in_t1 = selected_player in m["team1"]
                won = (in_t1 and m["score1"] > m["score2"]) or (not in_t1 and m["score2"] > m["score1"])
                player_matches.append("🟢 Win" if won else "🔴 Loss")
                
        if player_matches:
            recent_form = "  ".join(player_matches[-5:])
            st.write(f"*Last {min(5, len(player_matches))} matches for {selected_player}:* {recent_form}")
        else:
            st.info(f"No match history recorded for {selected_player} yet.")
    else:
        st.info("Start a session in the Courts tab to load player names for the Hub.")

# --- RECAP ---
with tab_recap:
    st.header("Night Recap")
    rs = st.session_state.get("recap_stats", {})
    total_matches = rs.get("total_matches", 0)
    current_date = datetime.now(ZoneInfo("Europe/London")).strftime("%d %B %Y")
    st.caption(f"{current_date} · SBC · {total_matches} matches")
    
    if total_matches > 0:
        wins = rs.get("player_wins", {})
        if wins:
            champ = max(wins, key=wins.get)
            with st.container(border=True):
                st.caption("CHAMPION OF THE NIGHT")
                st.markdown(f"*{champ}*")
                st.write(f"{wins[champ]} wins")
                
        lm = rs.get("longest_match", {})
        if lm.get("s1"):
            with st.container(border=True):
                st.caption("LONGEST GAME PLAYED")
                st.markdown(f"*{lm['s1']}–{lm['s2']}*")
                st.write(f"{' & '.join(lm['t1'])} vs {' & '.join(lm['t2'])}")
                
        close = rs.get("close_matches", {})
        if close:
            max_close = max(close.values())
            heroes = [k for k, v in close.items() if v == max_close]
            with st.container(border=True):
                st.caption("HEARTBREAK HEROES")
                st.markdown(f"*{' · '.join(heroes)}*")
                st.write(f"{max_close} close matches (decided by 2 points or fewer)")
                
        pts = rs.get("total_points", {})
        if pts:
            wh = max(pts, key=pts.get)
            with st.container(border=True):
                st.caption("THE WORKHORSE")
                st.markdown(f"*{wh}*")
                st.write(f"{pts[wh]} total points played")
    else:
        st.info("No games finished tonight yet.")

# --- LEAGUE ---
with tab_league:
    st.subheader(f"🏆 12-Session Overall League (Progress: {st.session_state.current_session_num}/12)")
    if st.session_state.league_standings:
        df_league = pd.DataFrame([
            {"Player": k, "Total Points": v}
            for k, v in st.session_state.league_standings.items()
        ]).sort_values(by="Total Points", ascending=False).reset_index(drop=True)
        df_league.index += 1
        st.markdown("### 🥇 Top 3 Leaderboard")
        cols = st.columns(3)
        if len(df_league) >= 1: cols[0].metric("🥇 1st Place", f"{df_league.iloc[0]['Player']}", f"{df_league.iloc[0]['Total Points']} pts")
        if len(df_league) >= 2: cols[1].metric("🥈 2nd Place", f"{df_league.iloc[1]['Player']}", f"{df_league.iloc[1]['Total Points']} pts")
        if len(df_league) >= 3: cols[2].metric("🥉 3rd Place", f"{df_league.iloc[2]['Player']}", f"{df_league.iloc[2]['Total Points']} pts")
        st.write("---")
        st.dataframe(df_league)
    else:
        st.info("No overall standings recorded yet.")

# --- SEASON CONTROLS TAB ---
if tab_season:
    with tab_season:
        st.subheader("⚙️ Session & Season Controls")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### End Current Session")
            if st.button("🏁 End All Games & Complete Session", type="primary", use_container_width=True):
                current_live = fetch_live_courts()
                for c_num, c_match in current_live.items():
                    if c_match:
                        process_court_finish_callback(c_num, c_match, f"c{c_num}_s1_pills", f"c{c_num}_s2_pills")
                if st.session_state.current_session_num < 12: st.session_state.current_session_num += 1
                st.session_state.active_players = []
                st.session_state.session_scores = {}
                st.session_state.play_counts = {}
                st.session_state.recap_stats = {}
                st.session_state.match_history = []
                save_global_session_state()
                st.success(f"Session finished! Advanced to Session {st.session_state.current_session_num} / 12.")
                st.rerun()

        with col_b:
            st.markdown("### Reset Entire Season")
            if st.button("🔴 End / Reset Entire Season", use_container_width=True):
                st.session_state.current_session_num = 1
                st.session_state.league_standings = {}
                st.session_state.session_scores = {}
                st.session_state.active_players = []
                st.session_state.play_counts = {}
                st.session_state.recap_stats = {}
                st.session_state.match_history = []
                for c in range(1, 7): update_live_court(c, None, None)
                save_global_session_state()
                st.success("Season reset back to Session 1 / 12!")
                st.rerun()

# --- USERS ---
if tab_users:
    with tab_users:
        st.subheader("👥 User Backend & Activity Logs")
        try:
            users_resp = supabase.table("users").select("*").execute()
            logs_resp = supabase.table("login_logs").select("username, login_time").order("id", desc=True).limit(50).execute()
            df_users = pd.DataFrame(users_resp.data) if users_resp.data else pd.DataFrame(columns=["username", "role", "created_at"])
            df_logs = pd.DataFrame(logs_resp.data) if logs_resp.data else pd.DataFrame(columns=["username", "login_time"])
            c1, c2 = st.columns(2)
            c1.metric("Registered Players", len(df_users))
            c2.metric("Total Login Events", len(df_logs))
            st.write("---")
            st.markdown("### 📋 Registered Player Accounts")
            st.dataframe(df_users)
            st.write("---")
            st.markdown("### 🕒 Recent Login Audit Trail")
            st.dataframe(df_logs)
        except Exception as ex:
            st.warning(f"Database query error: {ex}")

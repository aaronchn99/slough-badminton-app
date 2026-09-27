import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Slough Badminton Club", layout="wide")

# Persistent User Database in Session Memory
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "adminpassword123", "role": "admin"},
        "Shoj": {"password": "playerpass123", "role": "player"}
    }

# App State Setup
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

if "active_players" not in st.session_state:
    st.session_state.active_players = []
if "session_scores" not in st.session_state:
    st.session_state.session_scores = {}
if "league_standings" not in st.session_state:
    st.session_state.league_standings = {}
if "play_counts" not in st.session_state:
    st.session_state.play_counts = {}

# --- LOGIN / SIGNUP SCREEN ---
if not st.session_state.logged_in:
    st.title("🏸 Slough Badminton Club")
    
    login_tab, signup_tab = st.tabs(["🔒 Log In", "📝 Sign Up"])
    
    with login_tab:
        with st.form("login_form"):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Log In")
            
            if submit_button:
                db = st.session_state.user_database
                if username_input in db and db[username_input]["password"] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.session_state.role = db[username_input]["role"]
                    st.success(f"Welcome back, {username_input}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_button = st.form_submit_button("Create Account")
            
            if signup_button:
                db = st.session_state.user_database
                if new_username in db:
                    st.error("That username is already taken.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not new_username or not new_password:
                    st.error("Please fill in all fields.")
                else:
                    st.session_state.user_database[new_username] = {
                        "password": new_password,
                        "role": "player"
                    }
                    st.success("Account created successfully! Click the Log In tab to sign in.")
    st.stop()

# --- MAIN APP (AFTER LOG IN) ---
st.sidebar.write(f"Logged in as: *{st.session_state.username}* ({st.session_state.role.capitalize()})")
if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

st.title("🏸 Slough Badminton Club")

# Tabs
if st.session_state.role == "admin":
    tabs = st.tabs(["🎾 Matchmaker & Scoring", "📊 Today's Leaderboard", "🏆 12-Session League"])
else:
    tabs = st.tabs(["📊 Today's Leaderboard", "🏆 12-Session League"])

# --- ADMIN PANEL ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.subheader("1. Session Setup")
        
        default_names = "Shoj\nPlayer 2\nPlayer 3\nPlayer 4\nPlayer 5\nPlayer 6\nPlayer 7\nPlayer 8\nPlayer 9\nPlayer 10\nPlayer 11\nPlayer 12\nPlayer 13\nPlayer 14\nPlayer 15"
        player_text = st.text_area("Enter Player Names Present Tonight (one per line):", value=default_names, height=150)
        
        num_courts = st.number_input("Number of Courts Available", min_value=1, max_value=6, value=3)
        
        if st.button("✅ Load / Reset Today's Players"):
            names = [p.strip() for p in player_text.split("\n") if p.strip()]
            st.session_state.active_players = names
            st.session_state.session_scores = {p: 0 for p in names}
            st.session_state.play_counts = {p: 0 for p in names}
            
            for p in names:
                if p not in st.session_state.league_standings:
                    st.session_state.league_standings[p] = 0
            st.success(f"Loaded {len(names)} players for tonight!")

        st.write("---")
        st.subheader("2. Generate Next Round")
        
        if st.button("🔀 Shuffle & Generate Matches"):
            if not st.session_state.active_players:
                st.error("Please load players first above!")
            else:
                # Sort players by least played first to keep turnouts balanced
                available_players = sorted(
                    st.session_state.active_players, 
                    key=lambda p: (st.session_state.play_counts[p], random.random())
                )
                
                max_active_players = num_courts * 4
                active = available_players[:max_active_players]
                resting = available_players[max_active_players:]
                
                for p in active:
                    st.session_state.play_counts[p] += 1
                    
                random.shuffle(active)
                matches = []
                for i in range(0, len(active), 4):
                    group = active[i:i+4]
                    if len(group) == 4:
                        matches.append({
                            "court": (i // 4) + 1,
                            "team1": [group[0], group[1]],
                            "team2": [group[2], group[3]]
                        })
                        
                st.session_state.current_round = {
                    "matches": matches,
                    "resting": resting
                }

        if "current_round" in st.session_state:
            curr = st.session_state.current_round
            if curr["resting"]:
                st.warning(f"⏸️ *Resting this round ({len(curr['resting'])}):* {', '.join(curr['resting'])}")
            
            st.write("---")
            with st.form("match_results"):
                winners = {}
                for m in curr["matches"]:
                    st.markdown(f"#### Court {m['court']}")
                    col1, col2, col3 = st.columns([3, 1, 3])
                    with col1:
                        st.write(f"*Team A:* {m['team1'][0]} & {m['team1'][1]}")
                    with col2:
                        result = st.radio(
                            f"Winner Court {m['court']}", 
                            options=["Team A", "Team B"], 
                            key=f"court_{m['court']}", 
                            label_visibility="collapsed"
                        )
                    with col3:
                        st.write(f"*Team B:* {m['team2'][0]} & {m['team2'][1]}")
                    winners[m['court']] = (result, m['team1'], m['team2'])
                
                if st.form_submit_button("Submit Round Scores"):
                    for court_id, (winner, t1, t2) in winners.items():
                        winning_team = t1 if winner == "Team A" else t2
                        for p in winning_team:
                            st.session_state.session_scores[p] += 2
                            st.session_state.league_standings[p] += 2
                                
                    st.success("Scores updated!")
                    del st.session_state.current_round
                    st.rerun()

# --- TODAY'S LEADERBOARD ---
today_tab = tabs[1] if st.session_state.role == "admin" else tabs[0]
with today_tab:
    st.subheader("Today's Session Standings")
    if st.session_state.session_scores:
        df_today = pd.DataFrame([
            {"Player": k, "Points": v, "Games Played": st.session_state.play_counts.get(k, 0)}
            for k, v in st.session_state.session_scores.items()
        ]).sort_values(by="Points", ascending=False).reset_index(drop=True)
        df_today.index += 1
        st.dataframe(df_today, use_container_width=True)
    else:
        st.info("No games recorded today yet.")

# --- 12-SESSION LEAGUE ---
league_tab = tabs[2] if st.session_state.role == "admin" else tabs[1]
with league_tab:
    st.subheader("🏆 12-Session Overall League")
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

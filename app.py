import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Slough Badminton Club", layout="wide")

# --- User Accounts Setup ---
# You can add your players and their passwords here
USER_DATABASE = {
    "admin": {"password": "adminpassword123", "role": "admin"},
    "Shoj": {"password": "playerpass123", "role": "player"},
    "Player2": {"password": "playerpass123", "role": "player"},
    "Player3": {"password": "playerpass123", "role": "player"}
}

# --- Initialize Session State Data ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

if "players" not in st.session_state:
    st.session_state.players = list(USER_DATABASE.keys())
if "session_scores" not in st.session_state:
    st.session_state.session_scores = {name: 0 for name in USER_DATABASE.keys() if USER_DATABASE[name]["role"] == "player"}
if "league_standings" not in st.session_state:
    st.session_state.league_standings = {name: 0 for name in USER_DATABASE.keys() if USER_DATABASE[name]["role"] == "player"}
if "play_counts" not in st.session_state:
    st.session_state.play_counts = {name: 0 for name in USER_DATABASE.keys() if USER_DATABASE[name]["role"] == "player"}

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.title("🏸 Slough Badminton Club - Login")
    
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Log In")
        
        if submit_button:
            if username_input in USER_DATABASE and USER_DATABASE[username_input]["password"] == password_input:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = USER_DATABASE[username_input]["role"]
                st.success(f"Welcome back, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

# --- MAIN APP (AFTER LOGGING IN) ---
st.sidebar.write(f"Logged in as: *{st.session_state.username}* ({st.session_state.role.capitalize()})")
if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

st.title("🏸 Slough Badminton Club")

# Define Navigation Tabs based on User Role
if st.session_state.role == "admin":
    tabs = st.tabs(["🎾 Matchmaker & Scoring", "📊 Today's Leaderboard", "🏆 12-Session League"])
else:
    # Players can ONLY view the tables, not generate matches or submit scores
    tabs = st.tabs(["📊 Today's Leaderboard", "🏆 12-Session League"])

# --- ADMIN-ONLY MATCHMAKER ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.subheader("Generate Next Round")
        num_courts = st.number_input("Number of Courts Available", min_value=1, max_value=6, value=3)
        
        if st.button("🔀 Shuffle & Generate Matches"):
            active_list = [p for p in st.session_state.session_scores.keys()]
            available_players = sorted(active_list, key=lambda p: (st.session_state.play_counts[p], random.random()))
            
            max_active_players = num_courts * 4
            active_players = available_players[:max_active_players]
            resting_players = available_players[max_active_players:]
            
            for p in active_players:
                st.session_state.play_counts[p] += 1
                
            random.shuffle(active_players)
            matches = []
            for i in range(0, len(active_players), 4):
                group = active_players[i:i+4]
                if len(group) == 4:
                    matches.append({
                        "court": (i // 4) + 1,
                        "team1": [group[0], group[1]],
                        "team2": [group[2], group[3]]
                    })
                    
            st.session_state.current_round = {
                "matches": matches,
                "resting": resting_players
            }

        if "current_round" in st.session_state:
            curr = st.session_state.current_round
            if curr["resting"]:
                st.warning(f"⏸️ *Resting this round:* {', '.join(curr['resting'])}")
            
            st.write("---")
            with st.form("match_results"):
                winners = {}
                for m in curr["matches"]:
                    st.markdown(f"#### Court {m['court']}")
                    col1, col2, col3 = st.columns([3, 1, 3])
                    with col1:
                        st.write(f"*Team A:* {m['team1'][0]} & {m['team1'][1]}")
                    with col2:
                        result = st.radio(f"Winner Court {m['court']}", options=["Team A", "Team B"], key=f"court_{m['court']}", label_visibility="collapsed")
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

# --- TODAY'S LEADERBOARD (VISIBLE TO ALL) ---
today_tab = tabs[1] if st.session_state.role == "admin" else tabs[0]
with today_tab:
    st.subheader("Today's Session Standings")
    df_today = pd.DataFrame([
        {"Player": k, "Points": v, "Games Played": st.session_state.play_counts[k]}
        for k, v in st.session_state.session_scores.items()
    ]).sort_values(by="Points", ascending=False).reset_index(drop=True)
    df_today.index += 1
    st.dataframe(df_today, use_container_width=True)

# --- 12-SESSION LEAGUE (VISIBLE TO ALL) ---
league_tab = tabs[2] if st.session_state.role == "admin" else tabs[1]
with league_tab:
    st.subheader("🏆 12-Session Overall League")
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

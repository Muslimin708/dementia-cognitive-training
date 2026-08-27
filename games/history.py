import streamlit as st
from database import get_game_results

def render(patient_id):
    st.divider(); st.subheader('Game History')
    results = get_game_results(patient_id)
    if not results:
        st.info('No game sessions completed yet.'); return
    games = len(results)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Games Completed', games)
    c2.metric('Average Score', f"{sum(r[3] for r in results)/games:.1f}")
    c3.metric('Average Attempts', f"{sum(r[4] for r in results)/games:.1f}")
    best = max(results, key=lambda r: (r[3]/r[2] if r[2] else 0, r[3]))
    c4.metric('Best Score', f'{best[3]} / {best[2]}')
    for _, game, total, score, attempts, completed in results:
        with st.container(border=True):
            st.write(f'### {game}'); a,b = st.columns(2)
            a.write(f'**Score:** {score} / {total}'); b.write(f'**Attempts:** {attempts}')
            st.caption(f'Completed: {completed}')

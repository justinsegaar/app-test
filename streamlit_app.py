import random

import streamlit as st

from matching import match_guess
from questions import QUESTIONS

st.set_page_config(page_title="Top 10 Quiz", page_icon="🔟", layout="centered")

POINTS_FOR_RANK = {rank: 11 - rank for rank in range(1, 11)}  # plek 1 -> 10 punten, plek 10 -> 1 punt


def init_state():
    st.session_state.setdefault("phase", "setup")


def start_game(team_names):
    num_rounds = min(10, len(QUESTIONS))
    st.session_state.team_names = team_names
    st.session_state.scores = [0] * len(team_names)
    st.session_state.questions = random.sample(QUESTIONS, num_rounds)
    st.session_state.round_idx = 0
    st.session_state.phase = "playing"
    start_round()


def start_round():
    num_teams = len(st.session_state.team_names)
    start_team = st.session_state.round_idx % num_teams
    st.session_state.turn_order = list(range(start_team, num_teams)) + list(range(0, start_team))
    st.session_state.turn_ptr = 0
    st.session_state.round_guesses = {}  # team_idx -> ruwe tekst
    st.session_state.phase = "playing"


def current_question():
    return st.session_state.questions[st.session_state.round_idx]


def render_setup():
    st.title("🔟 Top 10 Quiz")
    st.write(
        "Raad met je vrienden wie of wat er in de top 10 staat. "
        "Plek 1 raden levert 10 punten op, plek 2 negen punten, enzovoort tot en met plek 10 (1 punt)."
    )

    num_teams = st.number_input("Met hoeveel teams spelen jullie?", min_value=2, max_value=8, value=3, step=1)

    team_names = []
    for i in range(num_teams):
        default = f"Team {i + 1}"
        name = st.text_input(f"Naam team {i + 1}", value=default, key=f"team_name_input_{i}")
        team_names.append(name.strip() or default)

    if st.button("Start spel", type="primary"):
        start_game(team_names)
        st.rerun()


def render_playing():
    question = current_question()
    num_rounds = len(st.session_state.questions)
    round_number = st.session_state.round_idx + 1

    st.title("🔟 Top 10 Quiz")
    st.caption(f"Ronde {round_number} van {num_rounds}")
    st.header(question["category"])

    render_scoreboard()

    turn_order = st.session_state.turn_order
    turn_ptr = st.session_state.turn_ptr

    if turn_ptr < len(turn_order):
        team_idx = turn_order[turn_ptr]
        team_name = st.session_state.team_names[team_idx]

        st.info(f"🎤 **{team_name}** is aan de beurt ({turn_ptr + 1}/{len(turn_order)})")

        with st.form(key=f"guess_form_{st.session_state.round_idx}_{turn_ptr}"):
            guess = st.text_input("Antwoord (leeg laten + versturen = passen)")
            submitted = st.form_submit_button("Antwoord geven")

        if submitted:
            st.session_state.round_guesses[team_idx] = guess
            st.session_state.turn_ptr += 1
            st.rerun()

        already_guessed = [
            st.session_state.team_names[i] for i in turn_order[:turn_ptr]
        ]
        if already_guessed:
            st.caption("Al geweest: " + ", ".join(already_guessed))
    else:
        st.success("Alle teams hebben een antwoord gegeven.")
        if st.button("Onthul de top 10", type="primary"):
            st.session_state.phase = "reveal"
            st.rerun()


def render_reveal():
    question = current_question()
    answers = question["answers"]
    num_rounds = len(st.session_state.questions)
    round_number = st.session_state.round_idx + 1

    st.title("🔟 Top 10 Quiz")
    st.caption(f"Ronde {round_number} van {num_rounds}")
    st.header(question["category"])

    guesses = st.session_state.round_guesses  # team_idx -> tekst

    matches_by_rank_index = {}
    unmatched = []
    for team_idx, guess_text in guesses.items():
        if not guess_text.strip():
            continue
        matched_index = match_guess(guess_text, answers)
        if matched_index is not None:
            matches_by_rank_index.setdefault(matched_index, []).append(team_idx)
        else:
            unmatched.append((team_idx, guess_text))

    if "round_scored" not in st.session_state:
        st.session_state.round_scored = False

    if not st.session_state.round_scored:
        for rank_index, team_indices in matches_by_rank_index.items():
            points = POINTS_FOR_RANK[rank_index + 1]
            for team_idx in team_indices:
                st.session_state.scores[team_idx] += points
        st.session_state.round_scored = True

    for rank_index, answer in enumerate(answers):
        rank = rank_index + 1
        points = POINTS_FOR_RANK[rank]
        guessers = matches_by_rank_index.get(rank_index, [])
        line = f"**#{rank}** — {answer} ({points} punten)"
        if guessers:
            names = ", ".join(st.session_state.team_names[t] for t in guessers)
            line += f"  ✅ geraden door: {names}"
        st.markdown(line)

    if unmatched:
        st.divider()
        st.caption("Niet in de top 10 gevonden:")
        for team_idx, guess_text in unmatched:
            st.caption(f"- {st.session_state.team_names[team_idx]}: “{guess_text}”")

    st.divider()
    render_scoreboard()

    is_last_round = st.session_state.round_idx >= num_rounds - 1
    button_label = "Bekijk eindstand" if is_last_round else "Volgende ronde"
    if st.button(button_label, type="primary"):
        del st.session_state.round_scored
        if is_last_round:
            st.session_state.phase = "finished"
        else:
            st.session_state.round_idx += 1
            start_round()
        st.rerun()


def render_scoreboard():
    st.subheader("Stand")
    cols = st.columns(len(st.session_state.team_names))
    for col, name, score in zip(cols, st.session_state.team_names, st.session_state.scores):
        col.metric(name, score)


def render_finished():
    st.title("🏆 Eindstand")

    scores = st.session_state.scores
    names = st.session_state.team_names
    max_score = max(scores)
    winners = [name for name, score in zip(names, scores) if score == max_score]

    if len(winners) == 1:
        st.success(f"🎉 {winners[0]} wint met {max_score} punten!")
    else:
        st.success(f"🎉 Gedeelde winnaars ({max_score} punten): {', '.join(winners)}")

    ranking = sorted(zip(names, scores), key=lambda pair: pair[1], reverse=True)
    for position, (name, score) in enumerate(ranking, start=1):
        st.write(f"{position}. **{name}** — {score} punten")

    if st.button("Nieuw spel"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


init_state()

if st.session_state.phase == "setup":
    render_setup()
elif st.session_state.phase == "playing":
    render_playing()
elif st.session_state.phase == "reveal":
    render_reveal()
elif st.session_state.phase == "finished":
    render_finished()

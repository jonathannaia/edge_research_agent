"""Research Chat — conversational research interface. Phase 1 uses only
canned demo answers (src/data_access/demo/research_answer_provider.py);
there is no LLM call here, per the foundation-phase scope. Conversation
state lives in st.session_state only — nothing persists across a reload.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.formatting import fmt_date
from src.models.models import ChatAnswer
from src.ui.components.badges import claim_type_badge, demo_badge
from src.ui.components.empty_state import empty_state
from src.ui.components.section import section_header

SESSION_KEY = "chat_messages"


def _render_answer_card(answer: ChatAnswer) -> None:
    with st.container(border=True):
        top = st.columns([4, 1])
        with top[0]:
            st.markdown(f"**{answer.question}**")
        with top[1]:
            demo_badge()

        badge_row = st.columns([1, 1, 4])
        with badge_row[0]:
            claim_type_badge(answer.claim_type)
        with badge_row[1]:
            st.badge(f"Confidence: {answer.confidence.value}", color="gray")
        with badge_row[2]:
            st.markdown(f'<div class="er-muted">Freshness: {answer.freshness}</div>', unsafe_allow_html=True)

        st.markdown(f"**What happened**\n\n{answer.what_happened}")
        st.markdown(f"**Why it matters**\n\n{answer.why_it_matters}")
        st.markdown(f"**What may be underappreciated**\n\n{answer.underappreciated}")
        st.markdown(f"**Risks / thesis breakers**\n\n{answer.risks}")
        st.markdown(f"**What to watch next**\n\n{answer.what_to_watch}")

        if answer.sources:
            with st.expander(f"Sources ({len(answer.sources)})"):
                for s in answer.sources:
                    st.markdown(f"- {s.source_name} (no external source — demo data), retrieved {fmt_date(s.retrieved_at)}")
        else:
            st.caption("No sources attached — demo placeholder answer.")


def render() -> None:
    ctx = get_repositories()
    st.markdown("# Research Chat")
    st.write(
        "Ask a research question and get a structured, evidence-labeled answer. In this phase, "
        "answers are canned demo responses only — there is no live model behind this yet."
    )

    suggested = ctx.research_answer_provider.get_suggested_questions()
    if suggested:
        section_header("Suggested research questions")
        cols = st.columns(len(suggested))
        for col, q in zip(cols, suggested):
            with col:
                if st.button(q, key=f"suggested-{q}", width="stretch"):
                    st.session_state.setdefault(SESSION_KEY, []).append(q)

    with st.expander("Saved threads"):
        empty_state(
            "Saved-thread persistence isn't built in this phase.",
            "Phase 2+ would let you name and return to a research thread; today, closing or reloading the page clears the conversation.",
        )

    st.divider()

    messages = st.session_state.setdefault(SESSION_KEY, [])
    if not messages:
        empty_state(
            "No questions asked yet this session.",
            "Try a suggested question above, or type your own below. Every answer will show what "
            "happened, why it matters, what's underappreciated, risks, what to watch, sources, and "
            "a confidence/freshness read — all clearly labeled demo data in this phase.",
        )
    else:
        for q in messages:
            with st.chat_message("user"):
                st.write(q)
            with st.chat_message("assistant"):
                _render_answer_card(ctx.research_answer_provider.get_answer(q))

    typed = st.chat_input("Ask a research question...")
    if typed:
        # chat_input is rendered after the messages read/render block above,
        # so the value appended here wouldn't show until a second rerun
        # without this explicit rerun — unlike the suggested-question
        # buttons above, which append before that same read happens.
        st.session_state.setdefault(SESSION_KEY, []).append(typed)
        st.rerun()

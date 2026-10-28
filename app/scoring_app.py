"""Blind scoring interface.  Run from the repository root:
    PYTHONPATH=src streamlit run app/scoring_app.py
Shows one response at a time with its segment and answer key; never shows model, run or confidence.
Every save is written to scoring/scores/<set>__<scorer>.csv at once, so closing the app loses nothing.
"""
import streamlit as st

from subtext.scoring import (C_CATEGORIES, E_CATEGORIES, is_l3, load_answer_key, load_sheet,
                             make_score_row, read_scores, write_scores)

CATEGORY_HELP = {
    "F": "Fully read: mismatch claimed, both core components match",
    "P": "Partially read: one component, too general, or one side of a mixed valence",
    "N": "Not read: accepts the literal meaning or restates the segment",
    "M": "Misread: opposite valence or unrelated object",
    "A": "Accepted literally (correct for C)",
    "O": "Over-interpreted: claims a mismatch on a C segment",
    "X": "Uncodable: blank, off-task, or misunderstands the literal meaning (reason required)",
}
COMPONENTS = {
    "A": "(1) object evaluated  (2) direction of evaluation",
    "B": "(1) the emotion (same family counts)  (2) the triggering event",
    "C": "(1) words/laughter not at face value, function stated  (2) stance towards the object and its direction",
    "D": "(1) content avoided  (2) power-related reason; opposite intended valence → M",
}
E_NOTE = ("Analysis plan 5.1: on E segments, attributing a feeling or evaluation that is incompatible "
          "with surface_meaning and matches a core component of intended_meaning counts as claiming "
          "a mismatch, without an explicit contrast, provided the literal content is not misstated.")

st.set_page_config(page_title="Blind scoring", layout="wide")

with st.sidebar:
    scorer = st.text_input("Scorer ID", value="XL").strip()
    set_name = st.selectbox("Set", ["practice", "primary", "second"])
    st.caption("Stage: pre-discussion")

if not scorer:
    st.stop()

sheet = load_sheet(set_name)
key = load_answer_key()
scores = read_scores(set_name, scorer)
ids = [e["response_id"] for e in sheet]

state_key = f"idx::{set_name}::{scorer}"
if state_key not in st.session_state:
    first_open = next((i for i, rid in enumerate(ids) if rid not in scores), len(ids) - 1)
    st.session_state[state_key] = first_open
idx = st.session_state[state_key]

with st.sidebar:
    st.progress(len(scores) / len(ids), text=f"{len(scores)} / {len(ids)} scored")
    jump = st.selectbox("Go to", range(len(ids)), index=idx,
                        format_func=lambda i: f"{i + 1:>3}. {ids[i]}  {key[sheet[i]['code']]['id']}"
                                              f"  {'✓' if ids[i] in scores else ''}")
    if jump != idx:
        st.session_state[state_key] = idx = jump

entry = sheet[idx]
seg = key[entry["code"]]
is_e = seg["version"] == "E"
prev = scores.get(entry["response_id"], {})

st.markdown(f"### {seg['id']}  ·  response {entry['response_id']}  ·  {idx + 1} of {len(ids)}")
left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown(f"**Interviewee details:** {seg['details']}")
    with st.container(height=420):
        for para in seg["passage"].split("\n\n"):
            st.markdown(para)
    st.markdown("**Answer key**")
    st.markdown(f"- **surface_meaning:** {seg['surface_meaning']}\n"
                f"- **intended_meaning:** {seg['intended_meaning']}\n"
                f"- **surface_valence:** {seg['surface_valence']}  ·  "
                f"**intended_valence:** {seg['intended_valence']}  ·  "
                f"**author_confidence:** {seg['author_confidence']}")
    if seg["key_cues"]:
        st.markdown("**key_cues:**\n" + "\n".join(f"- {c}" for c in seg["key_cues"]))
    if seg["notes"] and seg["notes"] != "—":
        st.markdown(f"**notes:** {seg['notes']}")
    if is_e:
        st.info(f"Core components, layer {seg['layer'][0]}: {COMPONENTS[seg['layer'][0]]}")

with right:
    st.markdown("**Response: interpretation**")
    st.markdown(f"> {entry['interpretation']}")
    st.markdown(f"**tone:** {entry['tone']}")
    with st.expander("Quotes cited by the response"):
        for q in entry["quotes"]:
            st.markdown(f"- “{q}”")

    st.divider()
    cats = E_CATEGORIES if is_e else C_CATEGORIES
    if is_e:
        st.caption(E_NOTE)
    with st.form(f"form::{set_name}::{scorer}::{entry['response_id']}"):
        cat = st.radio("Category", cats, horizontal=True,
                       index=cats.index(prev["category"]) if prev.get("category") in cats else None,
                       captions=[CATEGORY_HELP[c] for c in cats])
        flag = cue = ctx = None
        if is_e:
            flag = st.checkbox("+ over-extension flag (F or P only)", value=prev.get("flag_plus") == "1")
            cue = st.radio("cue_cited (7.2)", [1, 0], horizontal=True,
                           index=[1, 0].index(int(prev["cue_cited"])) if prev.get("cue_cited") else None)
            if is_l3(seg):
                ctx = st.radio("context_cited (L3)", [1, 0], horizontal=True,
                               index=[1, 0].index(int(prev["context_cited"])) if prev.get("context_cited") else None)
        note = st.text_area("Note (required for X)", value=prev.get("note", ""))
        saved = st.form_submit_button("Save and next", type="primary")

    if saved:
        if cat is None:
            st.error("Choose a category.")
        elif is_e and cue is None:
            st.error("Record cue_cited.")
        elif is_e and is_l3(seg) and ctx is None:
            st.error("Record context_cited.")
        else:
            try:
                scores[entry["response_id"]] = make_score_row(entry, seg, scorer, cat, flag, cue, ctx, note)
            except ValueError as ex:
                st.error(str(ex))
            else:
                write_scores(set_name, scorer, scores)
                st.session_state[state_key] = min(idx + 1, len(ids) - 1)
                st.rerun()

    nav1, nav2 = st.columns(2)
    if nav1.button("← Previous", disabled=idx == 0):
        st.session_state[state_key] = idx - 1
        st.rerun()
    if nav2.button("Next →", disabled=idx == len(ids) - 1):
        st.session_state[state_key] = idx + 1
        st.rerun()

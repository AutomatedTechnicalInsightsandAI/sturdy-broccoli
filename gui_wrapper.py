"""
gui_wrapper.py — Streamlit GUI for the sturdy-broccoli content engine.

Run with:
    streamlit run gui_wrapper.py
"""
from __future__ import annotations

import json

import streamlit as st

from src.prompt_builder import PromptBuilder

st.title("Prompt Generator")

page_data_input = st.text_area(
    "Enter Page Data (JSON):",
    height=300,
    placeholder='{"topic": "...", "primary_keyword": "...", ...}',
)

dry_run = st.checkbox("Dry-run mode (show prompts only, no LLM call)", value=True)

if st.button("Generate Prompts"):
    if not page_data_input.strip():
        st.error("Please enter page data JSON before generating.")
    else:
        try:
            page_data = json.loads(page_data_input)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
        else:
            try:
                builder = PromptBuilder()

                if dry_run:
                    st.subheader("System Prompt")
                    system_prompt = builder.build_system_prompt(page_data)
                    st.code(system_prompt, language="markdown")

                    st.subheader("Chain-of-Thought Prompts")
                    cot_prompts = builder.build_chain_of_thought_prompts(page_data)
                    for stage, prompt in cot_prompts.items():
                        with st.expander(f"Stage: {stage}"):
                            st.code(prompt, language="markdown")
                else:
                    st.info(
                        "Live generation requires an OpenAI API key. "
                        "Use the CLI for full generation: "
                        "`python generator.py generate --page-data <file> --openai-key <key>`"
                    )
            except ValueError as exc:
                st.error(f"Page data validation error: {exc}")
import streamlit as st
from generator import generate_prompts  # Assuming generator.py is in the same directory

# Streamlit application
st.title('Prompt Generator')

# Input fields for users to enter page data
user_input = st.text_area('Enter Page Data:')
dry_run = st.checkbox('Run Dry-Run Mode')

if st.button('Generate Prompts'):
    if user_input:
        prompts = generate_prompts(user_input, dry_run=dry_run)  # Call the generator function
        st.success('Prompts Generated!')
        st.write(prompts)
    else:
        st.error('Please enter valid page data.')
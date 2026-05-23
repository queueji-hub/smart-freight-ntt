import streamlit as st

def init_state():
    if "quotation" not in st.session_state:
        st.session_state.quotation = {
            "items": [],
            "meta": {}
        }

def get():
    return st.session_state.quotation

def set(data):
    st.session_state.quotation = data

def add_item(item):
    st.session_state.quotation["items"].append(item)

def remove_item(index):
    st.session_state.quotation["items"].pop(index)
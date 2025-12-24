import streamlit as st
from core.rag.rag import chatMessage
from core.rag.rag import initRag

if "chain" not in st.session_state:
    st.session_state.chain, st.session_state.get_session_history, st.session_state.retriever, st.session_state.format_docs = initRag()

st.set_page_config(page_title="Chat RAG - NeoFeed", page_icon="🧠", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = st.session_state.messages = [
        {
            "role": "assistant",
            "content": "**NEO**\n\nOi, sou NEO, a inteligência artificial do **NeoFeed**. O que você quer saber sobre o nosso conteúdo?"
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

pergunta = st.chat_input("Digite sua pergunta...")

if pergunta:
    st.session_state.messages.append({"role": "user", "content": pergunta})
    st.chat_message("user").markdown(pergunta)

    with st.chat_message("assistant"):
        resposta_stream = chatMessage(pergunta)
        resposta_final = st.write_stream(resposta_stream)

    st.session_state.messages.append({"role": "assistant", "content": resposta_final})
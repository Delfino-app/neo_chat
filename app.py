import streamlit as st
from index import consultar_rag


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

    mensagens_contexto = st.session_state.messages[-5:]

    with st.chat_message("assistant"):
        resposta_stream = consultar_rag(mensagens_contexto)
        resposta_final = st.write_stream(resposta_stream)

    st.session_state.messages.append({"role": "assistant", "content": resposta_final})
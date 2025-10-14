import streamlit as st
from index import consultar_rag


st.set_page_config(page_title="Chat RAG - NeoFeed", page_icon="🧠", layout="centered")

st.title("🧠 NEO")
st.caption("")

# inicializa histórico
if "messages" not in st.session_state:
    st.session_state.messages = st.session_state.messages = [
        {
            "role": "assistant",
            "content": "**NEO**\n\nOi, sou NEO, a inteligência artificial do **NeoFeed**. O que você quer saber sobre o nosso conteúdo?"
        }
    ]

# mostra histórico anterior
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# entrada do usuário
pergunta = st.chat_input("Digite sua pergunta...")

if pergunta:
    # mostra mensagem do usuário
    st.chat_message("user").markdown(pergunta)
    st.session_state.messages.append({"role": "user", "content": pergunta})

    consultar_rag(pergunta)


import streamlit as st
from index import consultar_rag  # importa a função do teu script principal

# =========================
# 💬 INTERFACE STREAMLIT
# =========================
st.set_page_config(page_title="Chat RAG - NeoFeed", page_icon="🧠", layout="centered")

st.title("🧠 Chat RAG - NeoFeed Demo")
st.caption("Faça perguntas com base nos artigos indexados")

# inicializa histórico
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# mostra histórico anterior
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# entrada do usuário
pergunta = st.chat_input("Digite sua pergunta...")

if pergunta:
    # mostra mensagem do usuário
    st.chat_message("user").markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    # executa busca e resposta
    with st.chat_message("assistant"):
        with st.spinner("Consultando base de artigos..."):
            resposta = consultar_rag(pergunta)
            st.markdown(resposta)

    # salva resposta no histórico
    st.session_state.mensagens.append({"role": "assistant", "content": resposta})

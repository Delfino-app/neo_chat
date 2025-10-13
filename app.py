import streamlit as st
from index import consultar_rag  # importa a função do teu script principal

# =========================
# 💬 INTERFACE STREAMLIT
# =========================
st.set_page_config(page_title="Chat RAG - NeoFeed", page_icon="🧠", layout="centered")

st.title("🧠 NEO")
st.caption("")

# inicializa histórico
if "mensagens" not in st.session_state:
    st.session_state.mensagens = st.session_state.mensagens = [
        {
            "role": "assistant",
            "content": "**NEO**\n\nOi, sou NEO, a inteligência artificial do **NeoFeed**. O que você quer saber sobre o nosso conteúdo?"
        }
    ]

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
        placeholder = st.empty()
        typing_html = """
        <div style='
            font-size: 40px;
            line-height: 1;
            letter-spacing: 3px;
            font-weight: 600;
            color: #555;
            display: inline-block;
        '>
            <span class='dots'></span>
        </div>

        <style>
        @keyframes blink {
            0% { opacity: 0.2; }
            20% { opacity: 1; }
            100% { opacity: 0.2; }
        }
        .dots::after {
            content: '...';
            animation: blink 1.2s infinite;
        }
        </style>
        """
        placeholder.markdown(typing_html, unsafe_allow_html=True)

        # 🔹 Aqui ele processa a consulta enquanto mostra os pontinhos
        resposta = consultar_rag(pergunta)

        # substitui os dots pela resposta final
        placeholder.markdown(resposta)
    st.session_state.mensagens.append({"role": "assistant", "content": resposta})

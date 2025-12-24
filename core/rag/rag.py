import streamlit as st
# LangChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableMap, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from operator import itemgetter
from core.db.loadDB import initDB
import time
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

OPENAI_API_KEY = st.secrets["openai"]["api_key"]
if not OPENAI_API_KEY:
    raise ValueError("A variável OPENAI_API_KEY não foi encontrada no .env!")



@st.cache_resource(show_spinner="Iniciando o Chat...")
def initRag():

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    vectorstore = initDB(embeddings,OPENAI_API_KEY)

    def getPrompt(caminho="./prompts/promptContextual.txt"):
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
        
    template = getPrompt()

    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        temperature=0.1,
        model="gpt-4o-mini",
        streaming=True
    )

    if "data_hoje" not in st.session_state:
        st.session_state.data_hoje = datetime.now().strftime("%Y-%m-%d")
    
    data_hoje = st.session_state.data_hoje

    from core.helpers.chatHelper import customRetrievel, format_docs
    retriever_com_filtro = customRetrievel(vectorstore, k=3)

    base_chain = {
        "input": itemgetter("input"),
        "history": itemgetter("history"),
        "context": itemgetter("context"),
        "data_atual": lambda x: data_hoje
    }

    rag_chain = base_chain | prompt | llm

    store = {}
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
            store[session_id].add_ai_message(
                "Olá! sou o NEO, o assistente conversacional do portal NeoFeed"
                "Posso ajudar você a encontrar informações sobre matérias disponíveis no NeoFeed."
            )
        return store[session_id]

    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    return chain_with_history, get_session_history, retriever_com_filtro, format_docs

def chatMessage(pergunta):

    chain = st.session_state.chain
    get_session_history = st.session_state.get_session_history
    retriever = st.session_state.retriever
    format_docs = st.session_state.format_docs

    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = f"session_{int(time.time())}"

    session_id = st.session_state.chat_session_id
    history = get_session_history(session_id)

    if "working_context" not in st.session_state:
        st.session_state.working_context = None

    try:
        if not pergunta.strip():
            yield "Por favor, faça uma pergunta sobre as matérias disponíveis no NeoFeed."
            return

        history.add_user_message(pergunta)
        resposta_final = ""

        from core.helpers.chatHelper import should_retrieve

        if st.session_state.working_context and not should_retrieve(pergunta, st.session_state.working_context):
            print("DEBUG - Usando contexto já existente...")
            contexto = st.session_state.working_context
        else:
            print("DEBUG - Realizando retrieval de documentos...")
            docs = retriever.invoke(pergunta)
            contexto = format_docs(docs)
            st.session_state.working_context = contexto
            print(f"DEBUG - \n contexto: {contexto}")


        payload = {
            "input": pergunta,
            "context": contexto
        }

        response = chain.stream(
            payload,
            config={"configurable": {"session_id": session_id}}
        )

        for chunk in response:
            if hasattr(chunk, 'content'):
                texto = chunk.content.replace("$", "\\$")
                resposta_final += texto
                time.sleep(0.08)
                yield texto

        if resposta_final.strip():
            history.add_ai_message(resposta_final)

    except Exception as e:
        yield "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."
        st.error(f"Erro no sistema: {str(e)}")

if __name__ == "__main__":
    # Teste simples do streaming
    initRag()
    print()
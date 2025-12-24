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

    def format_docs(docs):
        formatted = []        
        for doc in docs:

            doc_info = []
            

            if doc.metadata.get('titulo'):
                doc_info.append(f"Título: {doc.metadata['titulo']}")
            
            doc_info.append(f"Conteúdo: {doc.metadata['conteudo']}")

            if doc.metadata.get('categoria'):
                doc_info.append(f"Categoria: {doc.metadata['categoria']}")
            if doc.metadata.get('link'):
                doc_info.append(f"Link: {doc.metadata['link']}")
            if doc.metadata.get('data'):
                doc_info.append(f"Data: {doc.metadata['data']}")
            if doc.metadata.get('autor'):
                doc_info.append(f"Autor: {doc.metadata['autor']}")
            
            formatted.append("\n".join(doc_info))
        
        return "\n\n---\n\n".join(formatted)

    if "data_hoje" not in st.session_state:
        st.session_state.data_hoje = datetime.now().strftime("%Y-%m-%d")
    
    data_hoje = st.session_state.data_hoje

    from core.helpers.chatHelper import customRetrievel
    retriever_com_filtro = customRetrievel(vectorstore, k=3)

    retrieval_chain = {
        "input": itemgetter("input"),
        "history": itemgetter("history"),
        "data_atual": lambda x: data_hoje
    } | RunnablePassthrough.assign(
        context=itemgetter("input") | retriever_com_filtro | format_docs
    )

    rag_chain = retrieval_chain | prompt | llm

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

    return chain_with_history, get_session_history
def chatMessage(pergunta):
    
    chain = st.session_state.chain
    get_session_history = st.session_state.get_session_history

    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = f"session_{int(time.time())}"
    
    session_id = st.session_state.chat_session_id

    history = get_session_history(session_id)
    
    try:

        if not pergunta.strip():
            yield "Por favor, faça uma pergunta sobre as matérias disponíveis no Neofeed."
            return
        
        history.add_user_message(pergunta)
        resposta_final = ""

        response = chain.stream(
            {
               "input": pergunta,
            },
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
        
def chatMessages(pergunta):
    
    chain = st.session_state.chain
    get_session_history = st.session_state.get_session_history

    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = f"session_{int(time.time())}"
    
    session_id = st.session_state.chat_session_id

    history = get_session_history(session_id)
    
    try:

        if not pergunta.strip():
            yield "Por favor, faça uma pergunta sobre as matérias disponíveis no Neofeed."
            return
        
        history.add_user_message(pergunta)
        resposta_final = ""

        retriever = st.session_state.retriever
        from core.helpers.chatHelper import buscar_docs
        input_texto = buscar_docs(pergunta,retriever)

        response = chain.stream(
            {
               "input": input_texto or pergunta
            },
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
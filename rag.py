import streamlit as st
# LangChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableMap, RunnablePassthrough
from langchain_community.vectorstores import Chroma
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from operator import itemgetter
from langchain_community.document_loaders import SQLDatabaseLoader
from langchain_community.utilities import SQLDatabase


OPENAI_API_KEY = st.secrets["openai"]["api_key"]
if not OPENAI_API_KEY:
    raise ValueError("A variável OPENAI_API_KEY não foi encontrada no .env!")

@st.cache_resource(show_spinner=False)
def inicializar_sistema():

    # Conecta ao banco SQLite
    db = SQLDatabase.from_uri("sqlite:///artigos.db")
    loader = SQLDatabaseLoader(
        db=db,
        query="SELECT titulo, autor, data, link, conteudo, doc_id FROM artigos ORDER BY data DESC;"
    )

    documents = loader.load()
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    vectorstore = Chroma.from_documents(
        documents=documents,
        collection_name="artigos_demo",
        embedding=embeddings,
        persist_directory="./chroma_db"
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    def getPrompt(caminho="prompt.txt"):
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
        temperature=0.3,
        model="gpt-4o-mini",
        streaming=True
    )

    retrieval_chain = itemgetter("input") | retriever

    rag_chain = RunnableMap({
        "context": retrieval_chain,  
        "input": itemgetter("input"),  
        "history": itemgetter("history"),
    }) | prompt | llm

    store = {}
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    return chain_with_history

def chatMessage(pergunta):
    
    chain = inicializar_sistema()

    if 'chat_session_id' not in st.session_state:
        import time
        st.session_state.chat_session_id = f"session_{int(time.time())}"
    
    session_id = st.session_state.chat_session_id
    
    try:

        response = chain.stream(
            {
                "input": pergunta
            },
            config={"configurable": {"session_id": session_id}}
        )
        
        for chunk in response:
            if hasattr(chunk, 'content'):
                yield chunk.content
    except Exception as e:
        yield f"❌ Erro: {str(e)}"

if __name__ == "__main__":
    # Teste simples do streaming
    for token in chatMessage("Qual é o último artigo?"):
        print(token, end="", flush=True)
    print()

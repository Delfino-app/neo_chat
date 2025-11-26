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
from langchain_text_splitters import RecursiveCharacterTextSplitter
import time

OPENAI_API_KEY = st.secrets["openai"]["api_key"]
if not OPENAI_API_KEY:
    raise ValueError("A variável OPENAI_API_KEY não foi encontrada no .env!")

def load_documents_from_sql():

    import sqlite3
    conn = sqlite3.connect('artigos.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT titulo, categoria, autor, data, link, conteudo, doc_id FROM artigos")
    rows = cursor.fetchall()
    
    documents = []
    for row in rows:
        titulo, autor, categoria, data, link, conteudo, doc_id = row

        titulo = titulo.replace('$', '\\$')
        conteudo = conteudo.replace('$', '\\$')

        from langchain_core.documents import Document
        doc = Document(
            page_content=conteudo or "",
            metadata={
                "titulo": titulo or "",
                "autor": autor or "", 
                "categoria": categoria or "",
                "data": data or "",
                "link": link or "",
                "doc_id": doc_id or "",
                "doc_type": "artigo"
            }
        )
        documents.append(doc)
    
    conn.close()
    return documents


def reloadVetorDB():

    documents = load_documents_from_sql()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata.update({
            "doc_type": "artigo",
            "titulo": chunk.metadata.get("titulo", ""),
            "categoria": chunk.metadata.get("categoria", ""),
            "data": chunk.metadata.get("data", ""),
            "autor": chunk.metadata.get("autor", "")
        })

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # Recria o Chroma
    vectorstore = Chroma.from_documents(
        documents=chunks,
        collection_name="artigos_demo",
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    
    return vectorstore


#@st.cache_resource(show_spinner="Iniciando o Chat...")
def initRag():

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    try:

        vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embeddings,
            collection_name="artigos_demo"
        )
        
        doc_count = vectorstore._collection.count()
        
        if doc_count == 0:
            vectorstore = reloadVetorDB()
        
    except Exception as e:
        vectorstore = reloadVetorDB()

    retriever = vectorstore.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 8}
    )

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
        temperature=0.1,
        model="gpt-4o-mini",
        streaming=True
    )

    def format_docs(docs):
        formatted = []
        
        for doc in docs:
            link = doc.metadata.get('link', '')
            if any(proibido in link for proibido in ['/brand-stories/', '/apresentado-por-']):
                continue
                
            doc_info = []
            
            # Título
            if doc.metadata.get('titulo'):
                doc_info.append(f"Título: {doc.metadata['titulo']}")
            
            # Conteúdo
            doc_info.append(f"Conteúdo: {doc.page_content}")
            
            # Metadados
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
    
    retrieval_chain = {
        "input": itemgetter("input"),
        "history": itemgetter("history")
    } | RunnablePassthrough.assign(
        context=itemgetter("input") | retriever | format_docs
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
                "input": pergunta
            },
            config={"configurable": {"session_id": session_id}}
        )
        
        for chunk in response:
            if hasattr(chunk, 'content'):
                texto = chunk.content.replace("$", "\\$")
                resposta_final += texto
                time.sleep(0.07)
                yield texto

               

        if resposta_final.strip():
            history.add_ai_message(resposta_final)
                
    except Exception as e:
        st.error(f"Erro no sistema: {str(e)}")
        yield "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."

if __name__ == "__main__":
    # Teste simples do streaming
    initRag()
    print()
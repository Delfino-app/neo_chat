from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

DB_NAME = "artigos_demo";

CHROMA_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(CHROMA_BASE_DIR, 'chroma_db')

def initDB(embeddings,openai_api_key) :
    try:

        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings,
            collection_name=DB_NAME
        )

        doc_count = vectorstore._collection.count()
        
        if doc_count == 0:
            vectorstore = reloadVetorDB(embeddings,openai_api_key)
        
    except Exception as e:
        vectorstore = reloadVetorDB(embeddings,openai_api_key)

    return vectorstore

def load_documents_from_sql():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'artigos.db')

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
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
            page_content=f"""
                Título: {titulo}
                Categoria: {categoria}
                Autor: {autor}
                Data: {data}
                Link: {link}

                Conteúdo:
                {conteudo}
            """,
            metadata={
                "titulo": titulo,
                "autor": autor,
                "categoria": categoria,
                "data": data,
                "link": link,
                "doc_id": doc_id,
                "doc_type": "artigo",
                "conteudo": conteudo
            }
        )


        documents.append(doc)
    
    conn.close()
    return documents


def reloadVetorDB(embeddings,openai_api_key):

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

    embeddings = OpenAIEmbeddings(api_key=openai_api_key)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        collection_name=DB_NAME,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH
    )
    
    return vectorstore

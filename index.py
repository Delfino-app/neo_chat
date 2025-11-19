import streamlit as st
from langchain_core.documents import Document

def load_documents_from_sql():
    import sqlite3
    conn = sqlite3.connect('artigos.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT titulo, autor, categoria, data, link, conteudo, doc_id FROM artigos")
    rows = cursor.fetchall()
    
    documents = []
    for row in rows:
        titulo, autor, categoria, data, link, conteudo, doc_id = row

        titulo = (titulo or "").replace('$', '\\$')
        conteudo = (conteudo or "").replace('$', '\\$')

        doc = Document(
            page_content=conteudo,
            metadata={
                "titulo": titulo,
                "autor": autor or "",
                "categoria" : categoria or "", 
                "data": data or "",
                "link": link or "",
                "doc_id": doc_id or "",
                "doc_type": "artigo"
            }
        )
        documents.append(doc)
    
    conn.close()
    return documents


# ---------------------
# Página do Streamlit
# ---------------------

st.title("Lista de Matérias")

docs = load_documents_from_sql()

# Se quiser só os títulos, um embaixo do outro:
for doc in docs:
    st.markdown(f"### {doc.metadata['titulo']}")
    st.caption(f"Categoria: {doc.metadata['categoria']} | Autor: {doc.metadata['autor']} | Data: {doc.metadata['data']}")
    st.divider()


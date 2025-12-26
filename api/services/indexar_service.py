from bs4 import BeautifulSoup
from core.db.storage import save
from core.db.loadDB import addDocumentToVectorstore
from getRequests import limpar_caracteres_agressivo
import streamlit as st

def limpar_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    return soup.get_text(separator=" ", strip=True)


def indexar_post(payload):
    logs = []
    
    conteudo_limpo = limpar_caracteres_agressivo(payload.conteudo)
    conteudo_limpo = limpar_html(conteudo_limpo)


    doc = {
        "doc_id": f"artigo-{payload.id}",
        "titulo": payload.title,
        "conteudo": conteudo_limpo,
        "categoria": payload.categoria,
        "autor": payload.autor,
        "data": payload.data,
        #"tags": payload.tags,
        "link": payload.link,
       
    }

    save([doc])

    logs.append(f"Matéria adicionada ao banco: {payload.title}")

    OPENAI_API_KEY = st.secrets["openai"]["api_key"]

    total_chunks = addDocumentToVectorstore(
        doc,
        openai_api_key=OPENAI_API_KEY
    )

    logs.append(f"{total_chunks} chunks indexados no vectorstore (doc_id={doc['doc_id']})")

    return logs

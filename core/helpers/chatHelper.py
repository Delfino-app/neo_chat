import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from langchain_core.runnables import RunnableLambda
except ImportError:
    from langchain.schema.runnable import RunnableLambda

def customRetrievel(vectorstore, k=3):

    def detectar_metadado(pergunta: str):

        pergunta = pergunta.lower()
        if "autor" in pergunta or "quem escreveu" in pergunta:
            return "autor"
        if "data" in pergunta or "quando foi publicada" in pergunta:
            return "data"
        if "categoria" in pergunta:
            return "categoria"
        if "título" in pergunta or "título da matéria" in pergunta:
            return "titulo"
        return None

    def retriever_com_filtro(pergunta: str):
        filtro_data = detectar_filtro_data(pergunta)

        print(f"DEBUG - Filtro aplicado: {filtro_data}")

        quer_apenas_um = any(
            palavra in pergunta.lower() 
            for palavra in ['uma materia', 'uma notícia', 'uma matéria', 'um artigo']
        )
        k_final = 1 if quer_apenas_um else k

        metadado_foco = detectar_metadado(pergunta)
        sourceDocs = vectorstore.similarity_search(
            pergunta,
            k=20,
            filter=filtro_data
        )

        if metadado_foco:
            sourceDocs.sort(
                key=lambda d: d.metadata.get(metadado_foco, ""),
                reverse=True
            )
        else:
            sourceDocs.sort(
                key=lambda d: d.metadata.get("data", ""),
                reverse=True
            )

        docs = sourceDocs[:k_final]
        vistos = set()
        docs_unicos = []

        for doc in docs:
            doc_id = doc.metadata.get("doc_id", "")
            doc_link = doc.metadata.get("link", "")
            identificador = f"{doc_id}_{doc_link}"

            if not doc_link:
                continue

            if identificador not in vistos:
                vistos.add(identificador)
                docs_unicos.append(doc)

        print(f"DEBUG - Documentos encontrados: {len(docs_unicos)}")
        return docs_unicos

    return RunnableLambda(retriever_com_filtro)


def detectar_filtro_data(consulta: str):
    consulta_lower = consulta.lower().strip()
    
    from core.helpers.detectorTemporalNoticias import DetectorTemporalNoticias
    detector = DetectorTemporalNoticias()
    filtro_temporal = detector.detectar_filtro_temporal(consulta_lower)
    
    if filtro_temporal and '$gte' in filtro_temporal:
        return {"data": filtro_temporal['$gte']}  
    
    elif filtro_temporal and 'data' in filtro_temporal:
        return {"data": filtro_temporal['data']} 
    
    else:
        return None

def format_docs(docs):

    formatted = []

    for doc in docs:
        doc_info = []

        doc_info.append(f"Título: {doc.metadata.get('titulo', 'N/A')}")
        doc_info.append(f"Autor: {doc.metadata.get('autor', 'N/A')}")
        doc_info.append(f"Categoria: {doc.metadata.get('categoria', 'N/A')}")
        doc_info.append(f"Data: {doc.metadata.get('data', 'N/A')}")
        doc_info.append(f"Link: {doc.metadata.get('link', 'N/A')}")

        conteudo = doc.metadata.get('conteudo', '') or doc.page_content
        if conteudo:
            doc_info.append(f"Conteúdo: {conteudo.strip()}")

        formatted.append("\n".join(doc_info))

    return "\n\n---\n\n".join(formatted)

def should_retrieve(pergunta, working_context):
    
    if working_context:
        followup_gatilhos = [
            "resume", "resuma", "resumo",
            "bullets", "lista", "tópicos",
            "explique melhor", "reescreve",
            "agora", "continue"
        ]
        if any(g in pergunta.lower() for g in followup_gatilhos):
            return False

        metadado_gatilhos = [
            "autor", "quem escreveu",
            "data", "quando foi publicada",
            "categoria", "título", "link"
        ]
        if any(g in pergunta.lower() for g in metadado_gatilhos):
            return False
        
        triviais = ["olá", "oi", "bom dia", "boa tarde", "boa noite", "tudo bem", "prazer"]
        if any(t in pergunta.lower() for t in triviais):
            return False
        
    return True

if __name__ == "__main__":
    resultado = detectar_filtro_data("Novidades")
    print(resultado)
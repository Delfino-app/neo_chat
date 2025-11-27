import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from langchain_core.runnables import RunnableLambda
except ImportError:
    from langchain.schema.runnable import RunnableLambda

def customRetrievel(vectorstore, k=3):

    def retriever_com_filtro(pergunta: str):
        filtro_data = detectar_filtro_data(pergunta)
        print(f"DEBUG - Filtro aplicado: {filtro_data}")
        
        # Detecta se quer apenas uma matéria
        quer_apenas_um = any(palavra in pergunta.lower() for palavra in 
                            ['uma materia', 'uma notícia', 'uma matéria', 'um artigo'])
        
        k_final = 1 if quer_apenas_um else k
        
        docs = vectorstore.similarity_search(
            pergunta, 
            k=k_final, 
            filter=filtro_data
        )
        
        # Remove duplicados
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

def buscar_docs(pergunta, retriever):
    
    filtro_data = detectar_filtro_data(pergunta)
    print(f"Filtro SQL: {filtro_data}")
    
    quer_apenas_um = any(palavra in pergunta.lower() for palavra in 
                        ['uma materia', 'uma notícia', 'uma matéria', 'um artigo'])
    
    k = 1 if quer_apenas_um else 3
    
    docs = retriever.invoke(pergunta, filter=filtro_data, k=k)

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

    input_texto = "\n\n---\n\n".join( [f"Título: {d.metadata.get('titulo','')}\nData: {d.metadata.get('data','')}\nLink: {d.metadata.get('link','')}\nConteúdo: {d.page_content}" for d in docs_unicos] )

    return input_texto

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

if __name__ == "__main__":
    resultado = detectar_filtro_data("Novidades")
    print(resultado)
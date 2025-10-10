from openai import OpenAI
import chromadb
import pandas as pd
import tiktoken 
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠️ A variável OPENAI_API_KEY não foi encontrada no .env!")

client = OpenAI(api_key=OPENAI_API_KEY)

# Banco vetorial local (persistência automática na pasta ./chroma)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("artigos_demo")

# --- 1. Carregar CSV ---
df = pd.read_csv("artigos.csv")
print(f"Carregando {len(df)} artigos...")

# --- 2. Gerar embeddings e armazenar ---
for i, row in df.iterrows():
    
    text = (
        f"Título: {row['titulo']}\n"
        f"Autor: {row['autor']}\n"
        f"Data: {row['data']}\n"
        f"Link: {row['link']}\n\n"
        f"{row['conteudo']}"
    )

    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

    collection.add(
        ids=[f"artigo-{i}"],
        embeddings=[emb],
        documents=[text],
        metadatas=[{
            "titulo": row["titulo"],
            "data": row["data"],
            "autor": row["autor"],
            "link": row["link"]
        }]
    )



print("Embeddings salvos no banco vetorial ✅")

# --- 3. Função de consulta ---
def consultar_rag(pergunta, top_k=3):
    q_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=pergunta
    ).data[0].embedding

    resultados = collection.query(
        query_embeddings=[q_emb],
        n_results=top_k
    )

    docs = resultados["documents"][0]
    metas = resultados["metadatas"][0]

    contexto = ""
    for doc, meta in zip(docs, metas):
        contexto += (
            f"Título: {meta['titulo']}\n"
            f"Autor: {meta['autor']}\n"
            f"Data: {meta['data']}\n"
            f"Link: {meta['link']}\n"
            f"Texto: {doc}\n---\n"
        )

    prompt = f"""
    Você é um assistente que responde perguntas com base nos matérias abaixo.
    Use apenas essas informações.

    Pergunta: {pergunta}

    Matérias:
    {contexto}

    Resposta:
    """

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    print("🧠 Resposta:", resposta.choices[0].message.content.strip())

# --- 4. Testar ---
consultar_rag("Links de materias do dia 02")

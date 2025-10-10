from openai import OpenAI
import chromadb
import pandas as pd
import tiktoken 
from datetime import datetime
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠️ A variável OPENAI_API_KEY não foi encontrada no .env!")

client = OpenAI(api_key=OPENAI_API_KEY)

# Limpa o banco vetorial (apenas se desejar reiniciar tudo)
if os.path.exists("./chroma_db"):
    print("🧹 Limpando banco vetorial existente...")
    shutil.rmtree("./chroma_db", ignore_errors=True)

# Banco vetorial local (persistência na pasta ./chroma_db)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("artigos_demo")

# =====================================
# 🧠 FUNÇÕES AUXILIARES
# =====================================

# 👉 Formatar datas em Y-m-d
def formatar_data(data_str):
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formatos:
        try:
            return datetime.strptime(data_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return data_str  # caso não consiga converter

# 👉 Dividir textos longos em partes menores
tokenizer = tiktoken.get_encoding("cl100k_base")

def dividir_em_chunks(texto, max_tokens=800):
    tokens = tokenizer.encode(texto)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        trecho = tokenizer.decode(tokens[i:i + max_tokens])
        chunks.append(trecho)
    return chunks

# =====================================
# 📄 CARREGAR CSV E POPULAR CHROMA
# =====================================
df = pd.read_csv("artigos.csv")
print(f"📰 Carregando {len(df)} artigos...")

if collection.count() == 0:
    print("⚙️ Gerando embeddings e populando o banco...")
    for i, row in df.iterrows():
        doc_id = f"artigo-{i}"  # 🔹 identificador único por artigo
        full_text = (
            f"Título: {row['titulo']}\n"
            f"Autor: {row['autor']}\n"
            f"Data: {formatar_data(row['data'])}\n"
            f"Link: {row['link']}\n\n"
            f"{row['conteudo']}"
        )

        # divide em blocos (caso o conteúdo seja longo)
        for j, chunk in enumerate(dividir_em_chunks(full_text)):
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            ).data[0].embedding

            collection.add(
                ids=[f"{doc_id}-{j}"],
                embeddings=[emb],
                documents=[chunk],
                metadatas=[{
                    "doc_id": doc_id,
                    "titulo": row["titulo"],
                    "data": formatar_data(row["data"]),
                    "autor": row["autor"],
                    "link": row["link"]
                }]
            )
    print("✅ Embeddings salvos no banco vetorial.")
else:
    print(f"ℹ️ Banco vetorial já contém {collection.count()} vetores. Pulando criação.")

# =====================================
# 🔍 CONSULTA RAG
# =====================================
def consultar_rag(pergunta, top_k=5):
    q_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=pergunta
    ).data[0].embedding

    # Pega mais resultados brutos (garante artigos suficientes após deduplicar)
    resultados = collection.query(
        query_embeddings=[q_emb],
        n_results=top_k * 3
    )

    docs = resultados["documents"][0]
    metas = resultados["metadatas"][0]

    if not metas:
        print("🧠 Resposta: Nenhum resultado encontrado.")
        return

    artigos_unicos = {}
    links_vistos = set()

    for doc, meta in zip(docs, metas):
        doc_id = str(meta.get("doc_id", "")).strip().lower()
        link = str(meta.get("link", "")).strip().lower()

        if not doc_id or not link:
            continue

        # 🔹 Evita duplicatas por doc_id ou link
        if doc_id in artigos_unicos or link in links_vistos:
            continue

        artigos_unicos[doc_id] = {
            "titulo": meta.get("titulo", "(sem título)").strip(),
            "autor": meta.get("autor", "(sem autor)").strip(),
            "data": meta.get("data", "(sem data)").strip(),
            "link": meta.get("link", "(sem link)").strip(),
            "texto": doc
        }
        links_vistos.add(link)

        # 🔹 Interrompe quando já tem top_k artigos únicos
        if len(artigos_unicos) >= top_k:
            break

    if not artigos_unicos:
        print("🧠 Resposta: Nenhum artigo relevante encontrado.")
        return

    # 🔹 Monta o contexto final
    contexto = ""
    for artigo in artigos_unicos.values():
        resumo = artigo['texto'].split("\n")
        resumo_texto = "\n".join(resumo[:6])  # só as primeiras linhas do chunk

        contexto += (
            f"Título: {artigo['titulo']}\n"
            f"Autor: {artigo['autor']}\n"
            f"Data: {artigo['data']}\n"
            f"Link: {artigo['link']}\n\n"
            f"{resumo_texto}\n---\n"
        )

    prompt = f"""
    Você é um assistente que responde perguntas com base nas matérias abaixo.
    Use **apenas** essas informações — não invente fatos nem links.
    Quando relevante, apresente os resultados em formato de lista (com Título e Link). Não repita materias com o mesmo Link

    Pergunta: {pergunta}

    Matérias:
    {contexto}

    Responda de forma objetiva e natural:
    """

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    print("\n🧠 Resposta:")
    print(resposta.choices[0].message.content.strip())
    print("\n" + "=" * 70 + "\n")



# =====================================
# 💬 MODO INTERATIVO
# =====================================
if __name__ == "__main__":
    print("\n💬 Modo Chat RAG iniciado! (digite 'sair' para encerrar)\n")
    while True:
        pergunta = input("❓ Pergunta: ").strip()
        if pergunta.lower() in ["sair", "exit", "quit"]:
            print("👋 Encerrando...")
            break
        if pergunta:
            consultar_rag(pergunta)
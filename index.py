from openai import OpenAI
import chromadb
import pandas as pd
import tiktoken
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from getRequests import atualizar_db_com_wp
from storage import load_posts
import streamlit as st

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("⚠️ A variável OPENAI_API_KEY não foi encontrada no .env!")

client = OpenAI(api_key=OPENAI_API_KEY)

# Banco vetorial local (persistência em ./chroma_db)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("artigos_demo")

# Tokenizer para dividir textos longos
tokenizer = tiktoken.get_encoding("cl100k_base")


# =====================================
# 🧩 FUNÇÕES AUXILIARES
# =====================================

def formatar_data(data_str):
    """Converte datas para o formato YYYY-MM-DD."""
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formatos:
        try:
            return datetime.strptime(data_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return data_str


def dividir_em_chunks(texto, max_tokens=800):
    """Divide textos longos em blocos menores para embeddings."""
    tokens = tokenizer.encode(texto)
    return [tokenizer.decode(tokens[i:i + max_tokens]) for i in range(0, len(tokens), max_tokens)]


# =====================================
# 📰 ATUALIZAÇÃO AUTOMÁTICA DO BANCO
# =====================================
def updatePostsDB():
    print("Atualizando banco de matérias a partir do WordPress...")
    try:
        atualizar_db_com_wp()
    except Exception as e:
        print(f"Erro ao atualizar matérias: {e}")
        
# =====================================
# 💾 POPULAR CHROMA (INDEXAÇÃO RAG)
# =====================================
def popular_chroma(df):
    existentes = collection.count()
    novos = 0

    if existentes == 0:
        print("⚙️ Banco vetorial vazio. Criando embeddings...")
    else:
        print(f"ℹ️ Banco vetorial já contém {existentes} vetores. Verificando novos artigos...")

    for _, row in df.iterrows():
        doc_id = str(row["doc_id"]).strip()
        if not doc_id:
            continue

        # Verifica se o artigo já foi indexado no Chroma (pelo doc_id)
        existentes_doc = collection.get(where={"doc_id": doc_id})
        if existentes_doc and existentes_doc.get("ids"):
            continue  # já existe

        full_text = (
            f"Título: {row['titulo']}\n"
            f"Autor: {row['autor']}\n"
            f"Data: {formatar_data(row['data'])}\n"
            f"Link: {row['link']}\n\n"
            f"{row['conteudo']}"
        )

        # Divide o conteúdo e gera embeddings
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

        novos += 1

    print(f"✅ Embeddings atualizados. {novos} novos artigos adicionados ao Chroma.")

df = load_posts()
popular_chroma(df)


# =====================================
# 🔍 CONSULTA RAG
# =====================================

def getPrompt(caminho="prompt.txt"):
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def consultar_rag(mensagens, top_k=5):
    import streamlit as st

    # ====== 1️⃣ Identifica a última pergunta ======
    ultima_pergunta = ""
    for m in reversed(mensagens):
        if m["role"] == "user":
            ultima_pergunta = m["content"]
            break

    if not ultima_pergunta:
        print("⚠️ Nenhuma pergunta do usuário encontrada.")
        return

    # ====== 2️⃣ Verifica se a pergunta faz referência à última matéria ======
    referencias = ["essa matéria", "esse artigo", "essa reportagem", "essa análise", "esse texto", "ela", "ele", "isso"]
    referencia_detectada = any(ref in ultima_pergunta.lower() for ref in referencias)

    # ====== 3️⃣ Busca semântica (RAG normal) ======
    q_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=ultima_pergunta
    ).data[0].embedding

    resultados = collection.query(
        query_embeddings=[q_emb],
        n_results=top_k * 3
    )

    docs = resultados["documents"][0]
    metas = resultados["metadatas"][0]

    if not metas:
        print("🧠 Nenhum resultado encontrado.")
        return

    artigos_unicos = {}
    links_vistos = set()

    for doc, meta in zip(docs, metas):
        doc_id = str(meta.get("doc_id", "")).strip().lower()
        link = str(meta.get("link", "")).strip().lower()

        if not doc_id or not link:
            continue
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

        if len(artigos_unicos) >= top_k:
            break

    if not artigos_unicos:
        print("🧠 Nenhum artigo relevante encontrado.")
        return

    # ====== 4️⃣ Monta o contexto base ======
    contexto = ""
    for artigo in artigos_unicos.values():
        resumo = artigo['texto'].split("\n")
        resumo_texto = "\n".join(resumo[:6])
        contexto += (
            f"Título: {artigo['titulo']}\n"
            f"Autor: {artigo['autor']}\n"
            f"Data: {artigo['data']}\n"
            f"Link: {artigo['link']}\n\n"
            f"{resumo_texto}\n---\n"
        )

    # ====== 5️⃣ Se o usuário se referiu à matéria anterior, adiciona os metadados salvos ======
    if referencia_detectada and "metadados_ultima_materia" in st.session_state:
        meta = st.session_state.metadados_ultima_materia
        contexto = (
            f"(O usuário está se referindo à última matéria sugerida anteriormente.)\n"
            f"Título: {meta['titulo']}\n"
            f"Autor: {meta['autor']}\n"
            f"Data: {meta['data']}\n"
            f"Link: {meta['link']}\n\n"
            f"{contexto}"
        )

    # ====== 6️⃣ Usa o template do prompt ======
    template_prompt = getPrompt()
    prompt = template_prompt.format(pergunta=ultima_pergunta, contexto=contexto)

    # ====== 7️⃣ Monta o histórico (últimas 5 mensagens) ======
    historico = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens[-5:]
    ]

    # ====== 8️⃣ Monta payload final ======
    mensagens_completas = [
        {"role": "system", "content": "Você é NEO, o assistente do portal NeoFeed. Responda de forma clara e com base nos artigos do contexto."},
        *historico,
        {"role": "user", "content": prompt}
    ]

    # ====== 9️⃣ Envia pro modelo ======
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=mensagens_completas,
        temperature=0.2,
        stream=True,
    )

    # ====== 🔟 Salva metadados da última matéria ======
    # (pega a primeira, que normalmente é a mais relevante)
    primeiro_artigo = list(artigos_unicos.values())[0]
    st.session_state.metadados_ultima_materia = {
        "titulo": primeiro_artigo["titulo"],
        "autor": primeiro_artigo["autor"],
        "data": primeiro_artigo["data"],
        "link": primeiro_artigo["link"]
    }

    return stream

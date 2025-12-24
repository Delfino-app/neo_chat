import sqlite3
import pandas as pd
import os

def save(posts, arquivo_db="artigos.db"):
    conn = sqlite3.connect(arquivo_db)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE artigos ADD COLUMN categoria TEXT")
    except sqlite3.OperationalError:
        # coluna já existe
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artigos (
            doc_id TEXT PRIMARY KEY,
            titulo TEXT,
            conteudo TEXT,
            categoria TEXT,
            autor TEXT,
            data TEXT,
            link TEXT
        )
    """)

    for post in posts:
        cursor.execute("""
            INSERT INTO artigos (doc_id, titulo, conteudo, categoria, autor, data, link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                titulo=excluded.titulo,
                conteudo=excluded.conteudo,
                categoria=excluded.categoria,
                autor=excluded.autor,
                data=excluded.data,
                link=excluded.link
        """, (
            post["doc_id"],
            post["titulo"],
            post["conteudo"],
            post["categoria"],
            post["autor"],
            post["data"],
            post["link"],
        ))

    conn.commit()
    conn.close()
    print(f"✅ Banco atualizado com {len(posts)} matérias (novos ou atualizados).")


def load_posts(arquivo_db="artigos.db"):
    conn = sqlite3.connect(arquivo_db)
    df = pd.read_sql("SELECT * FROM artigos", conn)
    conn.close()
    return df


def load_posts_simplify(arquivo_db="artigos.db", limite=10):

    if not os.path.exists(arquivo_db):
        print(f"Banco {arquivo_db} não encontrado.")
        return

    conn = sqlite3.connect(arquivo_db)
    query = f"SELECT doc_id, titulo, categoria, data, link, conteudo, autor FROM artigos ORDER BY data DESC LIMIT {limite}"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("Nenhum registro encontrado na tabela 'artigos'.")
        return

    print(f"📋 Listando {len(df)} matérias mais recentes:\n")
    for _, row in df.iterrows():
        print(f"📰 {row['titulo']}")
        print(f"📰 {row['categoria']}")
        print(f"📰 {row['autor']}")
        print(f"📅 {row['data']} | 🔗 {row['link']}")
        print(f"🆔 {row['doc_id']}\n---")

    return df  # opcional, pra usar em outras funções


def clean_db(arquivo_db="artigos.db"):
   
    if not os.path.exists(arquivo_db):
        print(f"Banco {arquivo_db} não encontrado.")
        return

    conn = sqlite3.connect(arquivo_db)
    cursor = conn.cursor()

    # Garante que a tabela exista
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artigos (
            doc_id TEXT PRIMARY KEY,
            titulo TEXT,
            conteudo TEXT,
            categoria TEXT,
            autor TEXT,
            data TEXT,
            link TEXT
        )
    """)

    cursor.execute("DELETE FROM artigos")
    conn.commit()
    conn.close()

    print(f"Todos os dados foram removidos da tabela 'artigos' em {arquivo_db}.")

if __name__ == "__main__":
    # Teste simples do streaming
    clean_db()
    print()

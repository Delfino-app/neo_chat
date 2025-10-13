import requests
from datetime import datetime
from storage import save

def atualizar_db_com_wp(url="https://neofeed.com.br/wp-json/wp/v2/posts",page="1"):

    print(f"🔍 Buscando posts em: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://neofeed.com.br/",
    }

    resp = requests.get(url, params={"per_page": 10, "page":page,"_fields": "id,date,title,content,link,yoast_head_json"}, headers=headers)
    if resp.status_code == 403:
        print("🚫 Erro 403: acesso bloqueado. Tente com VPN ou verifique se o site exige autenticação.")
        return
    resp.raise_for_status()

    posts = resp.json()

    if not posts:
        print("⚠️ Nenhum post encontrado na API.")
        return

    # Garante lista
    if isinstance(posts, dict):
        posts = [posts]

    novos = []
    for p in posts:
        post_id = p.get("id")
        if not post_id:
            continue

        data_publicacao = p.get("date", "")[:10]
        try:
            data_publicacao = datetime.strptime(data_publicacao, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            pass

        novos.append({
            "doc_id": f"artigo-{post_id}",
            "titulo": p.get("title", {}).get("rendered", "").strip(),
            "conteudo": (
                p.get("content", {}).get("rendered", "")
                .replace("<p>", "")
                .replace("</p>", "")
                .replace("<br>", "\n")
                .replace("<br/>", "\n")
                .replace("&nbsp;", " ")
                .strip()
            ),
            "autor":p.get("yoast_head_json", {}).get("author", ""),
            "data": data_publicacao,
            "link": p.get("link", "").strip(),
        })

        if not novos:
            print("⚠️ Nenhum post válido encontrado.")
            return
        save(novos)
from core.db.storage import save
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import html
import re
from urllib.parse import urlparse

def limpar_caracteres_agressivo(texto):
    
    if not texto:
        return ""
    
    try:
       
        texto = str(texto)
        texto = html.unescape(texto)
        
        # Remove caracteres de controle (0x00-0x1F, 0x7F-0x9F) exceto tab, newline, return
        texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', texto)
        
        # Remove zero-width spaces e outros caracteres invisíveis
        texto = texto.replace('\u200b', '').replace('\ufeff', '')
        
        # Corrige caracteres acentuados mal formatados
        correcoes = {
            'á': 'á', 'é': 'é', 'í': 'í', 'ó': 'ó', 'ú': 'ú',
            'à': 'à', 'è': 'è', 'ì': 'ì', 'ò': 'ò', 'ù': 'ù', 
            'ã': 'ã', 'ẽ': 'ẽ', 'ĩ': 'ĩ', 'õ': 'õ', 'ũ': 'ũ',
            'â': 'â', 'ê': 'ê', 'î': 'î', 'ô': 'ô', 'û': 'û',
            'ç': 'ç', 'ñ': 'ñ',
            '\\c': '', '\\c​': '', '\\u0301': '', '\\u0300': ''
        }
        
        for erro, correcao in correcoes.items():
            texto = texto.replace(erro, correcao)
    
        texto = re.sub(r'\s+', ' ', texto)
        texto = texto.encode('utf-8', 'ignore').decode('utf-8')
        
    except Exception as e:
        print(f"⚠️ Erro na limpeza: {e}")
        texto = re.sub(r'[^\x20-\x7E\u00C0-\u00FF]', '', texto)
    
    return texto.strip()


def atualizar_db_com_wp(url="https://neofeed.com.br/wp-json/wp/v2/posts", page="1"):
    print(f"📡 Buscando posts em: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Charset": "utf-8",
        "Referer": "https://neofeed.com.br/",
    }

    try:
        resp = requests.get(
            url,
            params={
                "per_page": 10,
                "page": page,
                "_fields": "id,date,title,content,link,yoast_head_json"
            },
            headers=headers,
            timeout=30
        )
        
        resp.encoding = 'utf-8'
        
        if resp.status_code == 403:
            print("Erro 403: acesso bloqueado.")
            return
        resp.raise_for_status()
        
    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return

    posts = resp.json()
    if not posts:
        print("Nenhum post encontrado na API.")
        return

    novos = []
    for p in posts:
        post_id = p.get("id")
        if not post_id:
            continue

        link = p.get("link", "").strip()
        if any(proibido in link for proibido in ['/brand-stories/', '/apresentado-por-']):
            continue

        
        data_publicacao = p.get("date", "")[:10]
        conteudo_html = p.get("content", {}).get("rendered", "")

        print(data_publicacao)

        soup = BeautifulSoup(conteudo_html, "html.parser")
        
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
            
        conteudo_bruto = soup.get_text(separator=" ", strip=True)
        conteudo_limpo = limpar_caracteres_agressivo(conteudo_bruto)
        
        titulo_html = p.get("title", {}).get("rendered", "")
        titulo_limpo = limpar_caracteres_agressivo(titulo_html)

        parsed = urlparse(link)
        path_parts = parsed.path.strip("/").split("/")
        post_category = path_parts[0]

        categoria = post_category

        autor = p.get("yoast_head_json", {}).get("author", "")
        autor_limpo = limpar_caracteres_agressivo(autor)

        novos.append({
            "doc_id": f"artigo-{post_id}",
            "titulo": titulo_limpo,
            "conteudo": conteudo_limpo,
            "categoria": categoria,
            "autor": autor_limpo,
            "data": data_publicacao,
            "link": link,
        })

    if not novos:
        print("Nenhum post válido encontrado após limpeza.")
        return
    try:
        save(novos)
        print(f"{len(novos)} posts SALVOS COM SUCESSO (limpos e validados)!")
            
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")

if __name__ == "__main__":
    atualizar_db_com_wp()
import streamlit as st
from views import listPosts, indexarPosts


st.set_page_config(
    page_title="NEO - Assistente do NeoFeed",
    layout="wide",  # usa toda a largura da tela
    initial_sidebar_state="expanded"  # sidebar já expandida
)

# Funções ou arquivos
def home():
    st.title("🏠 Página Inicial")
    st.write("Bem-vindo ao NEO - Assistente do NeoFeed")

def noticias():
    st.title("📰 Matérias")
    listPosts.init()

def indexar():
    st.title("🔄 Indexar")
    indexarPosts.init()

def historico():
    st.title("📚 Histórico")
    st.write("Histórico de indexações")

# Criação das páginas com título, ícone e ordem
pages = [
    st.Page(home, title="Início", icon="🏠", default=True),
    st.Page(noticias, title="Notícias", icon="📰"),
    st.Page(indexar, title="Indexar", icon="🔄"),
    st.Page(historico, title="Histórico", icon="📚"),
]

# Navigation
selected_page = st.navigation(pages)
selected_page.run()

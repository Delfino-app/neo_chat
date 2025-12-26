import streamlit as st
import time
from getRequests import fetch_posts

def init():

    st.set_page_config(page_title="NEO | Indexar Matérias", layout="wide")

    st.divider()

   # Inputs principais
    col1, col2, col3 = st.columns([4, 2, 2])

    with col1:
        api_url = st.text_input(
            "URL da API",
            value="https://neofeed.com.br/wp-json/wp/v2/posts"
        )

    with col2:
        pagina_inicial = st.number_input(
            "Página inicial da API",
            min_value=1,
            value=1
        )

    with col3:
        total_paginas = st.number_input(
            "Quantas páginas indexar",
            min_value=1,
            value=1
        )

    # Botão de iniciar indexação
    if st.button("🚀 Iniciar Indexação", type="primary",use_container_width=True):
        st.divider()

        log_box = st.empty()
        logs_display = ""
        progress = st.progress(0)

        for i in range(total_paginas):
            pagina_atual = pagina_inicial + i
            result = fetch_posts(url=api_url, page=pagina_atual)

            for log in result.get("logs", []):
                logs_display += log + "\n"

            log_box.text(logs_display)

            progress.progress((i + 1) / total_paginas)
            time.sleep(0.3)

        st.success("🎉 Indexação finalizada")

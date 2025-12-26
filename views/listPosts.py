from core.db.loadDB import load_documents_from_sql
import streamlit as st
import math

def init() :

    st.set_page_config(page_title="NEO | Matérias Indexadas", layout="wide")

    st.divider()

    @st.cache_data
    def get_documents():
        docs = load_documents_from_sql()
        return docs

    docs = get_documents()

    itens_por_pagina = 5
    total_itens = len(docs)
    total_paginas = math.ceil(total_itens / itens_por_pagina)


    if "pagina" not in st.session_state:
        st.session_state.pagina = 1

    pagina_atual = st.session_state.pagina


    start = (pagina_atual - 1) * itens_por_pagina
    end = start + itens_por_pagina


    for doc in docs[start:end]:
        st.markdown(f"### {doc.metadata['titulo']}")
        st.caption(
            f"Categoria: {doc.metadata['categoria']} | "
            f"Autor: {doc.metadata['autor']} | "
            f"Data: {doc.metadata['data']}"
        )
        st.divider()


    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("Anterior", type="primary",disabled=pagina_atual <= 1):
            st.session_state.pagina -= 1
            st.rerun()

    with col3:
        if st.button("Próxima", type="primary", disabled=pagina_atual >= total_paginas):
            st.session_state.pagina += 1
            st.rerun()

    with col2:
        st.markdown(
            f"<p style='text-align:center'>Página {pagina_atual} de {total_paginas}</p>",
            unsafe_allow_html=True
        )
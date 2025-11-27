from datetime import datetime, timedelta
import re
from typing import Dict, Optional, Any

class DetectorTemporalNoticias:
    def __init__(self):
        self.hoje = datetime.now()
        
        # Palavras-chave que indicam "recência"
        self.indicadores_recencia = {
            'últimas notícias', 'novidades', 'notícias recentes', 
            'atualidades', 'ultimas', 'recentes', 'agora',
            'última hora', 'breaking news', 'novo'
        }
        
        # Intervalos temporais comuns em notícias
        self.intervalos_noticias = {
            'últimas 24 horas': timedelta(days=1),
            'últimas 48 horas': timedelta(days=2),
            'última semana': timedelta(weeks=1),
            'semana passada': timedelta(weeks=1),
            'últimos 7 dias': timedelta(days=7),
            'últimos 15 dias': timedelta(days=15),
            'último mês': timedelta(days=30),
            'este mês': self._inicio_do_mes(),
            'mês passado': self._mes_passado(),
        }

    def detectar_filtro_temporal(self, consulta: str) -> Dict[str, Any]:
        """
        Detecta filtros temporais em consultas de notícias
        Retorna filtros para MongoDB/Elasticsearch
        """
        consulta = consulta.lower().strip()
        
        # 1. PRIORIDADE: Indicadores de recência (mais comum em notícias)
        if any(indicador in consulta for indicador in self.indicadores_recencia):
            return self._filtro_ultimas_noticias(consulta)
        
        # 2. Datas relativas específicas
        filtro_relativo = self._detectar_datas_relativas(consulta)
        if filtro_relativo:
            return filtro_relativo
        
        # 3. Intervalos temporais
        filtro_intervalo = self._detectar_intervalos(consulta)
        if filtro_intervalo:
            return filtro_intervalo
        
        # 4. Datas específicas (DD/MM, DD/MM/AAAA, etc)
        filtro_data = self._detectar_datas_especificas(consulta)
        if filtro_data:
            return filtro_data
        
        # 5. Fallback: se não detectou nada, assume notícias recentes
        return self._filtro_default()
    
    def _filtro_ultimas_noticias(self, consulta: str) -> Dict[str, Any]:
        """Lógica para 'últimas notícias', 'novidades', etc"""
        if "hoje" in consulta or "agora" in consulta or "última hora" in consulta:
            return {"$gte": self.hoje.strftime("%Y-%m-%d")}
        elif "ontem" in consulta:
            ontem = self.hoje - timedelta(days=1)
            return {"data": ontem.strftime("%Y-%m-%d")}
        else:
            # CORREÇÃO: Para "novidades" genéricas, retorna HOJE, não últimos 3 dias
            return {"$gte": self.hoje.strftime("%Y-%m-%d")}  # ← Mudei esta linha

    def _detectar_datas_relativas(self, consulta: str) -> Optional[Dict[str, Any]]:
        """Detecta 'hoje', 'ontem', 'amanhã'"""
        if "hoje" in consulta:
            return {"data": self.hoje.strftime("%Y-%m-%d")}
        elif "ontem" in consulta:
            ontem = self.hoje - timedelta(days=1)
            return {"data": ontem.strftime("%Y-%m-%d")}
        elif "amanhã" in consulta:
            amanha = self.hoje + timedelta(days=1)
            return {"data": amanha.strftime("%Y-%m-%d")}
        return None

    def _detectar_intervalos(self, consulta: str) -> Optional[Dict[str, Any]]:
        """Detecta intervalos como 'última semana', 'mês passado'"""
        for intervalo, delta in self.intervalos_noticias.items():
            if intervalo in consulta:
                if callable(delta):
                    data_inicio = delta()
                else:
                    data_inicio = self.hoje - delta
                return {"$gte": data_inicio.strftime("%Y-%m-%d")}
        return None

    def _detectar_datas_especificas(self, consulta: str) -> Optional[Dict[str, Any]]:
        """Detecta datas no formato DD/MM, DD/MM/AAAA, etc"""
        
        # 1. Formato DD/MM ou DD/MM/AAAA
        match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", consulta)
        if match:
            dia, mes, ano = match.groups()
            ano = int(ano) if ano else self.hoje.year
            try:
                data = datetime(ano, int(mes), int(dia))
                return {"data": data.strftime("%Y-%m-%d")}
            except:
                pass
        
        # 2. NOVO: Formato "dia 27" ou "dia 27 de novembro"
        match = re.search(r"dia\s+(\d{1,2})(?:\s+de\s+(\w+))?(?:\s+de\s+(\d{4}))?", consulta)
        if match:
            dia, mes_str, ano = match.groups()
            ano = int(ano) if ano else self.hoje.year
            
            # Se não especificou mês, assume mês atual
            if not mes_str:
                mes = self.hoje.month
            else:
                meses = {
                    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
                }
                mes = meses.get(mes_str.lower())
            
            if mes:
                try:
                    data = datetime(ano, mes, int(dia))
                    return {"data": data.strftime("%Y-%m-%d")}
                except:
                    pass
        
        # 3. Formato "23 de novembro" ou "23 de novembro de 2024"
        match = re.search(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", consulta)
        if match:
            dia, mes_str, ano = match.groups()
            meses = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            mes = meses.get(mes_str.lower())
            ano = int(ano) if ano else self.hoje.year
            if mes:
                try:
                    data = datetime(ano, mes, int(dia))
                    return {"data": data.strftime("%Y-%m-%d")}
                except:
                    pass
        
        return None

    def _filtro_default(self) -> Dict[str, Any]:
        """Fallback para quando não detecta filtro temporal"""
        # Retorna notícias da última semana como default
        return None

    def _inicio_do_mes(self):
        return datetime(self.hoje.year, self.hoje.month, 1)

    def _mes_passado(self):
        if self.hoje.month == 1:
            return datetime(self.hoje.year - 1, 12, 1)
        else:
            return datetime(self.hoje.year, self.hoje.month - 1, 1)
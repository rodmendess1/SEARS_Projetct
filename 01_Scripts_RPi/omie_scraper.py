import requests
import pandas as pd
import io
from datetime import datetime, timedelta

def extrair_precos_portugal():
    # 1. Tenta primeiro os preços de AMANHÃ (D+1) para o planeamento de arbitragem
    data_alvo = datetime.now() + timedelta(days=1)
    data_str = data_alvo.strftime("%Y%m%d")
    url = f"https://www.omie.es/pt/file-download?parents%5B0%5D=marginalpdbcpt&filename=marginalpdbcpt_{data_str}.1"
    
    print(f"A tentar descarregar dados de: {data_alvo.strftime('%d/%m/%Y')}...")

    try:
        response = requests.get(url, timeout=10)
        
        # Lógica de FALLBACK: Se der 404, tenta os preços de HOJE
        if response.status_code == 404:
            print(f"Aviso: Dados de amanhã ainda não publicados.")
            data_alvo = datetime.now() 
            data_str = data_alvo.strftime("%Y%m%d")
            url = f"https://www.omie.es/pt/file-download?parents%5B0%5D=marginalpdbcpt&filename=marginalpdbcpt_{data_str}.1"
            print(f"A extrair dados de HOJE ({data_alvo.strftime('%d/%m/%Y')}) como alternativa...")
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        
        # Módulo de Parsing: Transforma o texto em tabela
        df = pd.read_csv(io.StringIO(response.text), sep=';', skiprows=1, header=None, engine='python')
        
        # Extrai as 24 horas (linhas 0 a 23) da 5ª coluna (índice 4)
        precos_raw = df.iloc[0:24, 4].values
        return [float(p) for p in precos_raw]

    except Exception as e:
        print(f"Erro crítico na extração: {e}")
        return None

# --- Bloco de Teste ---
precos = extrair_precos_portugal()

if precos:
    print("\n=== Preços Carregados no SEARS ===")
    for h, p in enumerate(precos):
        print(f"{h:02d}h: {p:.2f}€/MWh")
else:
    print("Falha total: Sem ligação à OMIE ou dados inexistentes.")
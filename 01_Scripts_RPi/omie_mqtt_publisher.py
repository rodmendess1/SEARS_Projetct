import requests
import pandas as pd
import io
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
BROKER = "localhost"
PORTA = 1883
TOPICO = "sears/precos"

def extrair_e_publicar_omie():
    # 1. Tenta primeiro AMANHÃ (D+1)
    data_alvo = datetime.now() + timedelta(days=1)
    data_str = data_alvo.strftime("%Y%m%d")
    url = f"https://www.omie.es/pt/file-download?parents%5B0%5D=marginalpdbcpt&filename=marginalpdbcpt_{data_str}.1"
    
    print(f"\n[OMIE] A tentar descarregar dados de: {data_alvo.strftime('%d/%m/%Y')}...")

    try:
        response = requests.get(url, timeout=10)
        
        # Lógica de FALLBACK: Se amanhã não estiver pronto, tenta HOJE
        if response.status_code == 404:
            print(f"[AVISO] Dados de amanhã ainda não publicados.")
            data_alvo = datetime.now() 
            data_str = data_alvo.strftime("%Y%m%d")
            url = f"https://www.omie.es/pt/file-download?parents%5B0%5D=marginalpdbcpt&filename=marginalpdbcpt_{data_str}.1"
            print(f"[OMIE] A extrair dados de HOJE ({data_alvo.strftime('%d/%m/%Y')}) como alternativa...")
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        
        # 2. Processamento com Pandas
        df = pd.read_csv(io.StringIO(response.text), sep=';', skiprows=1, header=None, engine='python')
        precos_raw = df.iloc[0:24, 4].values
        
        # Converter para €/kWh (Dividir por 1000)
        precos_dict = {str(h): round(float(p)/1000.0, 5) for h, p in enumerate(precos_raw)}
        
        # 3. MENSAGEM JSON ESTRUTURADA (Metadata + Payload)
        mensagem_final = {
            "metadata": {
                "device_id": "sears_gateway_01",
                "timestamp": datetime.now().isoformat(),
                "sensor_type": "electricity_market_api"
            },
            "payload": {
                "data_referencia": data_alvo.strftime("%Y-%m-%d"),
                "unidade": "EUR/kWh",
                "precos": precos_dict
            }
        }
        
        # 4. Publicar via MQTT
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(BROKER, PORTA, 60)
        client.publish(TOPICO, json.dumps(mensagem_final), retain=True)
        client.disconnect()
        
        print(f"[SUCESSO] Preços enviados para o tópico '{TOPICO}'!")

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha na integração: {e}")

if __name__ == "__main__":
    extrair_e_publicar_omie()
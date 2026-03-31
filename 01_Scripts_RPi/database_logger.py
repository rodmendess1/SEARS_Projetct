import paho.mqtt.client as mqtt
import sqlite3
import json
from datetime import datetime

# --- CONFIGURAÇÃO ---
DB_NAME = "sears_data.db"
BROKER = "localhost"
TOPICO_BASE = "sears/#"

# --- FUNÇÕES DE BASE DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Criamos uma tabela para telemetria (Consumo/Tensão/Corrente) e outra para Preços
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            device_id TEXT,
            tipo_sensor TEXT,
            potencia_w REAL,
            tensao_v REAL
            corrente_a REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            data_referencia TEXT,
            hora INTEGER,
            preco_kwh REAL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[DB] Base de dados '{DB_NAME}' pronta.")

def guardar_telemetria(device_id, sensor, potencia, tensao):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO telemetria (timestamp, device_id, tipo_sensor, potencia_w, tensao_v, corrente_a)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), device_id, sensor, potencia, tensao))
    conn.commit()
    conn.close()

def guardar_preco(data_ref, hora, preco):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historico_precos (timestamp, data_referencia, hora, preco_kwh)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().isoformat(), data_ref, hora, preco))
    conn.commit()
    conn.close()

# --- CALLBACK MQTT ---
def ao_receber_mensagem(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        
        # 1. Se for mensagem do SIMULADOR (Consumo/Barramento)
        if "potencia_w" in payload.get("payload", {}):
            load = payload["payload"]
            meta = payload["metadata"]
            guardar_telemetria(meta["device_id"], meta["sensor_type"], load["potencia_w"], load["tensao_v"], load["corrente_a"])
            print(f"[DB] Gravado Consumo: {load['potencia_w']}W")

        # 2. Se for mensagem da OMIE (Preços)
        elif "precos" in payload.get("payload", {}):
            load = payload["payload"]
            data_ref = load["data_referencia"]
            for hora, valor in load["precos"].items():
                guardar_preco(data_ref, int(hora), valor)
            print(f"[DB] Gravadas 24h de preços para {data_ref}")

    except Exception as e:
        print(f"[ERRO DB] Falha ao processar mensagem: {e}")

# --- EXECUÇÃO ---
iniciar_db()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Database_Logger")
client.on_message = ao_receber_mensagem
client.connect(BROKER, 1883)
client.subscribe(TOPICO_BASE)

print("A aguardar dados para gravar... (Ctrl+C para sair)")
client.loop_forever()

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
    
    # 1. TABELA PARA O QUADRO (AC - Trabalho do teu colega)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_ac (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            device_id TEXT,
            v_rms REAL,
            i_rms REAL,
            p_ativa REAL
        )
    ''')
    
    # 2. TABELA PARA O BARRAMENTO (DC - A tua tarefa desta semana)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_dc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            device_id TEXT,
            v_bus REAL,
            i_solar REAL,
            i_bat REAL,
            i_rede_dc REAL,
            p_total REAL
        )
    ''')

    # 3. TABELA DE PREÇOS (OMIE)
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
    print(f"[DB] Base de dados '{DB_NAME}' pronta com tabelas AC e DC.")

# --- FUNÇÕES DE INSERÇÃO ---

def guardar_ac(meta, load):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO telemetria_ac (timestamp, device_id, v_rms, i_rms, p_ativa)
        VALUES (?, ?, ?, ?, ?)
    ''', (meta["timestamp"], meta["device_id"], load["v_rms"], load["i_rms"], load["p_ativa"]))
    conn.commit()
    conn.close()

def guardar_dc(meta, load):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO telemetria_dc (timestamp, device_id, v_bus, i_solar, i_bat, i_rede_dc, p_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (meta["timestamp"], meta["device_id"], load["v_bus"], load["i_solar"], load["i_bat"], load["i_rede_dc"], load["p_total"]))
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
        dados = json.loads(message.payload.decode("utf-8"))
        meta = dados.get("metadata", {})
        load = dados.get("payload", {})

        # IDENTIFICAÇÃO PELO TIPO DE SENSOR
        tipo = meta.get("sensor_type")

        if tipo == "ac_monitor":
            guardar_ac(meta, load)
            # Mostra V, I e P para o lado AC
            print(f"[DB] ✅ Gravado AC: {load['v_rms']}V | {load['i_rms']}A | {load['p_ativa']}W")

        elif tipo == "dc_monitor":
            guardar_dc(meta, load)
            # Mostra V_bus e as Correntes Solar/Bateria conforme a tarefa 
            print(f"[DB] ✅ Gravado DC: {load['v_bus']}V | I_sol: {load['i_solar']}A | I_bat: {load['i_bat']}A | P: {load['p_total']}W")

        elif "precos" in load:
            data_ref = load["data_referencia"]
            for hora, valor in load["precos"].items():
                guardar_preco(data_ref, int(hora), valor)
            print(f"[DB] Gravados Preços OMIE para {data_ref}")

    except Exception as e:
        print(f"[ERRO DB] Falha: {e}")

# --- EXECUÇÃO ---
iniciar_db()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Database_Logger_Final")
client.on_message = ao_receber_mensagem
client.connect(BROKER, 1883)
client.subscribe(TOPICO_BASE)

print("A aguardar dados AC e DC para gravar... (Ctrl+C para sair)")
client.loop_forever()

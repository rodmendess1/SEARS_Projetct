import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

# "pip install paho-mqtt" ou "python -m pip install paho-mqtt" - caso nao conheça a primeira biblioteca

# =================================================================
# NOTA: ESTE SCRIPT DEVE SER EXECUTADO DENTRO DO RASPBERRY PI
# Ele simula os dados que viriam dos ESP32 via rede local (localhost).
# =================================================================

# --- CONFIGURAÇÕES ---
BROKER = "localhost" 
PORTA = 1883
# Usamos o tópico 'barramento' para ser apanhado pelo teu script subscriber
TOPICO = "sears/esp32/barramento" 
DEVICE_ID = "esp32_simulado_02"

# Inicialização do Cliente MQTT usando a versão 2 da API (conforme o teu código)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_Dados_Sinteticos")

try:
    print(f"--- Iniciando Simulação de Dados para o Barramento DC ---")
    print(f"A ligar ao Broker local...")
    client.connect(BROKER, PORTA, 60)
except Exception as e:
    print(f"[ERRO] Não foi possível ligar ao Broker: {e}")
    exit()

print("Simulador Ativo! Enviando dados a cada 5 segundos... (Ctrl+C para parar)")

try:
    while True:
        # 1. GERAR VALORES REALISTAS
        # Tensão em torno de 230V com pequenas oscilações
        tensao = round(random.uniform(227.0, 233.0), 2)
        
        # Corrente simulando variação entre standby (0.2A) e carga alta (10.0A)
        corrente = round(random.uniform(0.2, 10.0), 2)
        
        # Potência P = V * I (simplificado)
        potencia = round(tensao * corrente, 2)

        # 2. ESTRUTURA JSON (Seguindo o padrão do grupo: Metadata + Payload)
        mensagem_final = {
            "metadata": {
                "device_id": DEVICE_ID,
                "timestamp": datetime.now().isoformat(),
                "sensor_type": "pzem_004t_simulated"
            },
            "payload": {
                "tensao_v": tensao,
                "corrente_a": corrente,
                "potencia_w": potencia,
                "unidade_v": "V",
                "unidade_a": "A",
                "unidade_w": "W"
            }
        }

        # 3. PUBLICAR NO MQTT
        payload_json = json.dumps(mensagem_final)
        client.publish(TOPICO, payload_json)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Enviado para {TOPICO}:")
        print(f"   V: {tensao}V | I: {corrente}A | P: {potencia}W")
        
        # Intervalo de 5 segundos para não sobrecarregar o log enquanto testas
        time.sleep(5)

except KeyboardInterrupt:
    print("\n[INFO] Simulação encerrada pelo utilizador.")
    client.disconnect()
import time
import random
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# --- CONFIGURAÇÃO MQTT (Para o Raspberry Pi) ---
BROKER = "localhost"
TOPICO_TELEMETRIA = "sears/esp32/temperatura"

# ==========================================
# 1. A BATERIA VIRTUAL (Física Simulada)
# ==========================================
class SimuladorBateria:
    def __init__(self):
        self.temperatura = 28.0 

    def atualizar_temperatura(self, ventoinha_ligada):
        aquecimento = random.uniform(0.2, 0.8) 
        arrefecimento = random.uniform(0.8, 1.5) if ventoinha_ligada else 0.0
        
        self.temperatura += (aquecimento - arrefecimento)
        self.temperatura = max(20.0, min(self.temperatura, 50.0))
        return self.temperatura

# ==========================================
# 2. CICLO DE SIMULAÇÃO (Com MQTT)
# ==========================================
def iniciar_simulacao():
    # Como o RPi costuma ter as bibliotecas atualizadas, voltamos a usar o formato correto
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_Termico_RPi")
    
    try:
        client.connect(BROKER, 1883)
    except ConnectionRefusedError:
        print("❌ ERRO: Não foi possível ligar ao Mosquitto no localhost.")
        print("Garante que o serviço Mosquitto está a correr no Raspberry Pi!")
        return

    bateria = SimuladorBateria()
    ventoinha_ligada = False
    
    print("🌡️ Simulação de Gestão Térmica (ON/OFF Histerese) Ativa no RPi")
    print(f"📡 A enviar telemetria para o tópico: {TOPICO_TELEMETRIA}")
    print("-" * 50)
    
    try:
        while True:
            # 1. Atualizar física virtual
            temp_atual = bateria.atualizar_temperatura(ventoinha_ligada)
            
            # 2. Lógica de Controlo (Histerese)
            if temp_atual > 35.0 and not ventoinha_ligada:
                ventoinha_ligada = True
                print("⚠️ [ALERTA] Bateria aos 35°C! Ventoinha LIGADA 💨")
                
            elif temp_atual < 30.0 and ventoinha_ligada:
                ventoinha_ligada = False
                print("✅ [OK] Bateria arrefecida aos 30°C. Ventoinha DESLIGADA 🛑")
            
            # 3. Mostrar no terminal
            status_v = "ON  💨" if ventoinha_ligada else "OFF 🛑"
            print(f"[STATUS] Temp: {temp_atual:05.2f} °C | Ventoinha: {status_v}")
            
            # 4. Empacotar e Enviar via MQTT
            msg = {
                "metadata": {
                    "device_id": "esp32_termico",
                    "timestamp": datetime.now().isoformat(),
                    "sensor_type": "bms_temperatura"
                },
                "payload": {
                    "temperatura_c": round(temp_atual, 2),
                    "ventoinha_ativa": ventoinha_ligada,
                    "limite_superior": 35.0,
                    "limite_inferior": 30.0
                }
            }
            client.publish(TOPICO_TELEMETRIA, json.dumps(msg))
            
            time.sleep(1) # Correr a 1Hz (1 vez por segundo) para não encher os logs do RPi

    except KeyboardInterrupt:
        print("\n⏹️ Simulação Térmica terminada.")
        client.disconnect()

if __name__ == "__main__":
    iniciar_simulacao()
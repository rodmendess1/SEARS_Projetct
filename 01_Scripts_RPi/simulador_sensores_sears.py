import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

BROKER = "localhost"
PORTA = 1883

# --- VARIÁVEIS DE ESTADO (Para as Tarefas da Sprint) ---
v_bat = 12.6  # Tensão inicial da bateria de 12V
rede_ativa = True # Estado da rede para o Anti-Islanding

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_Global_SEARS")
client.connect(BROKER, PORTA, 60)

print("--- SEARS: Simulador Completo (AC + DC) com Proteções Ativo ---")

try:
    while True:
        # --- TAREFA 1: Sincronização de Segurança (Anti-islanding) ---
        # Há 10% de probabilidade de a rede elétrica "cair" para testarmos a segurança
        if random.random() < 0.10:
            rede_ativa = False
        else:
            rede_ativa = True

        # --- 1. SIMULAÇÃO LADO AC (QUADRO GERAL) ---
        # Se a rede falhar, a tensão AC vai a zero!
        v_ac = round(random.uniform(228.0, 232.0), 1) if rede_ativa else 0.0
        i_ac = round(random.uniform(0.5, 12.0), 2) if rede_ativa else 0.0
        p_ac = round(v_ac * i_ac, 1)

        msg_ac = {
            "metadata": {
                "device_id": "esp32_ac_quadro",
                "timestamp": datetime.now().isoformat(),
                "sensor_type": "ac_monitor"
            },
            "payload": {
                "v_rms": v_ac,
                "i_rms": i_ac,
                "p_ativa": p_ac,
                "unidade": "AC",
                "rede_status": "ONLINE" if rede_ativa else "FALHA DE REDE (ISOLADO)"
            }
        }
        client.publish("sears/esp32/quadro", json.dumps(msg_ac))

        # --- TAREFA 2: Validação de Tensões de Corte (Proteção da Bateria) ---
        # --- 2. SIMULAÇÃO LADO DC (BARRAMENTO CENTRAL) ---
        v_bus = round(random.uniform(23.5, 24.5), 1) # Alterado para 24V conforme o esquema do professor
        i_solar = round(random.uniform(0.0, 10.0), 2)
        i_bat = round(random.uniform(-5.0, 5.0), 2) # Negativo = Carga, Positivo = Descarga
        i_rede_dc = round(random.uniform(0.0, 2.0), 2) if rede_ativa else 0.0

        # Simulação física da bateria: se a corrente for positiva (descarga), a tensão cai.
        v_bat -= (i_bat * 0.05)
        
        status_bateria = "OK"
        # O CORTE DE EMERGÊNCIA NOS 10.5V
        if v_bat <= 10.5:
            v_bat = 10.5
            if i_bat > 0: # Se estiver a tentar descarregar energia da bateria
                i_bat = 0.0 # Corta a corrente imediatamente!
                status_bateria = "CRITICO_10.5V_CORTE"

        p_dc = round(v_bus * (i_solar + i_bat + i_rede_dc), 1)

        msg_dc = {
            "metadata": {
                "device_id": "esp32_dc_bus",
                "timestamp": datetime.now().isoformat(), 
                "sensor_type": "dc_monitor"
            },
            "payload": {
                "v_bus": v_bus, 
                "v_bat": round(v_bat, 2), # Adicionada a tensão da bateria real
                "status_bat": status_bateria,
                "i_solar": i_solar, 
                "i_bat": i_bat, 
                "i_rede_dc": i_rede_dc,
                "p_total": p_dc, 
                "unidade": "DC"
            }
        }
        client.publish("sears/esp32/barramento", json.dumps(msg_dc))

        # --- PRINT DETALHADO PARA DEBUG ---
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Sincronização Global:")
        print(f"   🏠 AC (Quadro): {v_ac}V | Rede: {'ONLINE' if rede_ativa else 'FALHA (Anti-islanding ativado)'}")
        print(f"   🔋 DC (Bus):   {v_bus}V | Tensão Bat: {v_bat:.2f}V ({status_bateria}) | I_Bat: {i_bat}A")
        print("-" * 50)
        time.sleep(5)

except KeyboardInterrupt:
    client.disconnect()
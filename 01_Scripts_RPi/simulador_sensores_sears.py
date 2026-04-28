import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

BROKER = "localhost"
PORTA = 1883

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_Global_SEARS")
client.connect(BROKER, PORTA, 60)

print("--- SEARS: Simulador Completo (AC + DC) Ativo ---")

try:
    while True:
        # --- 1. SIMULAÇÃO LADO AC (QUADRO GERAL) ---
        v_ac = round(random.uniform(228.0, 232.0), 1)
        i_ac = round(random.uniform(0.5, 12.0), 2)
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
                "unidade": "AC"
            }
        }
        client.publish("sears/esp32/quadro", json.dumps(msg_ac))

        # --- 2. SIMULAÇÃO LADO DC (BARRAMENTO CENTRAL) ---
        v_bus = round(random.uniform(47.0, 49.0), 1)
        i_solar = round(random.uniform(0.0, 10.0), 2)
        i_bat = round(random.uniform(-5.0, 5.0), 2) # Negativo = Carga, Positivo = Descarga
        i_rede_dc = round(random.uniform(0.0, 2.0), 2)
        p_dc = round(v_bus * (i_solar + i_bat + i_rede_dc), 1)

        msg_dc = {
            "metadata": {
                "device_id": "esp32_dc_bus",
                "timestamp": datetime.now().isoformat(), 
                "sensor_type": "dc_monitor"
            },
            "payload": {
                "v_bus": v_bus, 
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
        print(f"   🏠 AC (Quadro): {v_ac}V | {i_ac}A | {p_ac}W")
        print(f"   🔋 DC (Bus):   {v_bus}V | Sol: {i_solar}A | Bat: {i_bat}A | P_total: {p_dc}W")
        print("-" * 50)
        time.sleep(5)

except KeyboardInterrupt:
    client.disconnect()

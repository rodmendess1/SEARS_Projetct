import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# --- CONFIGURAÇÃO MQTT (Para o Raspberry Pi) ---
BROKER = "localhost"
TOPICO_STATS = "sears/stats/eficiencia"

# ==========================================
# 1. MOTOR DE CÁLCULO DE ESTATÍSTICAS
# ==========================================
class AnalisadorEficiencia:
    def __init__(self):
        # Energias Acumuladas (em Wh - Watt-hora para precisão interna)
        self.energia_consumida_rede = 0.0      
        self.energia_armazenada_bateria = 0.0  
        self.energia_retirada_bateria = 0.0    
        self.energia_injetada_casa = 0.0       
        
        # Financeiro
        self.lucro_acumulado_eur = 0.0

    def simular_passagem_tempo(self):
        """Simula o sistema a funcionar (Carga e Descarga)"""
        # Exemplo: Carregamento
        self.energia_consumida_rede += 1000.0
        self.energia_armazenada_bateria += 900.0  
        
        # Exemplo: Descarga
        self.energia_retirada_bateria += 800.0
        self.energia_injetada_casa += 720.0       
        
        # Lucro simulado por ciclo
        self.lucro_acumulado_eur += 0.15

    def calcular_metricas(self):
        # Eficiência Carregamento
        ef_carga = (self.energia_armazenada_bateria / self.energia_consumida_rede) * 100 if self.energia_consumida_rede > 0 else 0
        
        # Eficiência Descarga
        ef_descarga = (self.energia_injetada_casa / self.energia_retirada_bateria) * 100 if self.energia_retirada_bateria > 0 else 0
        
        # Eficiência Global
        ef_global = (ef_carga * ef_descarga) / 100
        
        # --- CONVERSÃO PARA kWh ---
        energia_kwh = self.energia_injetada_casa / 1000.0
        
        return {
            "eficiencia_global_perc": round(ef_global, 2),
            "lucro_total_eur": round(self.lucro_acumulado_eur, 2),
            "energia_total_poupada_kwh": round(energia_kwh, 4) # Unidade alterada para kWh
        }

# ==========================================
# 2. EXECUÇÃO NO RASPBERRY PI
# ==========================================
def iniciar_estatisticas():
    # Compatível com as bibliotecas do RPi
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "SEARS_Stats_Engine")
    
    try:
        client.connect(BROKER, 1883)
    except:
        print("❌ Mosquitto não encontrado no localhost.")
        return

    analisador = AnalisadorEficiencia()
    
    print("📊 SEARS: Motor de Estatísticas Ativo (Unidades em kWh)")
    print("-" * 60)

    try:
        while True:
            analisador.simular_passagem_tempo()
            stats = analisador.calcular_metricas()
            
            # Print no terminal com a nova unidade
            print(f"[STATS] Ef. Global: {stats['eficiencia_global_perc']}% | "
                  f"Lucro: {stats['lucro_total_eur']}€ | "
                  f"Energia: {stats['energia_total_poupada_kwh']} kWh")
            
            # Publicar via MQTT
            mensagem = {
                "metadata": {
                    "device_id": "sears_brain_stats",
                    "timestamp": datetime.now().isoformat(),
                    "unidade_energia": "kWh"
                },
                "payload": stats
            }
            client.publish(TOPICO_STATS, json.dumps(mensagem))
            
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n⏹️ Motor de estatísticas desligado.")
        client.disconnect()

if __name__ == "__main__":
    iniciar_estatisticas()
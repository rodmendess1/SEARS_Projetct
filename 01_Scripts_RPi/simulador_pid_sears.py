import time
import random
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# --- CONFIGURAÇÃO MQTT ---
BROKER = "localhost"
TOPICO_TELEMETRIA = "sears/esp32/pid_debug"

# ==========================================
# 1. O CONTROLADOR PID (O "Cérebro" do ESP32)
# ==========================================
class ControladorPID:
    def __init__(self, kp, ki, kd, setpoint):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        
        self.erro_integral = 0
        self.erro_anterior = 0
        self.tempo_anterior = time.time()

    def calcular(self, valor_atual):
        tempo_atual = time.time()
        dt = tempo_atual - self.tempo_anterior
        
        if dt <= 0.0:
            return 0

        # 1. Erro (P)
        erro = self.setpoint - valor_atual
        P = self.kp * erro

        # 2. Integral (I) com Anti-Windup (limita a memória para não saturar)
        self.erro_integral += erro * dt
        self.erro_integral = max(min(self.erro_integral, 50), -50) 
        I = self.ki * self.erro_integral

        # 3. Derivada (D)
        D = self.kd * ((erro - self.erro_anterior) / dt)

        # 4. Saída PID
        saida_pwm = P + I + D

        # Atualizar memórias
        self.erro_anterior = erro
        self.tempo_anterior = tempo_atual

        # Limitar o PWM virtual entre 0% e 100%
        # Assumimos que 50% é o ponto de equilíbrio perfeito (Tensão estável)
        pwm_final = max(min(saida_pwm + 50, 100), 0) 
        
        return pwm_final

# ==========================================
# 2. O BARRAMENTO VIRTUAL (A "Física" Simulada)
# ==========================================
class BarramentoFisicoSimulado:
    def __init__(self):
        self.tensao_atual = 48.0 # Começa nos 48V perfeitos

    def aplicar_fisica(self, pwm_aplicado):
        # 1. Criar uma perturbação aleatória (ex: nuvem passa ou frigorífico liga)
        # Faz a tensão cair ou subir aleatoriamente
        perturbacao = random.uniform(-1.5, 1.5) 
        
        # 2. O efeito do PWM (A correção do conversor)
        # Se o PWM for maior que 50%, a tensão sobe. Se for menor, desce.
        fator_correcao = (pwm_aplicado - 50.0) * 0.1 
        
        # 3. Calcular a nova tensão realística
        self.tensao_atual = self.tensao_atual + perturbacao + fator_correcao
        
        # Introduzir alguma inércia física (um condensador virtual para suavizar)
        self.tensao_atual = max(min(self.tensao_atual, 60.0), 30.0) # Limites físicos absolutos
        return self.tensao_atual

# ==========================================
# 3. CICLO DE SIMULAÇÃO PRINCIPAL
# ==========================================
def iniciar_simulacao():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_PID_SEARS")
    client.connect(BROKER, 1883)
    
    # Criar as nossas "máquinas" virtuais
    pid = ControladorPID(kp=2.5, ki=0.8, kd=0.1, setpoint=48.0)
    barramento = BarramentoFisicoSimulado()
    
    print("🚀 Iniciar Simulação do Controlo PID (Hardware Virtual)")
    print("Alvo: Manter Barramento a 48.0V")
    print("-" * 50)
    
    try:
        while True:
            # 1. Ler Sensor Físico (Simulado)
            v_bus_real = barramento.tensao_atual
            
            # 2. Calcular o PID
            pwm_out = pid.calcular(v_bus_real)
            
            # 3. Aplicar o PWM ao conversor físico (Simulado)
            nova_tensao = barramento.aplicar_fisica(pwm_out)
            
            # 4. Print bonito no terminal
            erro_abs = abs(48.0 - nova_tensao)
            status = "✅ ESTÁVEL" if erro_abs < 0.5 else "⚠️ A CORRIGIR"
            
            print(f"[{status}] V_Bus: {nova_tensao:05.2f}V | Erro: {erro_abs:04.2f}V | PWM Aplicado: {pwm_out:05.1f}%")
            
            # 5. Publicar no MQTT para o vosso ecosistema ver
            msg = {
                "metadata": {
                    "device_id": "esp32_pid_virtual",
                    "timestamp": datetime.now().isoformat(),
                    "sensor_type": "pid_telemetry"
                },
                "payload": {
                    "tensao_barramento": round(nova_tensao, 2),
                    "pwm_percentagem": round(pwm_out, 2),
                    "erro_v": round(erro_abs, 2)
                }
            }
            client.publish(TOPICO_TELEMETRIA, json.dumps(msg))
            
            # Correr a "10 Hz" (10 vezes por segundo)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n⏹️ Simulação PID terminada.")
        client.disconnect()

if __name__ == "__main__":
    iniciar_simulacao()
import paho.mqtt.client as mqtt
import json
import time
import math
import random
from datetime import datetime

# --- CONFIGURAÇÃO ---
BROKER = "localhost"
TOPICO_COMANDO = "sears/comando/estado"
TOPICO_CONFIRMACAO = "sears/atuador/confirmacao"

# Variáveis de Hardware Simulado
potencia_atual = 0.0  # Em Watts
tensao_barramento = 48.0 # Tensão normal 48V

# --- TAREFA: CONFIGURAÇÃO DE CANAIS PWM (IBT_2) ---
# O professor pediu 20-30kHz. Vamos definir 30kHz para não haver ruído audível.
PWM_FREQ_HZ = 30000 
PWM_RESOLUCAO_BITS = 10  # 10 bits significa valores de 0 a 1023
PWM_VALOR_MAX = 1023

# Limites de Segurança (Nunca ir a 0% nem a 100% para não queimar os transístores)
LIMITE_DUTY_MIN_PERCENT = 5   # Mínimo 5%
LIMITE_DUTY_MAX_PERCENT = 95  # Máximo 95%

# CÁLCULO DE RMS (Simulação Matemática)
def calcular_rms_simulado():
    amostras = []
    # Simula a captura de 50 amostras de uma onda senoide de 230V com ruído
    for i in range(50):
        v_instante = 325 * math.sin(2 * math.pi * i / 50) + random.uniform(-5, 5)
        amostras.append(v_instante ** 2)
    
    v_rms = math.sqrt(sum(amostras) / len(amostras))
    return round(v_rms, 2)

def calcular_sinal_pwm(potencia_desejada_w):
    # Regra de 3 simples: 500W = 100% Duty Cycle
    percentagem = (potencia_desejada_w / 500.0) * 100
    
    # Aplicar limites de segurança (Clamp)
    if percentagem < LIMITE_DUTY_MIN_PERCENT and potencia_desejada_w > 0:
        percentagem = LIMITE_DUTY_MIN_PERCENT
    elif percentagem > LIMITE_DUTY_MAX_PERCENT:
        percentagem = LIMITE_DUTY_MAX_PERCENT
    elif potencia_desejada_w == 0:
        percentagem = 0 # Corte total
        
    # Converter percentagem para valor real do ESP32 (0-1023)
    valor_pwm_esp32 = int((percentagem / 100.0) * PWM_VALOR_MAX)
    
    return percentagem, valor_pwm_esp32

# SOFT-START (Arranque Gradual)
def executar_soft_start(objetivo_watts):
    global potencia_atual
    print(f"   [Soft-Start] A iniciar rampa de potência para {objetivo_watts}W...")
    passo = objetivo_watts / 10
    for i in range(1, 11):
        potencia_atual = passo * i
        # Chama a função de PWM que acabaste de criar
        duty_pct, valor_raw = calcular_sinal_pwm(potencia_atual)
        print(f"      >>> Potência: {potencia_atual:.1f}W | Sinal PWM (30kHz): {duty_pct:.1f}% [Raw: {valor_raw}/1023]")
        time.sleep(0.1) # Simula os milissegundos de subida
    print(f"   [Soft-Start] Estabilizado em {potencia_atual:.1f}W.")

# WATCHDOG ELÉTRICO
def verificar_seguranca_eletrica():
    global tensao_barramento, potencia_atual
    # Simula uma leitura aleatória da tensão do barramento
    tensao_barramento = 48.0 + random.uniform(-1, 5) # Às vezes sobe...
    
    LIMITE_CRITICO = 52.0
    if tensao_barramento > LIMITE_CRITICO:
        print(f"\n💥 [WATCHDOG ELÉTRICO] Tensão Crítica: {tensao_barramento:.2f}V!")
        print("   [!] CORTE IMEDIATO DE TODA A POTÊNCIA (PWM -> 0%)")
        potencia_atual = 0
        return False
    return True

def ao_receber_comando(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        estado = payload.get("estado_ativo")
        motivo = payload.get("motivo", "N/A")
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📥 COMANDO RECEBIDO!")
        print(f"   🔹 ESTADO SOLICITADO: {estado}")
        print(f"   🔹 MOTIVO DA IA: {motivo}")
        
        # WATCHDOG (Verificar antes de agir) ---
        if not verificar_seguranca_eletrica():
            # Se o Watchdog disparar, não fazemos mais nada e avisamos o Cérebro
            confirmacao_erro = {"status": "ERRO", "motivo": "SOBRETENSAO_BARRAMENTO"}
            client.publish(TOPICO_CONFIRMACAO, json.dumps(confirmacao_erro), qos=1)
            return

        # Simulação da ação física no barramento DC | SOFT-START (Aplicar rampa conforme o estado) ---
        print("   --- Ações de Hardware ---")
        
        if estado == "MODO_SEGURANCA":
            print("   [🚫] SEGURANÇA: Desligando todos os conversores.")
            potencia_atual = 0 # Corte seco por ser emergência
            
        elif estado == "EMERGENCIA_CARREGAR_100":
            print("   [⚠️] MODO EMERGÊNCIA: Iniciando carga rápida.")
            executar_soft_start(450.0) # Alvo de 450W
            
        elif estado == "ARMAZENAR":
            print("   [!] Ativando Conversor DC/DC (Carga).")
            executar_soft_start(300.0)
            
        elif estado == "USAR_BATERIA":
            print("   [!] Ativando Conversor DC/DC (Descarga).")
            executar_soft_start(400.0)
            
        elif estado == "VENDER_REDE":
            print("   [!] Ativando Micro-Inversor (Venda).")
            executar_soft_start(500.0)
            
        elif estado == "COMPRAR_REDE":
            print("   [!] Ativando Fonte AC/DC (Rede).")
            executar_soft_start(250.0)

        # CÁLCULO DE RMS ---
        v_lida = calcular_rms_simulado()
        print(f"   [Sensor AC] Leitura RMS calculada: {v_lida}V")

        confirmacao = {
            "status": "OK",
            "comando_executado": estado,
            "v_rms_lida": v_lida,
            "potencia_real": round(potencia_atual, 2),
            "tensao_bus": round(tensao_barramento, 2),
            "timestamp": datetime.now().isoformat()
        }

        client.publish(TOPICO_CONFIRMACAO, json.dumps(confirmacao), qos=1)
        print(f"   ✅ [SYNC] Confirmação enviada para {TOPICO_CONFIRMACAO} (QoS 1)")
        
        print("-" * 40)

    except Exception as e:
        print(f"[ERRO ATUADOR] Falha ao processar comando: {e}")

# --- CONFIGURAÇÃO MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Simulador_Atuador_ESP32")
client.on_message = ao_receber_comando

print("--- SEARS: Simulador de Atuador (ESP32 #2) Ativo ---")
print(f"A aguardar ordens em '{TOPICO_COMANDO}'...")

client.connect(BROKER, 1883)
client.subscribe(TOPICO_COMANDO)
client.loop_forever()

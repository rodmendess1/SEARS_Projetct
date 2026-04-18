
import paho.mqtt.client as mqtt
import json
import time
import previsao_solar_coimbra  # O script da API tem de estar na mesma pasta no RPi

# --- CONFIGURAÇÃO RASPBERRY PI ---
# "localhost" assume que o Mosquitto está a correr no próprio Raspberry Pi.

BROKER = "localhost"
TOPICO_ESTADO = "sears/comando/estado"
TOPICO_DADOS = "sears/#"

# --- VARIÁVEIS DE ESTADO ---
status_sistema = {
    "preco_atual": 0.15,
    "soc_bateria": 50.0,
    "producao_solar": 0,
    "consumo_casa": 0,
    "resiliencia_ativa": False,    
    "resiliencia_motivo": ""       
}

# ==========================================
# 1. FUNÇÃO DE RESILIÊNCIA (EMBUTIDA)
# ==========================================
def verificar_modo_resiliencia(previsoes_tempo):
    """Analisa a meteorologia e ativa emergência se houver perigo."""
    if not previsoes_tempo:
        return False, "Sem dados meteorológicos."

    palavras_perigo = ["trovoada", "tempestade", "chuva forte", "chuva extrema", "granizo", "neve", "furacão", "vendaval"]
    
    for hora, dados in previsoes_tempo.items():
        condicao_atual = dados.get("condicao", "").lower() 
        for perigo in palavras_perigo:
            if perigo in condicao_atual:
                return True, f"Risco detetado às {hora}: {condicao_atual.capitalize()}"
                
    return False, "Previsão estável. Sem alertas meteorológicos."

# ==========================================
# 2. LÓGICA DE ESTADOS DE OPERAÇÃO
# ==========================================
def decidir_estado():
    p = status_sistema
    
    # PRIORIDADE 1: Segurança Máxima
    if p["resiliencia_ativa"]:
        return "EMERGENCIA_CARREGAR_100" 
    
    # PRIORIDADE 2: Proteção da Bateria
    if p["soc_bateria"] < 20.0:
        return "COMPRAR_REDE" 

    # PRIORIDADE 3: Arbitragem e Sol
    if p["preco_atual"] > 0.22:
        return "USAR_BATERIA"
    
    if p["producao_solar"] > p["consumo_casa"]:
        if p["soc_bateria"] < 95:
            return "ARMAZENAR"
        else:
            return "VENDER_REDE"
            
    return "COMPRAR_REDE" # Default

# ==========================================
# 3. GESTÃO DE MENSAGENS MQTT
# ==========================================
def ao_receber_mensagem(client, userdata, message):
    global status_sistema
    try:
        dados = json.loads(message.payload.decode("utf-8"))
        
        # Se recebemos preços da OMIE
        if "precos" in str(message.topic):
            hora_atual = str(time.localtime().tm_hour)
            status_sistema["preco_atual"] = dados["payload"]["precos"].get(hora_atual, 0.15)
            
            # Verificar a meteorologia
            print("[RPi] A consultar OpenWeatherMap...")
            dados_tempo = previsao_solar_coimbra.obter_previsao_coimbra()
            
            # Avaliar risco
            ativa, motivo = verificar_modo_resiliencia(dados_tempo)
            status_sistema["resiliencia_ativa"] = ativa
            status_sistema["resiliencia_motivo"] = motivo

        # Se recebemos dados do ESP32 (Sensores/Barramento)
        elif "barramento" in str(message.topic):
            status_sistema["soc_bateria"] = dados["payload"].get("soc", 75.0)
            status_sistema["producao_solar"] = dados["payload"].get("potencia_w", 0)

        # Tomar a decisão final
        novo_estado = decidir_estado()
        motivo_final = status_sistema["resiliencia_motivo"] if status_sistema["resiliencia_ativa"] else "Otimização Económica"
        
        # Enviar comando de volta para os ESP32
        comando = {
            "estado_ativo": novo_estado,
            "timestamp": time.time(),
            "motivo": motivo_final
        }
        client.publish(TOPICO_ESTADO, json.dumps(comando))
        
        # Logs no terminal do Raspberry Pi
        if status_sistema["resiliencia_ativa"]:
            print(f"⚠️ [ALERTA RPi] MODO RESILIÊNCIA: {novo_estado} | Motivo: {motivo_final}")
        else:
            print(f"[DECISÃO RPi] Estado: {novo_estado} | Preço: {status_sistema['preco_atual']}€")

    except Exception as e:
        print(f"Erro no Cérebro do RPi: {e}")

# --- SETUP MQTT RASPBERRY PI ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "SEARS_RPi_Brain")
client.on_message = ao_receber_mensagem
client.connect(BROKER, 1883)
client.subscribe(TOPICO_DADOS)

print("🧠 Cérebro do SEARS a correr no Raspberry Pi...")
client.loop_forever()
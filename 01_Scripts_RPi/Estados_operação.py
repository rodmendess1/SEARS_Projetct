import paho.mqtt.client as mqtt
import json
import time

# --- CONFIGURAÇÃO ---
BROKER = "localhost"
TOPICO_ESTADO = "sears/comando/estado"
TOPICO_DADOS = "sears/#"

# Variáveis de decisão (vêm das outras mensagens MQTT)
status_sistema = {
    "preco_atual": 0.15,
    "soc_bateria": 50.0, # State of Charge %
    "producao_solar": 0,
    "consumo_casa": 0
}

def decidir_estado():
    p = status_sistema
    # Limiares (Podem ser ajustados no Dashboard mais tarde)
    PRECO_ALTO = 0.22  # €/kWh
    PRECO_BAIXO = 0.10 # €/kWh
    SOC_MINIMO = 20.0  # %

    # LÓGICA DE DECISÃO
    if p["soc_bateria"] < SOC_MINIMO:
        return "COMPRAR_REDE" # Proteção da bateria
    
    if p["preco_atual"] > PRECO_ALTO and p["soc_bateria"] > SOC_MINIMO:
        return "USAR_BATERIA" # Arbitragem: poupar quando é caro
    
    if p["producao_solar"] > p["consumo_casa"]:
        if p["soc_bateria"] < 95:
            return "ARMAZENAR" # Guardar excesso solar
        else:
            return "VENDER_REDE" # Bateria cheia, vender lucro
            
    return "COMPRAR_REDE" # Estado padrão (Default)

def ao_receber_mensagem(client, userdata, message):
    global status_sistema
    try:
        dados = json.loads(message.payload.decode("utf-8"))
        # Atualiza o dicionário local com base no que chega dos outros scripts
        if "precos" in str(message.topic):
            # Exemplo: pega no preço da hora atual
            hora_atual = str(time.localtime().tm_hour)
            status_sistema["preco_atual"] = dados["payload"]["precos"].get(hora_atual, 0.15)
        
        elif "barramento" in str(message.topic):
            status_sistema["soc_bateria"] = 75.0 # Simulação para o exemplo
            status_sistema["producao_solar"] = dados["payload"]["potencia_w"]

        # Após atualizar dados, decide o novo estado
        novo_estado = decidir_estado()
        
        # Publica a decisão para os ESP32
        comando = {
            "estado_ativo": novo_estado,
            "timestamp": time.time(),
            "motivo": "Otimização Económica"
        }
        client.publish(TOPICO_ESTADO, json.dumps(comando))
        print(f"[DECISÃO] Estado: {novo_estado} | Preço: {status_sistema['preco_atual']}€")

    except Exception as e:
        print(f"Erro no Controller: {e}")

# --- SETUP MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "SEARS_Brain")
client.on_message = ao_receber_mensagem
client.connect(BROKER, 1883)
client.subscribe(TOPICO_DADOS)

print("Cérebro do SEARS Ativo. A processar estados...")
client.loop_forever()
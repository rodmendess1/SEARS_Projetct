import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import previsao_solar_coimbra

ULTIMO_CONTACTO = time.time()
LIMITE_SILENCIO = 30  # segundos
ESTADO_ANTERIOR = "MODO_SEGURANCA"

# --- CONFIGURAÇÃO ---
BROKER = "localhost"
TOPICO_ESTADO = "sears/comando/estado"
TOPICO_DADOS = "sears/#"
TOPICO_CONFIRMACAO = "sears/atuador/confirmacao"

# Variáveis de decisão (vêm das outras mensagens MQTT)
status_sistema = {
    "preco_atual": 0.15,
    "soc_bateria": 50.0, # State of Charge %
    "producao_solar": 0,
    "consumo_casa": 0,
    "override_manual": False,
    "resiliencia_ativa": False,
    "resiliencia_motivo": ""
}

# --- FUNÇÃO DE APOIO À DECISÃO FINANCEIRA ---
def calcular_margem_lucro(preco_venda, preco_compra):
    eficiencia = 0.85
    custo_degradacao = 0.02
    receita_efetiva = preco_venda * eficiencia
    custo_total = preco_compra + custo_degradacao
    return receita_efetiva - custo_total

def verificar_modo_resiliencia(previsoes_tempo):
    if not previsoes_tempo:
        return False, "Sem dados meteorológicos."

    palavras_perigo = ["trovoada", "tempestade", "chuva forte", "vendaval"]
    
    for hora, dados in previsoes_tempo.items():
        condicao_atual = dados.get("condicao", "").lower() 
        for perigo in palavras_perigo:
            if perigo in condicao_atual:
                return True, f"Risco detetado: {condicao_atual.capitalize()}"
                
    return False, "Previsão estável."

def decidir_estado():
    global ULTIMO_CONTACTO
    p = status_sistema

    # GESTÃO DE FALHA TIPO 2 (Rede Local)
    tempo_sem_noticias = time.time() - ULTIMO_CONTACTO
    if tempo_sem_noticias > LIMITE_SILENCIO:
        print(f"[ALERTA CRÍTICO] Sem comunicação com sensores há {int(tempo_sem_noticias)}s!")
        return "MODO_SEGURANCA" # Corta tudo por segurança
    
    # CONTROLO MANUAL (Override do Dashboard)
    if p["override_manual"]:
        print("[AVISO] Modo Backup ATIVADO pelo Utilizador. IA em pausa.")
        return "MODO_BACKUP" # Força o estado de reserva/segurança
    
    # Resiliência (Meteorologia manda)
    if p["resiliencia_ativa"]:
        print(f"⚠️ [RESILIÊNCIA] Ativada por: {p['resiliencia_motivo']}")
        return "EMERGENCIA_CARREGAR_100"

    # --- LÓGICA DE ARBITRAGEM INTEGRADA ---
    # Vamos assumir que carregámos a bateria a 0.08€ (vazio)
    PRECO_COMPRA_ESTIMADO = 0.08 
    lucro = calcular_margem_lucro(p["preco_atual"], PRECO_COMPRA_ESTIMADO)

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
            if lucro > 0:
                print(f"[IA] Venda Ativada: Lucro de {lucro:.3f}€/kWh")
                return "VENDER_REDE"
            else:
                print(f"[IA] Bateria cheia mas venda sem lucro ({lucro:.3f}€). Em espera.")
                return "COMPRAR_REDE" # Ou um estado de repouso
            
    return "COMPRAR_REDE" # Estado padrão (Default)

def ao_receber_mensagem(client, userdata, message):
    global status_sistema, ULTIMO_CONTACTO
    try:
        topico = str(message.topic)
        payload = message.payload.decode("utf-8")

        # --- LÓGICA DE SINCRONIZAÇÃO (ACK) ---
        if topico == TOPICO_CONFIRMACAO:
            dados_ack = json.loads(payload)
            estado_confirmado = dados_ack.get("comando_executado")
            print(f"🎯 [SYNC] Sincronização OK: ESP32 confirmou execução do estado: {estado_confirmado}")
            return # Paramos aqui, não é preciso decidir um novo estado para uma confirmação

        # --- LÓGICA PARA O BOTÃO DO DASHBOARD ---
        if "dashboard/override" in topico:
            # Converte "true", "1" ou "on" para Booleano do Python
            status_sistema["override_manual"] = payload.lower() in ["true", "1", "on"]
            print(f"[DASHBOARD] Override Manual: {status_sistema['override_manual']}")

        # 1. TRATAMENTO DE DADOS DO BARRAMENTO (DC)
        else:
            dados = json.loads(payload) # Aqui o Python transforma o texto em dicionário

        if "barramento" in topico or "quadro" in topico:
            ULTIMO_CONTACTO = time.time()

        if "barramento" in topico:      
            load = dados["payload"]
            # Vamos buscar os dados específicos que criámos no Simulador de Luxo
            status_sistema["soc_bateria"] = load.get("soc_bateria", 50.0) # SOC real
                
            # Produção Solar Real = V_bus * I_solar
            v_bus = load.get("v_bus", 48.0)
            i_solar = load.get("i_solar", 0.0)
            status_sistema["producao_solar"] = round(v_bus * i_solar, 2)
                
            print(f"[INFO] Dados DC Atualizados: Solar={status_sistema['producao_solar']}W")

            # 2. TRATAMENTO DE PREÇOS (OMIE)
        elif "precos" in topico:
            hora_atual = str(time.localtime().tm_hour)
            precos = dados["payload"].get("precos", {})
            status_sistema["preco_atual"] = precos.get(hora_atual, 0.15)
            print(f"[INFO] Preço Mercado: {status_sistema['preco_atual']}€/kWh")

            print("[RPi] A atualizar previsão meteorológica...")
            dados_tempo = previsao_solar_coimbra.obter_previsao_coimbra()
            ativa, motivo = verificar_modo_resiliencia(dados_tempo)
            status_sistema["resiliencia_ativa"] = ativa
            status_sistema["resiliencia_motivo"] = motivo

            # 3. TRATAMENTO DO QUADRO (AC - Trabalho do colega)
        elif "quadro" in topico:
            status_sistema["consumo_casa"] = dados["payload"].get("p_ativa", 0.0)

        # Após atualizar qualquer dado, decide o novo estado
        novo_estado = decidir_estado()
        
        # Lógica de Interlock: Evitar Carga e Descarga ao mesmo tempo
        GRUPO_CARGA = ["ARMAZENAR", "EMERGENCIA_CARREGAR_100", "COMPRAR_REDE"]
        GRUPO_DESCARGA = ["USAR_BATERIA", "VENDER_REDE"]
        
        inversao = (ESTADO_ANTERIOR in GRUPO_CARGA and novo_estado in GRUPO_DESCARGA) or \
                   (ESTADO_ANTERIOR in GRUPO_DESCARGA and novo_estado in GRUPO_CARGA)

        if inversao:
            print(f"⚠️ [INTERLOCK] Inversão detetada! Forçando STOP de segurança...")
            stop_msg = {"estado_ativo": "MODO_SEGURANCA", "motivo": "Proteção de Hardware (Interlock)"}
            client.publish(TOPICO_ESTADO, json.dumps(stop_msg))
            time.sleep(0.3) # Pausa física para os relés

        # Publica a decisão
        comando = {
            "estado_ativo": novo_estado,
            "timestamp": time.time(),
            "motivo": "Otimização Económica / Resiliência"
        }
        client.publish(TOPICO_ESTADO, json.dumps(comando))
        ESTADO_ANTERIOR = novo_estado

    except Exception as e:
        print(f"Erro no Controller: {e}")

# --- SETUP MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "SEARS_Brain")
client.on_message = ao_receber_mensagem
client.connect(BROKER, 1883)
client.subscribe(TOPICO_DADOS)

print("Cérebro do SEARS Ativo. A processar estados...")
client.loop_forever()

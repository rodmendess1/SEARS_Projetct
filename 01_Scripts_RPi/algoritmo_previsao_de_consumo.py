import sqlite3
import pandas as pd
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# --- CONFIGURAÇÃO ---
DB_NAME = "sears_data.db" 
BROKER = "localhost"
TOPICO_PREVISAO = "sears/previsao/consumo"

print(f"--- SEARS IA: Algoritmo de Previsão de Consumo ---")

try:
    # 1. Ligar à Base de Dados
    conn = sqlite3.connect(DB_NAME)

    # 2. QUERY CORRIGIDA (Alinhada com o novo Database Logger)
    # Tabela: telemetria_ac | Coluna: p_ativa
    query = """
        SELECT timestamp, p_ativa as potencia_w 
        FROM telemetria_ac 
        ORDER BY timestamp ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("[AVISO] Ainda não há dados suficientes na tabela 'telemetria_ac'.")
    else:
        # 3. Processamento de Datas
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hora'] = df['timestamp'].dt.hour
        df['data'] = df['timestamp'].dt.date

        # 4. Agrupar por hora (Média horária)
        df_hora = df.groupby(['data', 'hora'])['potencia_w'].mean().reset_index()
        df_hora.rename(columns={'potencia_w': 'consumo_real_w'}, inplace=True)

        # 5. Algoritmo EMA (Média Móvel Exponencial)
        df_hora['previsao_ia_w'] = df_hora.groupby('hora')['consumo_real_w'] \
                                .transform(lambda x: x.ewm(span=3, adjust=False).mean().shift(1))

        # 6. Previsão para a Próxima Hora
        hora_atual = datetime.now().hour
        proxima_hora = (hora_atual + 1) % 24
        
        historico = df_hora[df_hora['hora'] == proxima_hora]
        
        if len(historico) < 2:
            print(f"[IA] A aguardar mais histórico para a hora {proxima_hora}:00...")
        else:
            ultimo_real = historico['consumo_real_w'].iloc[-1]
            ultima_prev = historico['previsao_ia_w'].iloc[-1]
            if pd.isna(ultima_prev): ultima_prev = ultimo_real
                
            alpha = 2 / (3 + 1)
            previsao_final = round((ultimo_real * alpha) + (ultima_prev * (1 - alpha)), 2)
            
            # --- NOVO: PUBLICAR RESULTADO PARA O SISTEMA ---
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                client.connect(BROKER, 1883)
                
                msg = {
                    "metadata": {
                        "device_id": "ia_predictor",
                        "timestamp": datetime.now().isoformat(),
                        "metodo": "EMA_Span3"
                    },
                    "payload": {
                        "proxima_hora": proxima_hora,
                        "previsao_w": previsao_final,
                        "unidade": "W"
                    }
                }
                client.publish(TOPICO_PREVISAO, json.dumps(msg), retain=True)
                client.disconnect()
                
                print(f"✅ PREVISÃO CONCLUÍDA")
                print(f"Consumo estimado para as {proxima_hora}:00 -> {previsao_final} W (Enviado via MQTT)")
            except Exception as e:
                print(f"[ERRO MQTT] Não foi possível publicar a previsão: {e}")

except sqlite3.OperationalError:
    print(f"[ERRO] Base de dados '{DB_NAME}' não encontrada ou sem tabelas AC.")

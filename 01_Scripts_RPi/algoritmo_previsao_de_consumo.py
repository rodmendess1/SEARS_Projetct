import sqlite3
import pandas as pd
from datetime import datetime

# Nome do ficheiro que o 'database_logger.py' cria
DB_NAME = "sears_data.db" 

print(f"A ligar à base de dados '{DB_NAME}' para análise IA...")

try:
    # 1. Ligar ao ficheiro da base de dados
    conn = sqlite3.connect(DB_NAME)

    # 2. Procurar dados de consumo
    # Nota: Certificar que o simulador envia 'consumo_casa' no sensor_type
    query = """
        SELECT timestamp, potencia_w 
        FROM telemetria 
        WHERE tipo_sensor = 'consumo_casa' 
        ORDER BY timestamp ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("[AVISO] A base de dados existe mas ainda não tem dados de 'consumo_casa'.")
    else:
        # 3. Processamento de Datas
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hora'] = df['timestamp'].dt.hour
        df['data'] = df['timestamp'].dt.date

        # 4. Agrupar por hora (Média horária)
        df_hora = df.groupby(['data', 'hora'])['potencia_w'].mean().reset_index()
        df_hora.rename(columns={'potencia_w': 'consumo_real_w'}, inplace=True)

        # 5. Algoritmo EMA (Média Móvel Exponencial)
        # O 'span=3' significa que ele dá muito peso aos últimos 3 dias
        df_hora['previsao_ia_w'] = df_hora.groupby('hora')['consumo_real_w'] \
                                .transform(lambda x: x.ewm(span=3, adjust=False).mean().shift(1))

        # 6. Previsão para a Próxima Hora
        hora_atual = datetime.now().hour
        proxima_hora = (hora_atual + 1) % 24
        
        historico = df_hora[df_hora['hora'] == proxima_hora]
        
        if len(historico) < 2:
            print(f"[IA] A aguardar mais dados históricos para a hora {proxima_hora}:00...")
        else:
            ultimo_real = historico['consumo_real_w'].iloc[-1]
            ultima_prev = historico['previsao_ia_w'].iloc[-1]
            if pd.isna(ultima_prev): ultima_prev = ultimo_real
                
            alpha = 2 / (3 + 1)
            previsao_final = (ultimo_real * alpha) + (ultima_prev * (1 - alpha))
            
            print(f"\n✅ ANÁLISE CONCLUÍDA")
            print(f"Previsão de consumo para as {proxima_hora}:00 -> {previsao_final:.0f} W")

except sqlite3.OperationalError:
    print(f"[ERRO] Não encontrei o ficheiro '{DB_NAME}'. Garante que o logger já correu pelo menos uma vez.")
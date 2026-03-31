import requests
from datetime import datetime

# --- CONFIGURAÇÃO SEARS ---
# Chave de API do OpenWeatherMap
API_KEY = "5883339336b5a0385f3dae2afbd43f75" 

LAT = "40.2033"  # Coimbra
LON = "-8.4103"  # Coimbra
PAINEL_WATT_PICO = 60  # Potência do teu painel

def obter_previsao_coimbra():
    """
    Obtém a previsão meteorológica e estima a produção do painel de 60W 
    para as próximas 24h em Coimbra.
    """
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=pt"
    
    try:
        print("A contactar o OpenWeatherMap...")
        response = requests.get(url, timeout=10)
        dados = response.json()
        
        # --- O DETETIVE DE ERROS ---
        # Se o site não devolver o código 200 (OK), mostramos o erro real:
        if str(dados.get("cod")) != "200":
            mensagem_erro = dados.get("message", "Erro desconhecido")
            print(f"\n❌ Erro da API OpenWeather: {mensagem_erro}")
            print("Dica: Se acabaste de criar a chave, ela pode demorar até 2 horas a ficar ativa!")
            return None

        previsoes_producao = {}
        
        print(f"\n=== SEARS: Previsão Solar para Coimbra ({datetime.now().strftime('%d/%m')}) ===")
        
        # Analisar as próximas 8 entradas (3h cada = 24 horas)
        for item in dados.get('list', [])[:8]:
            dt = datetime.fromtimestamp(item['dt'])
            hora_str = dt.strftime("%H:%M")
            nuvens = item['clouds']['all']
            temp = item['main']['temp']
            condicao = item['weather'][0]['description'].capitalize()
            
            # Lógica de estimativa de produção (Simplificada para o SEARS)
            # 1. Se for noite em Coimbra (ex: 20h às 07h), produção é 0
            if dt.hour < 7 or dt.hour > 19:
                estimativa_w = 0.0
            else:
                # 2. Se for dia, a produção depende da cobertura de nuvens
                fator_sol = (100 - (nuvens * 0.75)) / 100 
                estimativa_w = PAINEL_WATT_PICO * fator_sol
            
            previsoes_producao[hora_str] = round(estimativa_w, 2)
            
            # Print formatado para o teu terminal
            status = "☀️ Sol" if nuvens < 20 else "☁️ Nuvens" if nuvens < 80 else "🌧️ Encoberto"
            print(f"[{hora_str}] {temp:>5.1f}°C | {status:<12} ({nuvens:>3}% nuvens) | Est. Produção: {estimativa_w:>5.2f}W")
            
        return previsoes_producao

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erro de ligação à Internet: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Erro inesperado no código: {e}")
        return None

# --- Execução de Teste ---
if __name__ == "__main__":
    previsao = obter_previsao_coimbra()
    if previsao:
        print("\n✅ Dados extraídos com sucesso para o Modelo de Decisão SEARS.")

        
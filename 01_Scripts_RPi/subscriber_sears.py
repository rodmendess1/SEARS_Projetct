import paho.mqtt.client as mqtt

# Configurações do Broker
BROKER = "localhost" 
PORT = 1883

# Função chamada quando uma mensagem chega
def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode("utf-8")
    
    print(f"--- Nova Mensagem Recebida ---")
    
    # Lógica para distinguir os ESP32 pelos tópicos
    if "quadro" in topic:
        print(f"[ESP32 #1 - QUADRO] Tópico: {topic} | Valor: {payload}")
        # Aqui no futuro podemos guardar na Base de Dados
        
    elif "barramento" in topic:
        print(f"[ESP32 #2 - BARRAMENTO] Tópico: {topic} | Valor: {payload}")
        
    else:
        print(f"[OUTRO] Tópico: {topic} | Valor: {payload}")

# Configuração do Cliente
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "RPi_Subscriber")
client.on_message = on_message

print(f"A ligar ao broker {BROKER}...")
client.connect(BROKER, PORT)

# Subscrever a todos os tópicos que comecem por 'sears/'
# O '#' é um wildcard (coringa) que apanha tudo o que vier depois
client.subscribe("sears/#")

print("Aguardando dados... (Ctrl+C para sair)")
client.loop_forever()
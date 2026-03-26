import paho.mqtt.client as mqtt
import json

BROKER = "localhost"
PORTA = 1883
TOPICO_BASE = "sears/#"

def ao_receber_mensagem(client, userdata, message):
    payload_raw = message.payload.decode("utf-8")
    
    print(f"\n" + "="*45)
    print(f"📡 TÓPICO: {message.topic}")
    
    try:
        dados = json.loads(payload_raw)
        
        # Verifica se é a nossa estrutura aninhada
        if "metadata" in dados and "payload" in dados:
            meta = dados["metadata"]
            load = dados["payload"]
            
            print(f"🆔 ID: {meta['device_id']} | 🕒 {meta['timestamp'][:19]}")
            print("-" * 45)
            
            # Se for a mensagem dos preços, mostra a lista
            if "precos" in load:
                # Usamos 'data_referencia' para bater certo com o Publisher
                data_alvo = load.get('data_referencia', 'Desconhecida')
                print(f"📅 PREÇOS PARA: {data_alvo} ({load['unidade']})")
                precos = load["precos"]
                for h in sorted(precos.keys(), key=int):
                    print(f"  {int(h):02d}h: {precos[h]:.5f} €/kWh")
            else:
                print(f"Conteúdo: {load}")
        else:
            print(f"JSON Simples: {dados}")

    except json.JSONDecodeError:
        print(f"VALOR BRUTO: {payload_raw}")
    
    print("="*45)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "RPi_Monitor")
client.on_message = ao_receber_mensagem
client.connect(BROKER, PORTA)
client.subscribe(TOPICO_BASE)

print("A aguardar dados em tempo real... (Ctrl+C para parar)")
client.loop_forever()
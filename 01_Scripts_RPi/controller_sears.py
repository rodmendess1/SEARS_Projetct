# Ficheiro: controller_sears.py (no Raspberry Pi)

def publicar_comando_seguro(novo_estado):
    # Dicionário de estados que não podem coexistir
    conflitos = {
        "CARREGAR": "DESCARREGAR",
        "DESCARREGAR": "CARREGAR"
    }
    
    # Se o novo estado for o oposto do atual, forçamos um "STOP" primeiro
    if novo_estado == conflitos.get(estado_atual):
        client.publish("sears/comando", "STOP")
        time.sleep(0.2) # Pausa para os relés abrirem fisicamente
    
    client.publish("sears/comando", novo_estado)
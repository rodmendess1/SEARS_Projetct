subscriber_sears.py: É o monitor geral. Este script funciona como um "ouvinte". Ele subscreve todos os tópicos do projeto para que possas ver no terminal tudo o que 
está a ser dito entre os vários componentes (preços, sensores, decisões). É usado principalmente para diagnóstico.

omie_scraper.py: É o coletor de dados brutos. A função dele é ir "raspar" (scraping) os preços reais da eletricidade diretamente do mercado ibérico (OMIE). Ele obtém
os valores, mas ainda não os envia para o sistema; apenas os recolhe da fonte.

omie_mqtt_publisher.py: É o emissor de preços. Ele pega nos dados que o scraper recolheu (ou numa lista simulada) e "grita-os" para o Broker MQTT. É graças a este 
script que o Dashboard e o Cérebro sabem quanto custa a luz a cada hora.

simulador_sensores_sears.py: É o gémeo digital (Hardware Virtual). Como ainda não tens os painéis e baterias físicos, este script simula o comportamento deles. Ele 
envia dados falsos de voltagem, corrente e estado da bateria para que possas testar o software como se o material já tivesse chegado.

database_logger.py: É o escrivão da base de dados. Este é o script que te toca mais de perto. Ele fica atento a todas as mensagens que passam no MQTT e, assim que 
chega um dado de sensor ou um preço, ele abre a tua base de dados SQLite e grava lá a informação para criar o histórico.

previsao_solar_coimbra.py: É o consultor meteorológico. Ele liga-se a uma API de meteorologia (como a OpenWeather) e verifica se vai estar sol ou chuva em Coimbra. 
Esta informação é vital para o sistema decidir se deve guardar energia na bateria ou gastá-la.

estados_operacao.py: É o Cérebro (Lógica de Decisão). Este é o script mais importante. Ele lê os preços do omie_mqtt, a previsão do previsao_solar e o estado da 
bateria do simulador. Com base nisso, ele decide o estado do sistema: "Vender Energia", "Carregar Bateria", "Usar Bateria" ou "Proteção".

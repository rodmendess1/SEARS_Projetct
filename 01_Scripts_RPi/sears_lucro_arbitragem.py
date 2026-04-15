def vale_a_pena_vender(preco_venda, preco_compra, eficiencia=0.85, custo_degradacao=0.02):
    """
    Avalia se a venda de energia da bateria dá lucro real.
    
    :param preco_venda: Preço atual da OMIE (€/kWh)
    :param preco_compra: Preço a que a bateria foi carregada (€/kWh)
    :param eficiencia: Eficiência global do sistema (ex: 0.85 para 85%)
    :param custo_degradacao: Custo de desgaste da bateria por kWh (€/kWh)
    :return: True (Vender) ou False (Aguardar) e a margem de lucro.
    """
    
    # O valor real que entra no bolso depois das perdas do inversor/bateria
    receita_efetiva = preco_venda * eficiencia
    
    # O custo real da energia que tens armazenada
    custo_total = preco_compra + custo_degradacao
    
    margem = receita_efetiva - custo_total
    
    if margem > 0:
        return True, margem
    else:
        return False, margem

# --- Exemplo de Teste ---
# Comprei de noite a 0.05€, quero vender de dia a 0.15€. 
# A bateria tem 85% de eficiência e 0.02€ de desgaste por kWh.
vender, lucro = vale_a_pena_vender(0.15, 0.05, 0.85, 0.02)

if vender:
    print(f"LUCRO DETETADO! Margem limpa de: {lucro:.3f} €/kWh")
else:
    print(f"PREJUÍZO! Não vender. Margem seria de: {lucro:.3f} €/kWh")
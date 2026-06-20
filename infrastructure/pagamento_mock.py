import random

def simular_pagamento(pedido_id: int, valor: float) -> dict:
    """
    Mock: 70% de chance de aprovar, 30% de negar.
    Retorna { "status": "APROVADO" ou "NEGADO", "transacao_id": "mock_123" }
    """
    aprovado = random.random() < 0.7  # 70% aprova
    status = "APROVADO" if aprovado else "NEGADO"
    transacao_id = f"mock_{pedido_id}_{random.randint(1000,9999)}"
    return {
        "status": status,
        "transacao_externa_id": transacao_id
    }
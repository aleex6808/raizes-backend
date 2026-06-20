from sqlalchemy.orm import Session
from domain.models import Pedido, ItemPedido, Estoque, Produto, Pagamento, Cliente
from domain.enums import CanalPedido, StatusPedido
from infrastructure.pagamento_mock import simular_pagamento

class PedidoService:
    @staticmethod
    def criar_pedido(db: Session, cliente_id: int, unidade_id: int, canal: CanalPedido, itens: list):
        # 1. Valida canal
        if not canal:
            raise ValueError("Canal do pedido é obrigatório")
        
        # 2. Valida itens e calcula total
        total = 0.0
        itens_criados = []
        for item in itens:
            produto = db.query(Produto).filter(Produto.id == item["produto_id"]).first()
            if not produto:
                raise Exception(f"Produto {item['produto_id']} não encontrado")
            # Verifica estoque
            estoque = db.query(Estoque).filter(
                Estoque.produto_id == produto.id,
                Estoque.unidade_id == unidade_id
            ).first()
            if not estoque or estoque.quantidade < item["quantidade"]:
                raise Exception(f"Estoque insuficiente para {produto.nome}")
            total += produto.preco * item["quantidade"]
            itens_criados.append({
                "produto": produto,
                "quantidade": item["quantidade"],
                "preco": produto.preco
            })
        
        # 3. Cria pedido
        pedido = Pedido(
            cliente_id=cliente_id,
            unidade_id=unidade_id,
            canal=canal,
            valor_total=total,
            status=StatusPedido.CRIADO
        )
        db.add(pedido)
        db.flush()  # pega o id
        
        # 4. Cria itens e baixa estoque
        for item_data in itens_criados:
            item = ItemPedido(
                pedido_id=pedido.id,
                produto_id=item_data["produto"].id,
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["preco"]
            )
            db.add(item)
            # Baixa estoque
            estoque = db.query(Estoque).filter(
                Estoque.produto_id == item_data["produto"].id,
                Estoque.unidade_id == unidade_id
            ).first()
            estoque.quantidade -= item_data["quantidade"]
        
        db.commit()
        db.refresh(pedido)
        return pedido

    @staticmethod
    def processar_pagamento(db: Session, pedido_id: int):
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            raise Exception("Pedido não encontrado")
        if pedido.status != StatusPedido.CRIADO:
            raise Exception("Pedido já foi pago ou cancelado")
        
        # Chama mock
        resposta = simular_pagamento(pedido_id, pedido.valor_total)
        
        # Registra pagamento
        pag = Pagamento(
            pedido_id=pedido.id,
            status=resposta["status"],
            transacao_externa_id=resposta["transacao_externa_id"]
        )
        db.add(pag)
        
        # Atualiza status do pedido
        if resposta["status"] == "APROVADO":
            pedido.status = StatusPedido.PAGO
        else:
            pedido.status = StatusPedido.CRIADO  # mantém como criado para tentar novamente
        
        db.commit()
        return pag
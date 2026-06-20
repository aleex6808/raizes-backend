from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from infrastructure.database import Base
from domain.enums import CanalPedido, StatusPedido, PerfilUsuario
import datetime

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)  # Armazenar hash
    perfil = Column(Enum(PerfilUsuario), default=PerfilUsuario.CLIENTE)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=True)

class Unidade(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String)

class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"))
    sazonal = Column(Boolean, default=False)

class Estoque(Base):
    __tablename__ = "estoque"
    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    unidade_id = Column(Integer, ForeignKey("unidades.id"))
    quantidade = Column(Integer, default=0)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    data_nascimento = Column(String, nullable=True)
    consentimento_lgpd = Column(Boolean, default=False)

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    unidade_id = Column(Integer, ForeignKey("unidades.id"))
    canal = Column(Enum(CanalPedido), nullable=False)  # OBRIGATÓRIO
    status = Column(Enum(StatusPedido), default=StatusPedido.CRIADO)
    valor_total = Column(Float, default=0.0)
    data_hora = Column(DateTime, default=datetime.datetime.utcnow)

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    status = Column(String, default="PENDENTE")  # APROVADO, NEGADO
    transacao_externa_id = Column(String, nullable=True)
    data_hora = Column(DateTime, default=datetime.datetime.utcnow)

class Fidelidade(Base):
    __tablename__ = "fidelidade"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), unique=True)
    pontos = Column(Integer, default=0)
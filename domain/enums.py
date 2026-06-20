from enum import Enum

class CanalPedido(str, Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"

class StatusPedido(str, Enum):
    CRIADO = "CRIADO"
    PAGO = "PAGO"
    PREPARO = "PREPARO"
    PRONTO = "PRONTO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"

class PerfilUsuario(str, Enum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"
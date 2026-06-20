from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import jwt
import datetime
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from domain.models import Usuario, Unidade, Produto, Pedido, Estoque, Cliente, Fidelidade
from domain.enums import CanalPedido, StatusPedido, PerfilUsuario
from infrastructure.database import get_db, engine, Base
from application.services import PedidoService

load_dotenv()

# Cria as tabelas no banco (se não existirem)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Raizes do Nordeste API",
    version="1.0",
    description="API para gestão da rede de lanchonetes",
    swagger_ui_parameters={"persistAuthorization": True}
)

# ==================== SEGURANÇA ====================
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-super-secret-key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ==================== SCHEMAS (Pydantic) ====================
class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: PerfilUsuario = PerfilUsuario.CLIENTE

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class PedidoCreate(BaseModel):
    cliente_id: int
    unidade_id: int
    canal: CanalPedido
    itens: List[dict]  # [{"produto_id": 1, "quantidade": 2}]

class PagamentoRequest(BaseModel):
    pedido_id: int

# ==================== DEPENDÊNCIA DE AUTENTICAÇÃO ====================
def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Valida o token JWT e retorna os dados do usuário (payload).
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_user(payload: dict = Depends(verificar_token), db: Session = Depends(get_db)) -> Usuario:
    """
    Busca o usuário no banco a partir do email contido no token.
    """
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Token inválido: email não encontrado")
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return usuario

# ==================== ENDPOINTS ====================

@app.post("/auth/register", status_code=201)
def register(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Cadastra um novo usuário."""
    # Verifica se email já existe
    existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    hashed = pwd_context.hash(usuario.senha)
    novo = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=hashed,
        perfil=usuario.perfil
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "email": novo.email, "perfil": novo.perfil}

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Autentica o usuário e retorna um JWT."""
    usuario = db.query(Usuario).filter(Usuario.email == req.email).first()
    if not usuario or not pwd_context.verify(req.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    payload = {
        "sub": usuario.email,
        "perfil": usuario.perfil,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# --- Unidades ---
@app.get("/unidades")
def listar_unidades(db: Session = Depends(get_db), _=Depends(verificar_token)):
    """Lista todas as unidades (requer autenticação)."""
    return db.query(Unidade).all()

@app.get("/unidades/{unidade_id}/produtos")
def cardapio(unidade_id: int, db: Session = Depends(get_db), _=Depends(verificar_token)):
    """Lista os produtos de uma unidade (requer autenticação)."""
    return db.query(Produto).filter(Produto.unidade_id == unidade_id).all()

# --- Pedidos ---
@app.post("/pedidos", status_code=201)
def criar_pedido(pedido: PedidoCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """
    Cria um novo pedido. 
    ATENÇÃO: O campo 'canal' é OBRIGATÓRIO (APP, TOTEM, BALCAO, PICKUP, WEB).
    """
    try:
        novo = PedidoService.criar_pedido(
            db=db,
            cliente_id=pedido.cliente_id,
            unidade_id=pedido.unidade_id,
            canal=pedido.canal,
            itens=pedido.itens
        )
        return {"pedido_id": novo.id, "status": novo.status, "total": novo.valor_total, "canal": novo.canal}
    except Exception as e:
        # Tratamento de erro padronizado
        raise HTTPException(status_code=409, detail=str(e))

@app.get("/pedidos")
def listar_pedidos(
    canal: Optional[CanalPedido] = None,
    status: Optional[StatusPedido] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Lista pedidos com filtros opcionais por canal e status.
    Exemplo: /pedidos?canal=APP
    """
    query = db.query(Pedido)
    if canal:
        query = query.filter(Pedido.canal == canal)
    if status:
        query = query.filter(Pedido.status == status)
    return query.all()

@app.get("/pedidos/{pedido_id}")
def status_pedido(pedido_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Consulta o status de um pedido específico."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {"id": pedido.id, "status": pedido.status, "total": pedido.valor_total, "canal": pedido.canal}

# --- Pagamento (Mock) ---
@app.post("/pagamentos/solicitar")
def solicitar_pagamento(req: PagamentoRequest, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Simula uma solicitação de pagamento ao gateway externo."""
    try:
        pagamento = PedidoService.processar_pagamento(db, req.pedido_id)
        return {
            "pedido_id": req.pedido_id,
            "status_pagamento": pagamento.status,
            "transacao": pagamento.transacao_externa_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/pagamentos/webhook")
def webhook(payload: dict, db: Session = Depends(get_db)):
    """Endpoint para receber notificações do gateway de pagamento."""
    # Apenas simula recebimento
    return {"ok": True}

# --- Fidelidade ---
@app.get("/fidelidade/{cliente_id}")
def pontos_cliente(cliente_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Consulta os pontos de fidelidade de um cliente."""
    fid = db.query(Fidelidade).filter(Fidelidade.cliente_id == cliente_id).first()
    if not fid:
        return {"cliente_id": cliente_id, "pontos": 0}
    return {"cliente_id": cliente_id, "pontos": fid.pontos}

# ==================== SEED (para criar dados de teste via API) ====================
@app.post("/seed", status_code=201)
def seed_database(db: Session = Depends(get_db)):
    """
    Endpoint auxiliar para popular o banco com dados de teste.
    Use apenas uma vez para ter dados iniciais.
    """
    # Verifica se já tem dados
    if db.query(Unidade).count() > 0:
        return {"message": "Banco já populado"}

    # Cria unidade
    unidade = Unidade(nome="Recife Centro", endereco="Rua da Aurora, 123")
    db.add(unidade)
    db.commit()
    db.refresh(unidade)

    # Cria produto
    produto = Produto(nome="Tapioca", preco=12.50, unidade_id=unidade.id)
    db.add(produto)
    db.commit()
    db.refresh(produto)

    # Cria estoque
    estoque = Estoque(produto_id=produto.id, unidade_id=unidade.id, quantidade=10)
    db.add(estoque)
    db.commit()

    # Cria usuário (cliente)
    senha_hash = pwd_context.hash("123456")
    usuario = Usuario(
        nome="Cliente Teste",
        email="cliente@teste.com",
        senha_hash=senha_hash,
        perfil=PerfilUsuario.CLIENTE
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    # Cria cliente (vinculado ao usuário)
    cliente = Cliente(
        usuario_id=usuario.id,
        data_nascimento="1990-01-01",
        consentimento_lgpd=True
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    # Cria fidelidade
    fid = Fidelidade(cliente_id=cliente.id, pontos=100)
    db.add(fid)
    db.commit()

    return {
        "message": "Dados criados com sucesso!",
        "unidade_id": unidade.id,
        "produto_id": produto.id,
        "cliente_id": cliente.id,
        "email": "cliente@teste.com",
        "senha": "123456"
    }
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LoginRequest(BaseModel):
    documento: str = Field(..., description="CPF ou CNPJ do usuário")
    senha: str = Field(..., description="Senha manual cadastrada")

class Token(BaseModel):
    access_token: str
    token_type: str
    nome_estabelecimento: str
    is_admin: bool

class PlacaResponse(BaseModel):
    id_placa: int
    dono_documento: str
    nome_exibicao: Optional[str] = None
    tipo_dispositivo: Optional[str] = None
    local_uso: Optional[str] = None
    loja_unidade: Optional[str] = None
    responsavel: Optional[str] = None
    observacao: Optional[str] = None
    link_frente: Optional[str] = None
    link_verso: Optional[str] = None
    pix_chave: Optional[str] = None
    pix_tipo_valor: Optional[str] = None
    pix_valor_fixo: Optional[float] = None
    status_ativa: bool

    class Config:
        from_attributes = True

class PlacaUpdate(BaseModel):
    nome_exibicao: Optional[str] = None
    tipo_dispositivo: Optional[str] = None
    local_uso: Optional[str] = None
    loja_unidade: Optional[str] = None
    responsavel: Optional[str] = None
    observacao: Optional[str] = None
    link_frente: Optional[str] = None
    link_verso: Optional[str] = None
    pix_chave: Optional[str] = None
    pix_tipo_valor: Optional[str] = None
    pix_valor_fixo: Optional[float] = None

class ComercianteCreate(BaseModel):
    documento: str = Field(..., description="CPF ou CNPJ do comerciante")
    senha: str = Field(..., description="Senha de acesso")
    nome_estabelecimento: str = Field(..., description="Nome do estabelecimento")
    id_placa: Optional[int] = Field(None, description="ID físico do dispositivo inicial")
    tipo_dispositivo: Optional[str] = None

class PlacaVinculo(BaseModel):
    id_placa: int = Field(..., description="ID físico do dispositivo")
    dono_documento: str = Field(..., description="CPF ou CNPJ do comerciante proprietário")
    tipo_dispositivo: Optional[str] = None

class PlacaStatusUpdate(BaseModel):
    status_ativa: bool = Field(..., description="Status ativo/suspenso do dispositivo")

class ComercianteResponse(BaseModel):
    documento: str
    nome_estabelecimento: str
    is_admin: bool
    ativo: bool
    placas: List[PlacaResponse]

    class Config:
        from_attributes = True

class ClienteStatusUpdate(BaseModel):
    ativo: bool = Field(..., description="Status ativo/inativo do cliente (login bloqueado quando inativo)")

class ClickDaily(BaseModel):
    data: str
    frente: int
    verso: int

class PlateStats(BaseModel):
    id_placa: int
    frente_cliques: int
    verso_cliques: int
    total_cliques: int

class DashboardStats(BaseModel):
    total_placas: int
    total_cliques: int
    cliques_hoje: int
    frente_cliques: int
    verso_cliques: int
    historico_cliques_diarios: List[ClickDaily]
    placas_stats: List[PlateStats] = Field(default_factory=list)

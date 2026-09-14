from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, CheckConstraint, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    documento = Column(String(20), primary_key=True, index=True)
    senha = Column(String(255), nullable=False)
    nome_estabelecimento = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False, server_default="false", nullable=False)
    ativo = Column(Boolean, default=True, server_default="true", nullable=False)

    placas = relationship("Placa", back_populates="dono", cascade="all, delete-orphan")

class Placa(Base):
    __tablename__ = "placas"

    id_placa = Column(Integer, primary_key=True)
    dono_documento = Column(String(20), ForeignKey("usuarios.documento", ondelete="CASCADE"), nullable=False)
    nome_exibicao = Column(String(120), nullable=True)
    tipo_dispositivo = Column(String(30), nullable=True)
    local_uso = Column(String(120), nullable=True)
    loja_unidade = Column(String(120), nullable=True)
    responsavel = Column(String(120), nullable=True)
    observacao = Column(String(500), nullable=True)
    link_frente = Column(String(500))
    link_verso = Column(String(500))
    pix_chave = Column(String(100), nullable=True)
    pix_tipo_valor = Column(String(10), nullable=True)
    pix_valor_fixo = Column(Numeric(10, 2), nullable=True)
    status_ativa = Column(Boolean, default=True, server_default="true", nullable=False)

    dono = relationship("Usuario", back_populates="placas")
    cliques = relationship("HistoricoClique", back_populates="placa", cascade="all, delete-orphan")

class HistoricoClique(Base):
    __tablename__ = "historico_cliques"

    id_clique = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_placa = Column(Integer, ForeignKey("placas.id_placa", ondelete="CASCADE"), nullable=False)
    data_hora = Column(DateTime(timezone=True), server_default=func.now())
    lado = Column(String(10), nullable=False)

    __table_args__ = (
        CheckConstraint("lado IN ('Frente', 'Verso')", name='chk_lado'),
    )

    placa = relationship("Placa", back_populates="cliques")

import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
from .pix import generate_pix_string

from .database import get_db, engine, Base
from .models import Usuario, Placa, HistoricoClique
from .schemas import LoginRequest, Token, PlacaResponse, PlacaUpdate, DashboardStats, ClickDaily, PlateStats, ComercianteCreate, PlacaStatusUpdate, PlacaVinculo, ComercianteResponse, ClienteStatusUpdate
from .auth import verify_password, create_access_token, get_current_user, get_password_hash

# Cria as tabelas se elas não existirem (garantia adicional, embora tenhamos o init.sql)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="OsmarDev Store API", description="Backend para gerenciamento e redirecionamento de dispositivos OsmarDev Store")

# Configuração de CORS para permitir desenvolvimento local facilitado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def render_error_page(title: str, message: str) -> HTMLResponse:
    """Renderiza uma página HTML estilizada e premium para erros de redirecionamento."""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                background: radial-gradient(circle at top right, #1e1b4b, #09090b);
                color: #f4f4f5;
                font-family: 'Outfit', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 40px 30px;
                width: 100%;
                max-width: 420px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            }}
            .icon {{
                font-size: 48px;
                margin-bottom: 20px;
                display: inline-block;
                background: linear-gradient(135deg, #f43f5e, #ec4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 12px;
                background: linear-gradient(to right, #ffffff, #a1a1aa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            p {{
                font-size: 16px;
                color: #a1a1aa;
                line-height: 1.6;
                margin-bottom: 24px;
            }}
            .logo {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 2px;
                text-transform: uppercase;
                color: rgba(255, 255, 255, 0.3);
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="icon">⚠️</span>
            <h1>{title}</h1>
            <p>{message}</p>
            <div class="logo">OsmarDev Store</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

def render_blocked_page(id_placa: int) -> HTMLResponse:
    """Renderiza uma página HTML premium informando que o dispositivo está temporariamente suspenso."""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Serviço Suspenso</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                background: radial-gradient(circle at top right, #311010, #09090b);
                color: #f4f4f5;
                font-family: 'Outfit', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.02);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 99, 99, 0.15);
                border-radius: 24px;
                padding: 40px 30px;
                width: 100%;
                max-width: 420px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            }}
            .icon {{
                font-size: 56px;
                margin-bottom: 20px;
                display: inline-block;
                color: #ef4444;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 12px;
                background: linear-gradient(to right, #ff8888, #f43f5e);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            p {{
                font-size: 15px;
                color: #d1d5db;
                line-height: 1.6;
                margin-bottom: 24px;
            }}
            .logo {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 2px;
                text-transform: uppercase;
                color: rgba(255, 99, 99, 0.4);
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="icon">🚫</span>
            <h1>Dispositivo Suspenso</h1>
            <p>Este dispositivo OsmarDev Store está temporariamente suspenso para manutenção administrativa. Se você é o proprietário, entre em contato com o suporte.</p>
            <div class="logo">OsmarDev Store</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

def get_current_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Verifica se o usuário atual é administrador do sistema."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores do sistema possuem permissão."
        )
    return current_user

# Template HTML do Pix
PIX_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pagamento Pix | __MERCHANT_NAME__</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            background: radial-gradient(circle at top right, #091e1d, #09090b);
            color: #f4f4f5;
            font-family: 'Outfit', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 32px 24px;
            width: 100%;
            max-width: 400px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }
        .pix-header {
            margin-bottom: 24px;
        }
        .pix-icon {
            font-size: 36px;
            color: #32bcad;
            margin-bottom: 12px;
            display: inline-block;
        }
        h1 {
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
        }
        .establishment {
            font-size: 14px;
            color: #32bcad;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }
        .amount-tag {
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 24px;
        }
        .qrcode-container {
            background: white;
            padding: 16px;
            border-radius: 16px;
            display: inline-block;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        }
        #qrcode img {
            margin: 0 auto;
        }
        .btn-action {
            width: 100%;
            background: #32bcad;
            border: none;
            border-radius: 12px;
            padding: 14px;
            color: #04080e;
            font-family: 'Outfit', sans-serif;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(50, 188, 173, 0.25);
        }
        .btn-action:hover {
            background: #43cfc0;
            transform: translateY(-1px);
        }
        .btn-action:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .btn-action.copied {
            background: #10b981;
            color: white;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }
        .btn-secondary {
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px;
            color: #a1a1aa;
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        .input-group {
            text-align: left;
            margin-bottom: 24px;
        }
        .input-group label {
            display: block;
            font-size: 14px;
            color: #a1a1aa;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .input-wrapper {
            position: relative;
        }
        .input-wrapper span {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: #a1a1aa;
            font-size: 18px;
            font-weight: 600;
        }
        .input-wrapper input {
            width: 100%;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 14px 16px 14px 44px;
            color: white;
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 700;
            transition: all 0.2s ease;
        }
        .input-wrapper input:focus {
            outline: none;
            border-color: #32bcad;
            background: rgba(255, 255, 255, 0.06);
            box-shadow: 0 0 12px rgba(50, 188, 173, 0.2);
        }
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <div class="card" id="payment-card">
        <div class="pix-header">
            <span class="pix-icon"><i class="fa-brands fa-pix"></i></span>
            <h1>Pagamento via Pix</h1>
            <div class="establishment" id="merchant-name">__MERCHANT_NAME__</div>
        </div>

        __CONTENT_HTML__
    </div>

    <script>
        function copyToClipboard(text, btn) {
            const tempInput = document.createElement("textarea");
            tempInput.value = text;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand("copy");
            document.body.removeChild(tempInput);

            const originalHTML = btn.innerHTML;
            btn.classList.add("copied");
            btn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Código Copiado!`;
            setTimeout(() => {
                btn.classList.remove("copied");
                btn.innerHTML = originalHTML;
            }, 2000);
        }
    </script>
</body>
</html>
"""

def render_pix_page(id_placa: int, nome_estabelecimento: str, tipo_valor: str, valor_fixo: Optional[float] = None, pix_string: Optional[str] = None) -> HTMLResponse:
    """Gera a página de pagamentos via Pix com design premium."""

    if tipo_valor == "fixo":
        valor_formatado = f"{valor_fixo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        content_html = f"""
        <div class="amount-tag">R$ {valor_formatado}</div>
        <div class="qrcode-container">
            <div id="qrcode"></div>
        </div>
        <button class="btn-action" onclick="copyToClipboard('{pix_string}', this)">
            <i class="fa-solid fa-copy"></i> Pix Copia e Cola
        </button>
        <script>
            new QRCode(document.getElementById("qrcode"), {{
                text: '{pix_string}',
                width: 180,
                height: 180,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.M
            }});
        </script>
        """
    else:
        content_html = """
        <div id="value-input-section">
            <p style="color: #a1a1aa; font-size: 14px; margin-bottom: 24px; line-height: 1.5;">
                Digite o valor informado pelo atendente para gerar o seu QR Code de pagamento Pix.
            </p>
            <form id="value-form">
                <div class="input-group">
                    <label for="amount">Valor do Pagamento</label>
                    <div class="input-wrapper">
                        <span>R$</span>
                        <input type="text" id="amount" placeholder="0,00" required autocomplete="off">
                    </div>
                </div>
                <button type="submit" class="btn-action" id="btn-generate">
                    <i class="fa-solid fa-qrcode"></i> Gerar QR Code
                </button>
            </form>
        </div>

        <div id="qrcode-section" class="hidden">
            <div class="amount-tag" id="display-amount">R$ 0,00</div>
            <div class="qrcode-container">
                <div id="qrcode"></div>
            </div>
            <button class="btn-action" id="btn-copy">
                <i class="fa-solid fa-copy"></i> Pix Copia e Cola
            </button>
            <button class="btn-secondary" id="btn-edit">
                <i class="fa-solid fa-pen"></i> Alterar Valor
            </button>
        </div>

        <script>
            const amountInput = document.getElementById("amount");
            const valueForm = document.getElementById("value-form");
            const inputSection = document.getElementById("value-input-section");
            const qrcodeSection = document.getElementById("qrcode-section");
            const displayAmount = document.getElementById("display-amount");
            const btnCopy = document.getElementById("btn-copy");
            const btnEdit = document.getElementById("btn-edit");
            const btnGenerate = document.getElementById("btn-generate");

            let qrInstance = null;
            let currentPixString = "";

            // Mascara de moeda R$ 0,00
            amountInput.addEventListener("input", (e) => {
                let value = e.target.value.replace(/\\D/g, "");
                if (value === "") {
                    e.target.value = "";
                    return;
                }
                value = (parseFloat(value) / 100).toFixed(2);
                e.target.value = value.replace(".", ",").replace(/(\\d)(?=(\\d{3})+(?!\\d))/g, "$1.");
            });

            // Envio do formulario
            valueForm.addEventListener("submit", async (e) => {
                e.preventDefault();

                const cleanVal = amountInput.value.replace(/\\./g, "").replace(",", ".");
                const numericVal = parseFloat(cleanVal);
                if (isNaN(numericVal) || numericVal <= 0) {
                    alert("Por favor, digite um valor maior que zero.");
                    return;
                }

                btnGenerate.disabled = true;
                btnGenerate.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Gerando...`;

                try {
                    const response = await fetch(`/api/public/placa/{id_placa}/gerar-pix`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ valor: numericVal })
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.detail || "Erro ao gerar codigo Pix.");
                    }

                    currentPixString = data.pix_string;

                    // Limpar QR Code anterior se houver
                    document.getElementById("qrcode").innerHTML = "";

                    // Renderizar QR Code
                    qrInstance = new QRCode(document.getElementById("qrcode"), {
                        text: currentPixString,
                        width: 180,
                        height: 180,
                        colorDark : "#000000",
                        colorLight : "#ffffff",
                        correctLevel : QRCode.CorrectLevel.M
                    });

                    displayAmount.textContent = "R$ " + amountInput.value;
                    inputSection.classList.add("hidden");
                    qrcodeSection.classList.remove("hidden");

                } catch (err) {
                    alert(err.message);
                } finally {
                    btnGenerate.disabled = false;
                    btnGenerate.innerHTML = `<i class="fa-solid fa-qrcode"></i> Gerar QR Code`;
                }
            });

            // Copiar codigo Pix
            btnCopy.addEventListener("click", () => {
                copyToClipboard(currentPixString, btnCopy);
            });

            // Voltar para digitar valor
            btnEdit.addEventListener("click", () => {
                qrcodeSection.classList.add("hidden");
                inputSection.classList.remove("hidden");
                amountInput.focus();
            });
        </script>
        """.replace("{id_placa}", str(id_placa))

    html = PIX_TEMPLATE.replace("__MERCHANT_NAME__", nome_estabelecimento).replace("__CONTENT_HTML__", content_html)
    return HTMLResponse(content=html, status_code=200)

class PixGenerateRequest(BaseModel):
    valor: float

# ==================== ROTAS DE REDIRECIONAMENTO PÚBLICAS ====================

def placa_code(id_placa: int) -> str:
    """Código visual ODS-XXXX exibido no verso da placa e no painel."""
    return f"ODS-{id_placa:04d}"

@app.get("/r/{id_placa}/frente")
def redirect_frente(id_placa: int, db: Session = Depends(get_db)):
    """Registra o clique e redireciona para o link da Frente (Google Maps/Avaliação)"""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        return render_error_page("Dispositivo não encontrado", f"O dispositivo {placa_code(id_placa)} não está cadastrado em nosso sistema.")

    if not placa.status_ativa:
        return render_blocked_page(id_placa)

    if not placa.link_frente or placa.link_frente.strip() == "":
        return render_error_page("Link não configurado", "O estabelecimento ainda não cadastrou o link da avaliação do Google para este dispositivo.")

    # Registrar Clique
    clique = HistoricoClique(id_placa=id_placa, lado="Frente")
    db.add(clique)
    db.commit()

    return RedirectResponse(url=placa.link_frente, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.get("/r/{id_placa}/verso")
def redirect_verso(id_placa: int, db: Session = Depends(get_db)):
    """Registra o clique e exibe a tela de pagamento Pix ou redireciona para o link do Verso (Cardápio)."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        return render_error_page("Dispositivo não encontrado", f"O dispositivo {placa_code(id_placa)} não está cadastrado em nosso sistema.")

    if not placa.status_ativa:
        return render_blocked_page(id_placa)

    # Se o dispositivo possui configuração de Pix Local ativa
    if placa.pix_chave and placa.pix_chave.strip() != "":
        # Registrar Clique
        clique = HistoricoClique(id_placa=id_placa, lado="Verso")
        db.add(clique)
        db.commit()

        if placa.pix_tipo_valor == "fixo":
            valor = float(placa.pix_valor_fixo or 0.0)
            pix_str = generate_pix_string(placa.pix_chave, valor, placa.dono.nome_estabelecimento)
            return render_pix_page(id_placa, placa.dono.nome_estabelecimento, "fixo", valor, pix_str)
        else:
            return render_pix_page(id_placa, placa.dono.nome_estabelecimento, "aberto")

    # Caso contrário, fallback para redirecionamento normal para link_verso
    if not placa.link_verso or placa.link_verso.strip() == "":
        return render_error_page("Link não configurado", "O estabelecimento ainda não cadastrou o link do cardápio ou Pix para este dispositivo.")

    # Registrar Clique
    clique = HistoricoClique(id_placa=id_placa, lado="Verso")
    db.add(clique)
    db.commit()

    return RedirectResponse(url=placa.link_verso, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# --- ALIAS COMPATÍVEIS ---
@app.get("/placa/{id_placa}/frente")
def redirect_frente_alias(id_placa: int, db: Session = Depends(get_db)):
    """Alias para a rota da Frente."""
    return redirect_frente(id_placa, db)

@app.get("/placa/{id_placa}/verso")
def redirect_verso_alias(id_placa: int, db: Session = Depends(get_db)):
    """Alias para a rota do Verso (com suporte a Pix e redirecionamento)."""
    return redirect_verso(id_placa, db)

# --- ENDPOINT PÚBLICO PIX ---
@app.post("/api/public/placa/{id_placa}/gerar-pix")
def api_gerar_pix(id_placa: int, payload: PixGenerateRequest, db: Session = Depends(get_db)):
    """Gera o Pix BR Code dinamicamente para valores variáveis (aberto)."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado."
        )
    if not placa.status_ativa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este dispositivo está suspenso e temporariamente inativo."
        )

    if not placa.pix_chave or placa.pix_chave.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este dispositivo não está configurado para pagamentos Pix."
        )

    if placa.pix_tipo_valor != "aberto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este dispositivo exige um valor fixo pré-configurado."
        )

    if payload.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor do Pix deve ser maior que zero."
        )

    pix_str = generate_pix_string(placa.pix_chave, payload.valor, placa.dono.nome_estabelecimento)
    return {"pix_string": pix_str}

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.post("/api/auth/login", response_model=Token)
def login(request_data: LoginRequest, db: Session = Depends(get_db)):
    """Valida o login do usuário (Documento + Senha) e gera o token JWT."""
    superadmin_documento = os.getenv("SUPERADMIN_DOCUMENTO")
    superadmin_senha = os.getenv("SUPERADMIN_SENHA")

    if (
        superadmin_documento
        and superadmin_senha
        and request_data.documento == superadmin_documento
        and request_data.senha == superadmin_senha
    ):
        admin_user = db.query(Usuario).filter(Usuario.is_admin == True).first()
        if not admin_user:
            admin_user = Usuario(
                documento=superadmin_documento,
                senha=get_password_hash(superadmin_senha),
                nome_estabelecimento="Administrador do Sistema",
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        usuario = admin_user
    else:
        usuario = db.query(Usuario).filter(Usuario.documento == request_data.documento).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Documento ou senha inválidos."
            )

        # Valida senha
        if not verify_password(request_data.senha, usuario.senha):
            # Caso especial para o seed que usa bcrypt e teste com hash padrão do backend
            # Se for o usuário seed e a senha for "senha123", deixamos passar se o hash bater
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Documento ou senha inválidos."
            )

        if not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cliente inativo. Entre em contato com o suporte."
            )

    # Cria token
    access_token = create_access_token(data={"sub": usuario.documento})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "nome_estabelecimento": usuario.nome_estabelecimento,
        "is_admin": bool(getattr(usuario, "is_admin", False))
    }

# Rota auxiliar para registro de novos comerciantes (útil para testes e expansão futura)
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(request_data: LoginRequest, nome_estabelecimento: str, db: Session = Depends(get_db)):
    """Cria um novo usuário/estabelecimento com senha hashada."""
    usuario_existente = db.query(Usuario).filter(Usuario.documento == request_data.documento).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este documento já está cadastrado."
        )

    hashed_pwd = get_password_hash(request_data.senha)
    novo_usuario = Usuario(
        documento=request_data.documento,
        senha=hashed_pwd,
        nome_estabelecimento=nome_estabelecimento
    )
    db.add(novo_usuario)
    db.commit()
    return {"message": f"Estabelecimento '{nome_estabelecimento}' cadastrado com sucesso!"}

# ==================== ROTAS ADMINISTRATIVAS PROTEGIDAS ====================

@app.get("/api/admin/placas", response_model=List[PlacaResponse])
def listar_placas(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna todos os dispositivos associados ao comerciante logado."""
    placas = db.query(Placa).filter(Placa.dono_documento == current_user.documento).order_by(Placa.id_placa).all()
    return placas

@app.put("/api/admin/placas/{id_placa}", response_model=PlacaResponse)
def atualizar_placa(id_placa: int, payload: PlacaUpdate, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualiza as configurações operacionais, links e Pix de um dispositivo do comerciante logado."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa, Placa.dono_documento == current_user.documento).first()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado ou não pertence ao seu estabelecimento."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(placa, field, value)

    db.commit()
    db.refresh(placa)
    return placa

@app.get("/api/admin/dashboard", response_model=DashboardStats)
def obter_dados_dashboard(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna estatísticas compiladas de cliques dos dispositivos do comerciante logado nos últimos 7 dias."""

    # 1. Obter IDs dos dispositivos do usuário
    placas = db.query(Placa).filter(Placa.dono_documento == current_user.documento).all()
    plate_ids = [p.id_placa for p in placas]

    if not plate_ids:
        return {
            "total_placas": 0,
            "total_cliques": 0,
            "cliques_hoje": 0,
            "frente_cliques": 0,
            "verso_cliques": 0,
            "historico_cliques_diarios": [],
            "placas_stats": []
        }

    # 2. Contagens Totais
    total_placas = len(plate_ids)

    total_cliques = db.query(HistoricoClique).filter(
        HistoricoClique.id_placa.in_(plate_ids)
    ).count()

    inicio_hoje = datetime.combine(date.today(), datetime.min.time())
    cliques_hoje = db.query(HistoricoClique).filter(
        HistoricoClique.id_placa.in_(plate_ids),
        HistoricoClique.data_hora >= inicio_hoje
    ).count()

    frente_cliques = db.query(HistoricoClique).filter(
        HistoricoClique.id_placa.in_(plate_ids),
        HistoricoClique.lado == "Frente"
    ).count()

    verso_cliques = db.query(HistoricoClique).filter(
        HistoricoClique.id_placa.in_(plate_ids),
        HistoricoClique.lado == "Verso"
    ).count()

    placas_stats = []
    for placa_id in plate_ids:
        placa_frente = db.query(HistoricoClique).filter(
            HistoricoClique.id_placa == placa_id,
            HistoricoClique.lado == "Frente"
        ).count()
        placa_verso = db.query(HistoricoClique).filter(
            HistoricoClique.id_placa == placa_id,
            HistoricoClique.lado == "Verso"
        ).count()
        placas_stats.append(
            PlateStats(
                id_placa=placa_id,
                frente_cliques=placa_frente,
                verso_cliques=placa_verso,
                total_cliques=placa_frente + placa_verso
            )
        )

    # 3. Estatísticas diárias (Últimos 7 dias)
    hoje_data = date.today()
    dados_diarios = {}

    # Inicializa os últimos 7 dias com contagens zeradas para garantir o preenchimento do gráfico
    for i in range(6, -1, -1):
        d = hoje_data - timedelta(days=i)
        dados_diarios[d.isoformat()] = {"frente": 0, "verso": 0}

    sete_dias_atras = datetime.combine(hoje_data - timedelta(days=6), datetime.min.time())

    # Buscar cliques ocorridos nos últimos 7 dias
    cliques_recentes = db.query(HistoricoClique).filter(
        HistoricoClique.id_placa.in_(plate_ids),
        HistoricoClique.data_hora >= sete_dias_atras
    ).all()

    for c in cliques_recentes:
        # Formata o timestamp do clique para a data YYYY-MM-DD
        data_str = c.data_hora.date().isoformat()
        if data_str in dados_diarios:
            if c.lado == "Frente":
                dados_diarios[data_str]["frente"] += 1
            elif c.lado == "Verso":
                dados_diarios[data_str]["verso"] += 1

    # Transforma o dict em lista ordenada
    historico_cliques_diarios = []
    for data_str, contagens in sorted(dados_diarios.items()):
        historico_cliques_diarios.append(
            ClickDaily(
                data=data_str,
                frente=contagens["frente"],
                verso=contagens["verso"]
            )
        )

    return DashboardStats(
        total_placas=total_placas,
        total_cliques=total_cliques,
        cliques_hoje=cliques_hoje,
        frente_cliques=frente_cliques,
        verso_cliques=verso_cliques,
        historico_cliques_diarios=historico_cliques_diarios,
        placas_stats=placas_stats
    )

# ==================== ROTAS EXCLUSIVAS DO SUPERADMIN ====================

@app.get("/api/admin/super/comerciantes", response_model=List[ComercianteResponse])
def super_listar_comerciantes(current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista todos os comerciantes (usuários comuns) e seus respectivos dispositivos."""
    comerciantes = db.query(Usuario).filter(Usuario.is_admin == False).order_by(Usuario.nome_estabelecimento).all()
    return comerciantes

@app.put("/api/admin/super/comerciantes/{documento}/status")
def super_alterar_status_comerciante(documento: str, payload: ClienteStatusUpdate, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Ativa ou inativa o acesso ao painel de um comerciante (as placas continuam funcionando)."""
    comerciante = db.query(Usuario).filter(Usuario.documento == documento).first()
    if not comerciante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comerciante não encontrado."
        )
    if comerciante.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível inativar um administrador."
        )

    comerciante.ativo = payload.ativo
    db.commit()
    db.refresh(comerciante)
    return comerciante

@app.post("/api/admin/super/comerciantes", status_code=status.HTTP_201_CREATED)
def super_criar_comerciante(payload: ComercianteCreate, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Cadastra um novo comerciante e vincula opcionalmente um dispositivo físico inicial."""
    usuario_existente = db.query(Usuario).filter(Usuario.documento == payload.documento).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este documento."
        )

    # Cria novo comerciante
    novo_usuario = Usuario(
        documento=payload.documento,
        senha=get_password_hash(payload.senha),
        nome_estabelecimento=payload.nome_estabelecimento,
        is_admin=False
    )
    db.add(novo_usuario)
    db.flush()  # Para permitir associação imediata do dispositivo

    # Se um dispositivo físico inicial foi informado, tenta vinculá-lo
    if payload.id_placa is not None:
        placa_existente = db.query(Placa).filter(Placa.id_placa == payload.id_placa).first()
        if placa_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O dispositivo {payload.id_placa} já está vinculado ao documento {placa_existente.dono_documento}."
            )

        nova_placa = Placa(
            id_placa=payload.id_placa,
            dono_documento=payload.documento,
            nome_exibicao=None,
            tipo_dispositivo=payload.tipo_dispositivo,
            local_uso=None,
            loja_unidade=None,
            responsavel=None,
            observacao=None,
            link_frente=None,
            link_verso=None,
            pix_chave=None,
            pix_tipo_valor=None,
            pix_valor_fixo=None,
            status_ativa=True
        )
        db.add(nova_placa)

    db.commit()
    if payload.id_placa is not None:
        return {"detail": "Comerciante cadastrado e dispositivo vinculado com sucesso. O comerciante poderá personalizar nome, local, loja, responsável e destinos pelo painel dele."}
    return {"detail": "Comerciante cadastrado com sucesso. Vincule dispositivos físicos quando necessário."}

@app.post("/api/admin/super/placas", response_model=PlacaResponse, status_code=status.HTTP_201_CREATED)
def super_vincular_placa(payload: PlacaVinculo, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Vincula um dispositivo físico novo a um comerciante existente."""
    comerciante = db.query(Usuario).filter(Usuario.documento == payload.dono_documento).first()
    if not comerciante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comerciante não encontrado com o documento informado."
        )

    placa_existente = db.query(Placa).filter(Placa.id_placa == payload.id_placa).first()
    if placa_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O dispositivo {payload.id_placa} já está vinculado ao documento {placa_existente.dono_documento}."
        )

    nova_placa = Placa(
        id_placa=payload.id_placa,
        dono_documento=payload.dono_documento,
        nome_exibicao=None,
        tipo_dispositivo=payload.tipo_dispositivo,
        local_uso=None,
        loja_unidade=None,
        responsavel=None,
        observacao=None,
        link_frente=None,
        link_verso=None,
        pix_chave=None,
        pix_tipo_valor=None,
        pix_valor_fixo=None,
        status_ativa=True
    )
    db.add(nova_placa)
    db.commit()
    db.refresh(nova_placa)
    return nova_placa

@app.put("/api/admin/super/placas/{id_placa}/status", response_model=PlacaResponse)
def super_alterar_status_placa(id_placa: int, payload: PlacaStatusUpdate, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Ativa ou suspende o funcionamento de um dispositivo."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado."
        )

    placa.status_ativa = payload.status_ativa
    db.commit()
    db.refresh(placa)
    return placa

@app.delete("/api/admin/super/placas/{id_placa}", status_code=status.HTTP_204_NO_CONTENT)
def super_excluir_placa(id_placa: int, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Remove qualquer dispositivo do sistema e todo o histórico de cliques."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado."
        )

    db.delete(placa)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.put("/api/admin/super/placas/{id_placa}", response_model=PlacaResponse)
def super_atualizar_placa(id_placa: int, payload: PlacaUpdate, current_admin: Usuario = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Permite ao superadministrador editar as configurações de qualquer dispositivo."""
    placa = db.query(Placa).filter(Placa.id_placa == id_placa).first()
    if not placa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(placa, field, value)

    db.commit()
    db.refresh(placa)
    return placa

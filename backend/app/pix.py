import unicodedata

def normalize_text(text: str) -> str:
    """Remove acentos, caracteres especiais e deixa o texto em letras maiúsculas."""
    if not text:
        return ""
    # Remove acentuação
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_bytes = nfkd.encode('ASCII', 'ignore')
    ascii_str = ascii_bytes.decode('utf-8')
    # Mantém apenas letras, números e espaços
    clean = "".join(c for c in ascii_str if c.isalnum() or c == ' ')
    return clean.upper()

def format_emv(tag: str, value: str) -> str:
    """Formata um bloco EMV no padrão Tag-Length-Value (TLV)."""
    return f"{tag}{len(value):02d}{value}"

def generate_pix_string(chave: str, valor: float, nome_recebedor: str, cidade_recebedor: str = "SAO PAULO") -> str:
    """Gera a string Pix estática no padrão BR Code (EMV Co) para Pix Copia e Cola."""

    # 00: Payload Format Indicator (Sempre "01")
    parts = [format_emv("00", "01")]

    # 26: Merchant Account Information (Dados do Pix)
    # Sub-tag 00: GUI (br.gov.bcb.pix)
    # Sub-tag 01: Chave Pix
    gui = format_emv("00", "br.gov.bcb.pix")
    key = format_emv("01", chave)
    parts.append(format_emv("26", f"{gui}{key}"))

    # 52: Merchant Category Code (Sempre "0000" para transações comerciais genéricas)
    parts.append(format_emv("52", "0000"))

    # 53: Transaction Currency (986 para Real - BRL)
    parts.append(format_emv("53", "986"))

    # 54: Transaction Amount (Valor, opcional se for aberto)
    if valor and valor > 0:
        valor_str = f"{valor:.2f}"
        parts.append(format_emv("54", valor_str))

    # 58: Country Code (Sempre "BR")
    parts.append(format_emv("58", "BR"))

    # 59: Merchant Name (Nome do recebedor, max 25 caracteres, limpo e em maiúsculas)
    nome_norm = normalize_text(nome_recebedor)[:25].strip()
    if not nome_norm:
        nome_norm = "ESTABELECIMENTO"
    parts.append(format_emv("59", nome_norm))

    # 60: Merchant City (Cidade do recebedor, max 15 caracteres, limpo e em maiúsculas)
    cidade_norm = normalize_text(cidade_recebedor)[:15].strip()
    if not cidade_norm:
        cidade_norm = "SAO PAULO"
    parts.append(format_emv("60", cidade_norm))

    # 62: Additional Data Field (Reference Label para identificador, usando padrão "***")
    parts.append(format_emv("62", format_emv("05", "***")))

    # 63: CRC16 (Sempre o último campo, seu valor é o hash do payload anterior)
    parts.append("6304")

    payload = "".join(parts)

    # Cálculo do CRC16-CCITT (Polinômio 0x1021, valor inicial 0xFFFF)
    crc = 0xFFFF
    for char in payload:
        crc ^= (ord(char) << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF

    crc_hex = f"{crc:04X}"
    return f"{payload}{crc_hex}"

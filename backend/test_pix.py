import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import unittest
from app.pix import normalize_text, format_emv, generate_pix_string

class TestPixGenerator(unittest.TestCase):
    def test_normalize_text(self):
        # Test cleaning special characters and accents
        self.assertEqual(normalize_text("Barbearia do João!"), "BARBEARIA DO JOAO")
        self.assertEqual(normalize_text("Açúcar & Café"), "ACUCAR  CAFE")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_format_emv(self):
        # Test TLV formatting
        self.assertEqual(format_emv("00", "01"), "000201")
        self.assertEqual(format_emv("26", "test"), "2604test")

    def test_generate_pix_string_without_amount(self):
        # Test static Pix without fixed value
        pix_str = generate_pix_string(
            chave="pix@loja.com",
            valor=0.0,
            nome_recebedor="Barbearia do João",
            cidade_recebedor="São Paulo"
        )
        self.assertTrue(pix_str.startswith("000201"))
        # Verify it has merchant details
        self.assertIn("26340014br.gov.bcb.pix0112pix@loja.com", pix_str)
        # Verify country, name and city
        self.assertIn("5802BR", pix_str)
        self.assertIn("5917BARBEARIA DO JOAO", pix_str)
        self.assertIn("6009SAO PAULO", pix_str)
        # Verify 62070503*** is in there
        self.assertIn("62070503***", pix_str)
        # Verify ending CRC tag
        self.assertIn("6304", pix_str)
        # Check overall length of CRC suffix
        self.assertEqual(len(pix_str) - pix_str.find("6304"), 8)

    def test_generate_pix_string_with_amount(self):
        # Test static Pix with fixed value
        pix_str = generate_pix_string(
            chave="12345678909",
            valor=45.90,
            nome_recebedor="Café do Centro",
            cidade_recebedor="Belo Horizonte"
        )
        self.assertTrue(pix_str.startswith("000201"))
        # Verify merchant account info
        self.assertIn("26330014br.gov.bcb.pix011112345678909", pix_str)
        # Verify amount field is present
        self.assertIn("540545.90", pix_str)
        # Verify name and city
        self.assertIn("5914CAFE DO CENTRO", pix_str)
        self.assertIn("6014BELO HORIZONTE", pix_str)
        # Verify ending CRC tag
        self.assertIn("6304", pix_str)

if __name__ == "__main__":
    unittest.main()

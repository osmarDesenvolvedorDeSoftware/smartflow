import sys
import os
import unittest
import requests

class TestNfcConnectIntegration(unittest.TestCase):
    BASE_URL = "http://localhost"  # Call Nginx on port 80

    def setUp(self):
        self.doc = "12345678901"
        self.pwd = "senha123"
        self.plate_id = 1001

        # Reset plate 1001 configuration to clean state before test starts
        import subprocess
        res = subprocess.run([
            "docker", "exec", "nfc_db", "psql", "-U", "postgres", "-d", "plaquinhas", "-c",
            "UPDATE placas SET link_verso = 'https://cardapio.example.com/pedro', pix_chave = NULL, pix_tipo_valor = NULL, pix_valor_fixo = NULL WHERE id_placa = 1001;"
        ], capture_output=True, text=True)

    def test_end_to_end_flow(self):
        # 1. Test fallback redirection when no Pix is configured (Plate 1001 should redirect to its configured link)
        print("Testing fallback redirect...")
        r_redirect = requests.get(f"{self.BASE_URL}/r/{self.plate_id}/verso", allow_redirects=False)
        self.assertEqual(r_redirect.status_code, 307)
        original_link_verso = r_redirect.headers["Location"]
        print(f"Original fallback redirect URL: {original_link_verso}")

        # 2. Login to get token
        print("Testing login...")
        r_login = requests.post(f"{self.BASE_URL}/api/auth/login", json={
            "documento": self.doc,
            "senha": self.pwd
        })
        self.assertEqual(r_login.status_code, 200)
        token_data = r_login.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Update plate to use Pix with fixed value
        print("Configuring plate with fixed Pix amount...")
        r_update = requests.put(f"{self.BASE_URL}/api/admin/placas/{self.plate_id}", headers=headers, json={
            "link_frente": "https://goo.gl/maps/example1",
            "link_verso": None,
            "pix_chave": "pix@barbearia.com",
            "pix_tipo_valor": "fixo",
            "pix_valor_fixo": 35.00
        })
        self.assertEqual(r_update.status_code, 200)
        updated_data = r_update.json()
        self.assertEqual(updated_data["pix_chave"], "pix@barbearia.com")
        self.assertEqual(updated_data["pix_tipo_valor"], "fixo")
        self.assertEqual(float(updated_data["pix_valor_fixo"]), 35.00)

        # 4. Test redirection / rendering now that Pix is configured with fixed value
        print("Testing render_pix_page for fixed amount...")
        r_pix_page = requests.get(f"{self.BASE_URL}/r/{self.plate_id}/verso")
        self.assertEqual(r_pix_page.status_code, 200)
        self.assertIn("pix@barbearia.com", r_pix_page.text)
        self.assertIn("35,00", r_pix_page.text)  # Should show formatted price
        self.assertIn("6304", r_pix_page.text)     # Should contain EMV BR Code

        # 5. Check if generating variable-value Pix fails when mode is 'fixo'
        print("Testing dynamic Pix block on fixed amount...")
        r_gen_fail = requests.post(f"{self.BASE_URL}/api/public/placa/{self.plate_id}/gerar-pix", json={"valor": 50.00})
        self.assertEqual(r_gen_fail.status_code, 400)
        self.assertIn("exige um valor fixo", r_gen_fail.json()["detail"])

        # 6. Update plate to use Pix with variable value (aberto)
        print("Configuring plate with variable (aberto) Pix...")
        r_update2 = requests.put(f"{self.BASE_URL}/api/admin/placas/{self.plate_id}", headers=headers, json={
            "link_frente": "https://goo.gl/maps/example1",
            "link_verso": None,
            "pix_chave": "12345678909",
            "pix_tipo_valor": "aberto",
            "pix_valor_fixo": None
        })
        self.assertEqual(r_update2.status_code, 200)
        updated_data2 = r_update2.json()
        self.assertEqual(updated_data2["pix_chave"], "12345678909")
        self.assertEqual(updated_data2["pix_tipo_valor"], "aberto")
        self.assertIsNone(updated_data2["pix_valor_fixo"])

        # 7. Access /r/{id}/verso (should show form to enter amount)
        print("Testing render_pix_page for variable/open amount...")
        r_pix_page2 = requests.get(f"{self.BASE_URL}/r/{self.plate_id}/verso")
        self.assertEqual(r_pix_page2.status_code, 200)
        self.assertIn("Digite o valor", r_pix_page2.text)

        # 8. Post value to generate dynamic Pix
        print("Generating dynamic Pix string...")
        r_gen_success = requests.post(f"{self.BASE_URL}/api/public/placa/{self.plate_id}/gerar-pix", json={"valor": 12.50})
        self.assertEqual(r_gen_success.status_code, 200)
        gen_data = r_gen_success.json()
        self.assertIn("pix_string", gen_data)
        # Should have correct amount in EMV tags (540512.50)
        self.assertIn("540512.50", gen_data["pix_string"])

        # 9. Clean up and restore original configuration
        print("Cleaning up plate configuration...")
        r_cleanup = requests.put(f"{self.BASE_URL}/api/admin/placas/{self.plate_id}", headers=headers, json={
            "link_frente": "https://goo.gl/maps/example1",
            "link_verso": original_link_verso,
            "pix_chave": None,
            "pix_tipo_valor": None,
            "pix_valor_fixo": None
        })
        self.assertEqual(r_cleanup.status_code, 200)
        cleanup_data = r_cleanup.json()
        self.assertIsNone(cleanup_data["pix_chave"])
        self.assertIsNone(cleanup_data["pix_tipo_valor"])
        self.assertIsNone(cleanup_data["pix_valor_fixo"])
        self.assertEqual(cleanup_data["link_verso"], original_link_verso)
        print("Integration tests completed successfully!")

    def test_superadmin_and_suspension_flow(self):
        print("Testing SuperAdmin login...")
        r_login = requests.post(f"{self.BASE_URL}/api/auth/login", json={
            "documento": "00000000000",
            "senha": "senha123"
        })
        self.assertEqual(r_login.status_code, 200)
        token_data = r_login.json()
        self.assertTrue(token_data["is_admin"])
        admin_token = token_data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # List merchants
        print("Listing merchants...")
        r_merchants = requests.get(f"{self.BASE_URL}/api/admin/super/comerciantes", headers=admin_headers)
        self.assertEqual(r_merchants.status_code, 200)
        merchants = r_merchants.json()
        self.assertTrue(len(merchants) > 0)
        merchant_docs = [m["documento"] for m in merchants]
        self.assertIn("12345678901", merchant_docs)

        # Suspend plate 1001
        print("Suspending plate 1001...")
        r_suspend = requests.put(f"{self.BASE_URL}/api/admin/super/placas/1001/status", headers=admin_headers, json={
            "status_ativa": False
        })
        self.assertEqual(r_suspend.status_code, 200)
        self.assertFalse(r_suspend.json()["status_ativa"])

        # Access suspended plate (Frente)
        print("Accessing suspended plate (Frente)...")
        r_frente = requests.get(f"{self.BASE_URL}/r/1001/frente")
        self.assertEqual(r_frente.status_code, 200)
        self.assertIn("Dispositivo Suspenso", r_frente.text)

        # Access suspended plate (Verso)
        print("Accessing suspended plate (Verso)...")
        r_verso = requests.get(f"{self.BASE_URL}/r/1001/verso")
        self.assertEqual(r_verso.status_code, 200)
        self.assertIn("Dispositivo Suspenso", r_verso.text)

        # Generating Pix on suspended plate should fail
        print("Generating Pix on suspended plate...")
        r_gen = requests.post(f"{self.BASE_URL}/api/public/placa/1001/gerar-pix", json={"valor": 10.00})
        self.assertEqual(r_gen.status_code, 403)
        self.assertIn("suspensa", r_gen.json()["detail"])

        # Reactive plate 1001
        print("Reactivating plate 1001...")
        r_activate = requests.put(f"{self.BASE_URL}/api/admin/super/placas/1001/status", headers=admin_headers, json={
            "status_ativa": True
        })
        self.assertEqual(r_activate.status_code, 200)
        self.assertTrue(r_activate.json()["status_ativa"])

        # Access plate after reactivation (should be allowed now)
        print("Accessing reactivated plate...")
        r_verso_ok = requests.get(f"{self.BASE_URL}/r/1001/verso", allow_redirects=False)
        self.assertNotEqual(r_verso_ok.status_code, 403)
        self.assertNotIn("Dispositivo Suspenso", r_verso_ok.text)

        # Create new merchant manually
        print("Creating new merchant manually...")
        new_merchant_doc = "98765432100"
        r_create = requests.post(f"{self.BASE_URL}/api/admin/super/comerciantes", headers=admin_headers, json={
            "documento": new_merchant_doc,
            "senha": "testpassword",
            "nome_estabelecimento": "Loja Teste SuperAdmin",
            "id_placa": 9999
        })
        self.assertEqual(r_create.status_code, 201)

        # Verify created merchant has plate 9999
        r_merchants2 = requests.get(f"{self.BASE_URL}/api/admin/super/comerciantes", headers=admin_headers)
        merchants2 = r_merchants2.json()
        created_merchant = next((m for m in merchants2 if m["documento"] == new_merchant_doc), None)
        self.assertIsNotNone(created_merchant)
        self.assertEqual(created_merchant["nome_estabelecimento"], "Loja Teste SuperAdmin")
        self.assertEqual(len(created_merchant["placas"]), 1)
        self.assertEqual(created_merchant["placas"][0]["id_placa"], 9999)

        # Cleanup: Delete the created test merchant (and cascade plate 9999)
        print("Cleaning up test merchant...")
        import subprocess
        subprocess.run([
            "docker", "exec", "nfc_db", "psql", "-U", "postgres", "-d", "plaquinhas", "-c",
            f"DELETE FROM usuarios WHERE documento = '{new_merchant_doc}';"
        ], capture_output=True, text=True)
        print("SuperAdmin integration test passed successfully!")

if __name__ == "__main__":
    unittest.main()

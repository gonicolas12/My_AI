"""
Tests unitaires pour les outils locaux (math, recherche, extraction d'infos).
"""
import unittest
from tools import local_tools

class TestLocalTools(unittest.TestCase):
    def test_local_math(self):
        self.assertEqual(local_tools.local_math("2+2"), 4)
        self.assertTrue("Erreur" in str(local_tools.local_math("2/0")))

    def test_local_search(self):
        # Suppose qu'il y a toujours ce fichier
        results = local_tools.local_search("*.py", folder="tools")
        self.assertTrue(any("local_tools.py" in r for r in results))

    def test_extract_emails(self):
        text = "Contact: test@example.com, autre@mail.fr"
        emails = local_tools.extract_emails(text)
        self.assertIn("test@example.com", emails)
        self.assertIn("autre@mail.fr", emails)

    def test_extract_dates(self):
        text = "Rendez-vous le 25/07/2025 ou le 2025-07-25."
        dates = local_tools.extract_dates(text)
        self.assertIn("25/07/2025", dates)
        self.assertIn("2025-07-25", dates)

if __name__ == "__main__":
    unittest.main()

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_lister_livres():
    reponse = client.get("/livres")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 3


def test_ajouter_livre():
    livre = {"id": 4, "titre": "Neuromancien", "auteur": "William Gibson"}
    assert client.post("/livres", json=livre).status_code == 201


def test_livre_en_double():
    livre = {"id": 1, "titre": "Dune", "auteur": "Frank Herbert"}
    assert client.post("/livres", json=livre).status_code == 409

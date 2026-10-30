from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Bibliothèque")


class Livre(BaseModel):
    id: int
    titre: str
    auteur: str


LIVRES: dict[int, Livre] = {
    1: Livre(id=1, titre="Dune", auteur="Frank Herbert"),
    2: Livre(id=2, titre="Fondation", auteur="Isaac Asimov"),
    3: Livre(id=3, titre="Hypérion", auteur="Dan Simmons"),
}


@app.get("/livres")
def lister_livres() -> list[Livre]:
    return list(LIVRES.values())


@app.post("/livres", status_code=201)
def ajouter_livre(livre: Livre) -> Livre:
    if livre.id in LIVRES:
        raise HTTPException(status_code=409, detail="Ce livre existe déjà")
    LIVRES[livre.id] = livre
    return livre

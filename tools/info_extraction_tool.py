"""
Outil d'extraction d'informations structurées depuis un texte
"""
def extract_emails(text: str) -> list:
    import re
    return re.findall(r"[\w\.-]+@[\w\.-]+", text)

def extract_dates(text: str) -> list:
    import re
    return re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text)

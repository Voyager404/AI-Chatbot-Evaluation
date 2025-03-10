from sentence_transformers import SentenceTransformer
import json
import psycopg2
import os
import numpy as np

# Embedding-Modell herunterladen
model = SentenceTransformer(
    "jinaai/jina-embeddings-v2-base-de",
    trust_remote_code=True
)
# die Eingabe ist auf 1024 Sequenzen limitiert -> to do Bedeutung sequenz?
model.max_seq_length=1024

# Employee Code aus Umgebungsvariable abrufen
employee_code = os.getenv("EMPLOYEE_CODE", "")

# Rollen-Mapping definieren
employee_roles = {
    "MS": ["Employee"],
    "MM": ["Manager"]
}

# Mitarbeiterrolle abrufen (falls kein Kürzel -> leere Rolle)
employee_role = employee_roles.get(employee_code, [""])

# Prompt/Query wird eingegeben
prompt = input("Prompt eingeben:")

# Falls der Nutzer ein Mitarbeiter ist, "ich" durch das Kürzel ersetzen
if employee_code:
    prompt = prompt.replace(" ich ", f" {employee_code} ")
    prompt = prompt.replace("mein ", f"{employee_code}s ")
    prompt = prompt.replace("meine ", f"{employee_code}s ")
    prompt = prompt.replace("meinen ", f"{employee_code}s ")

# Prompt/Query wird verarbeitet
prompt_embedding = model.encode([
    prompt
])

# Ähnliche Texte aus der Datenbank abfragen
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="mysecretpassword",
    host="localhost",
    port="9000"
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT text, link 
        FROM items
        WHERE role @> ARRAY[%s]::TEXT[]
        ORDER BY embedding <-> %s::vector
        LIMIT 3;
        """, (employee_role, prompt_embedding[0].tolist()))
    
    results = cur.fetchall()
    conn.commit()

if not results:
    print("Keine relevanten Informationen gefunden.")
    results = [{"text": "Ich habe leider keine Informationen zu diesem Thema.", "link": ""}]

with open("prompt_suggestions.json", "w") as f:
    json.dump({
        "prompt": prompt,
        "texts": results  # Speichert als Dictionairies
    }, f)

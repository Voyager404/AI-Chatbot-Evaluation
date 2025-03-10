from sentence_transformers import SentenceTransformer
import psycopg2
import fitz
from nltk.tokenize import sent_tokenize
import os
import unicodedata

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_per_page = [(page.number + 1, page.get_text("text")) for page in doc]
    return text_per_page

# Vektoren und Ursprungstext in eine Tabelle im postgres container schieben

# Verbindung zur Datenbank aufbauen
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="mysecretpassword",
    host="localhost",
    port="9000"
)

# Tabelle mit Vektoren erstellen
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE if not exists items (
            embedding vector,
            text varchar(1024) PRIMARY KEY,
            page_num INTEGER,   
            link VARCHAR(1024),  -- Neue Spalte für externe Links
            role TEXT[],   -- Neue Spalte für Rolle
            pdf_name VARCHAR(255) -- Neue Spalte PDF Datei
        );
    """)
    conn.commit()

# Embedding-Modell herunterladen
model = SentenceTransformer(
    "jinaai/jina-embeddings-v2-base-de",
    trust_remote_code=True
)
# Die Eingabe ist auf 1024 Sequenzen limitiert
model.max_seq_length=1024

# Ordner mit PDFs
pdf_folder = "pdfs"

# Manuelle Zuordnung von externen Links zu bestimmten Themen
link_mapping = {
    "Onboarding": "https://www.icloud.com/iclouddrive/03cE0xtTG-zlvX7joCaUPWelQ",
    "Excel": "https://www.icloud.com/iclouddrive/03cE0xtTG-zlvX7joCaUPWelQ",
}

role_mapping = {
    "EinführungO365.pdf":  ["Employee", "Manager"], # Mehrere Rollen als Array
    "Personalakte_MM.pdf": ["Manager"],
    "Personalakte_MS.pdf": ["Employee", "Manager"]
}

# Alle PDFs im Verzeichnis durchgehen
for pdf_file in os.listdir(pdf_folder):
    if not pdf_file.endswith(".pdf"):
        continue  # Falls keine PDF-Datei, überspringen

    pdf_path = os.path.join(pdf_folder, pdf_file)
    dokument_text_pages = extract_text_from_pdf(pdf_path)

    dokument_sätze = []
    sätze_mit_seiten = []
    for page_num, text in dokument_text_pages:
        sätze = sent_tokenize(text)
        dokument_sätze.extend(sätze)
        sätze_mit_seiten.extend([(s, page_num) for s in sätze])

# Embeddings für jeden Satz erstellen
    dokument_embeddings = model.encode(dokument_sätze)

# Bestimme die Rolle für das gesamte Dokument (nicht pro Satz!)
    assigned_role = ["All"]  # Standardrolle setzen
    for keyword, role in role_mapping.items():
        if keyword.lower() in pdf_file.lower():  # Prüfe auf PDF-Namen, nicht Satzinhalt!
            assigned_role = role
            break  # Falls gefunden, abbrechen

# Bestehende Texte abrufen (für das aktuelle PDF)
    with conn.cursor() as cur: 
        cur.execute("SELECT text FROM items WHERE pdf_name = %s;", (pdf_file,))
        result = cur.fetchall()
        existing_texts = {row[0] for row in result} if result else set()  # Falls leer, setze eine leere Menge

# Neue Einträge sammeln
    new_entries = []
    for (text, page_num), embedding in zip(sätze_mit_seiten, dokument_embeddings):
        related_link = None
        
# Prüfen, ob ein Stichwort aus `link_mapping` im Text vorkommt
        for keyword, url in link_mapping.items():
            if keyword.lower() in text.lower():
                related_link = url
                break

# Prüfen, ob eine Rolle zugewiesen werden kann
        for keyword, role in role_mapping.items():
            if unicodedata.normalize("NFC", keyword.lower()) in unicodedata.normalize("NFC", pdf_file.lower()):
                assigned_role = role
                break

        new_entries.append((embedding.tolist(), text, page_num, related_link, assigned_role, pdf_file))

# Neue Einträge einfügen
    if new_entries:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO items (embedding, text, page_num, link, role, pdf_name)
                VALUES (%s::vector, %s, %s, %s, %s, %s)
                ON CONFLICT (text) DO UPDATE
                SET 
                    embedding = EXCLUDED.embedding,
                    link = COALESCE(EXCLUDED.link, items.link),
                    role = ARRAY(
                    SELECT DISTINCT unnest(
                        COALESCE(items.role, '{}'::text[]) || COALESCE(EXCLUDED.role, '{}'::text[])
                        )
                    ),
                    pdf_name = EXCLUDED.pdf_name;
                """,
                [
                    (embedding, text, page_num, related_link, assigned_role, pdf_file)
                    for (embedding, text, page_num, related_link, assigned_role, pdf_file) in new_entries
                ]
            )
            conn.commit()
            print(f"{len(new_entries)} neue Einträge mit Rolle '{assigned_role}' hinzugefügt.")

# Falls es alte Einträge ohne Rolle gibt, aktualisiere sie
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE items
            SET role = ARRAY(
                SELECT DISTINCT unnest(
                    COALESCE(role, '{}'::text[]) || %s
                )
            )
            WHERE pdf_name = %s;
            """,
            (assigned_role if isinstance(assigned_role, list) else [assigned_role], pdf_file)
        )
        conn.commit()
        print(f"Rolle für bestehende Sätze in '{pdf_file}' gesetzt: {assigned_role}")

    
# Nicht mehr existierende Einträge löschen
    texts_to_delete = existing_texts - set(dokument_sätze)
    if texts_to_delete:
        with conn.cursor() as cur: 
            cur.execute(
                "DELETE FROM items WHERE text = ANY(%s);",
                (list(texts_to_delete),)
            )
            conn.commit()
            print(f"{len(texts_to_delete)} alte Einträge entfernt.")

# Embeddings für bestehende Texte aktualisieren, falls sie sich geändert haben
    with conn.cursor() as cur:
        for new_embedding, text in zip(dokument_embeddings, dokument_sätze):
            cur.execute(
                "SELECT embedding FROM items WHERE text = %s;",
                (text,)
            )
            existing_embedding = cur.fetchone()
            if existing_embedding and list(existing_embedding[0]) != new_embedding.tolist():
                cur.execute(
                    "UPDATE items SET embedding = %s WHERE text = %s;",
                    (new_embedding.tolist(), text)
                )
                conn.commit()
                print(f"Embedding für '{text}' aktualisiert.")


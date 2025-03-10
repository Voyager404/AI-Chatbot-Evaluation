from llama_cpp import CreateChatCompletionResponse, Llama
import json
import subprocess
import os
import sys
import re

# Mapping von Kürzeln zu Namen
employee_names = {
    "MS": "Max Schmidt",
    "MM": "Mia Müller"
}

# Nutzer fragen, ob er Mitarbeiter oder Kunde ist
def get_user_type():
    """Fragt den Nutzer, ob er Mitarbeiter oder Kunde ist."""
    user_type = input("Bist du ein Mitarbeiter oder ein Kunde? (Mitarbeiter/Kunde): ").strip().lower()
    
    if user_type not in ["mitarbeiter", "kunde"]:
        print("Ungültige Eingabe. Bitte 'Mitarbeiter' oder 'Kunde' eingeben.")
        return get_user_type()
    
    return user_type

def get_employee_code():
    """Fragt nach dem Mitarbeiter-Kürzel."""
    employee_code = input("Bitte gib dein Kürzel ein (z. B. MS, MM): ").strip().upper()
    
    if employee_code not in employee_names:
        print("Ungültiges Kürzel. Bitte versuche es erneut.")
        return get_employee_code()
    
    return employee_code, employee_names[employee_code]

user_type = get_user_type()
ticket_offen = False # Variable, um zu speichern, ob ein Ticket erstellt wurde

if user_type == "mitarbeiter":
    employee_code, employee_name = get_employee_code()
    print(f"Hallo {employee_name}👋")
    
    # Speichert das Kürzel in einer Umgebungsvariable
    os.environ["EMPLOYEE_CODE"] = employee_code 

else:
    user_permissions = {}
    print("Herzlich willkommen! 😊 Wie kann ich Ihnen weiterhelfen?")

# Alte JSON-Datei entfernen, um veraltete Informationen zu verhindern
if os.path.exists("prompt_suggestions.json"):
    os.remove("prompt_suggestions.json")

# SentenceTransformer in einem Subprozess ausführen (test2_get_relevant_data)
subprocess.run(["python", "test2_get_relevant_data.py"])

# Prüfen, ob die Datei erfolgreich erstellt wurde
if not os.path.exists("prompt_suggestions.json"):
    exit()

# Standardausgabe und Fehlerausgabe in eine Datei umleiten
sys.stdout = open(os.devnull, "w")
sys.stderr = open(os.devnull, "w")

# LLM aufrufen
llm = Llama(
    model_path="./discolm_german_7b_v1.Q4_K_M.gguf",
    verbose=False
)

# Standardausgabe wiederherstellen
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# Informationen aus prompt_suggestions file holen
with open("prompt_suggestions.json", "r") as f:
    data = json.load(f)

    raw_texts = data["texts"]
    prompt = data["prompt"]

# Umwandlung in das richtige Format
kontextinformation = [{"text": text, "link": link} for text, link in raw_texts]

# Kontextinformationen mit Links zusammenstellen
response_texts = []
for item in kontextinformation:
    if isinstance(item, dict) and "text" in item:  
        text = item["text"]
        link = item.get("link")  
        
        if link:
            response_texts.append(f"{text}\n\n🔗 Mehr Infos: {link}")
        else:
            response_texts.append(text)

# Kontextinformationen formatieren
formatted_context = "\n\n".join(
    [f"{item['text']}\n\n🔗 Mehr Infos: {item['link']}" for item in kontextinformation if isinstance(item, dict) and "text" in item and "link" in item and item["link"]]
)

messages = [
    {
      "role": "system",
        "content": 
        "Du bist ein freundlicher Assistent. "
        "Verwende **ausschließlich** die folgenden Informationen, um Fragen zu beantworten. "
        "Gib **keine** Antworten, die nicht aus diesen Informationen stammen. "
        "Falls du die Antwort nicht in diesen Infos findest, sage: 'Ich kann das nicht beantworten.'"
    },
    {
       "role": "system",
        "content": "📚 Kontextinformationen:\n\n" + "\n\n".join(response_texts)  # Direkt die Liste nutzen
    },
    {
        "role": "system",
        "content": 
        "In diesem System gibt es zwei Mitarbeiter: MS und MM. "
        "Diese sind Kürzel für spezifische Personen. "
        "Wenn ein Nutzer sich als MS identifiziert, ist er Mitarbeiter MS. "
        "Wenn ein Nutzer sich als MM identifiziert, ist er Mitarbeiter MM. "
        "Zugriffsrechte basieren auf diesen Kürzeln."
    },
    {
       "role": "system",
        "content": f"Der Nutzer ist ein {user_type}. Passe deine Antwort entsprechend an."
    },
    {
       "role": "user",
        "content": prompt  # Die Nutzerfrage wird zuletzt hinzugefügt
    }
]

while True:
# Falls der Nutzer "Radwechsel" schreibt, nachfragen
   if user_type == "kunde" and "reifenwechsel" in prompt.lower():
        klarstellung = input("Willst du einen zusätzlichen Reifenwechsel'? (ja/nein): ").strip().lower()
        
        if klarstellung == "ja":
            prompt = "Radwechsel"  # Damit das System es wie einen Radwechsel behandelt
    
# Falls der Nutzer ein Kunde ist und Radwechsel erwähnt, Termine anbieten
   if user_type == "kunde" and "Radwechsel" in prompt.lower():
    print("\nFür einen Radwechsel stehen folgende Termine zur Verfügung:")
    print("1) Montag, 10:00 Uhr")
    print("2) Mittwoch, 14:30 Uhr")
    
    auswahl = input("Bitte wähle einen Termin (1 oder 2): ").strip()
    
    if auswahl == "1":
        print("Dein Termin für den Radwechsel ist am Montag um 10:00 Uhr bestätigt. ✅")
    elif auswahl == "2":
        print("Dein Termin für den Radwechsel ist am Mittwoch um 14:30 Uhr bestätigt. ✅")
    else:
        print("Ungültige Eingabe. Bitte versuche es erneut.")
    
    exit()  # Beende das Programm nach der Terminvergabe

# Prüfen, ob das Wort "Ticket" in der Eingabe vorkommt und der Nutzer ein Mitarbeiter ist
   if user_type == "mitarbeiter" and "ticket" in prompt.lower():
        ticket_type = input("Geht es um ein Problem oder eine Information? (Problem/Information): ").strip().lower()
        
        if ticket_type == "problem":
            messages.append({"role": "system", "content": "Der Nutzer hat ein Problem und möchte deshalb ein Ticket eröffnen."})
            ticket_offen = True  # Ticket wurde erstellt
        elif ticket_type == "information":
            messages.append({"role": "system", "content": "Der Nutzer hat eine Information und möchte deshalb ein Ticket eröffnen."})
            ticket_offen = True  # Ticket wurde ebenfalls erstellt
        else:
            print("Ungültige Eingabe. Bitte 'Problem' oder 'Information' eingeben.")
            continue  # Wiederhole die Schleife, wenn die Eingabe ungültig ist.

# Nutzerfrage hinzufügen
   messages.append({"role": "user", "content": prompt})

# Antwort generieren
   response: CreateChatCompletionResponse = llm.create_chat_completion(
        messages=messages,
    )
   
   bot_response = response["choices"][0]["message"]["content"]

   # Kürzel im Bot-Text durch Namen ersetzen (Vermeidung von falschen Ersetzungen)
   for code, name in employee_names.items():
        bot_response = re.sub(rf"\b{code}\b", name, bot_response)

   links = [item["link"] for item in kontextinformation if isinstance(item, dict) and "link" in item and item["link"]]

# Falls Links vorhanden sind, hänge sie an die Antwort an
   links = [str(item["link"]) for item in kontextinformation if isinstance(item, dict) and "link" in item and item["link"]]
   if links:
    bot_response += "\n\n📢 Mehr Infos hier:\n\n" + "\n".join(links)

# Bot-Antwort speichern, damit er sich an den Verlauf erinnert    
   messages.append({"role": "assistant", "content": bot_response})

# Antwort ausgeben
   if "ich weiß es nicht" in bot_response.lower() or "nicht sicher" in bot_response.lower():
    print("Ich weiß die Antwort leider nicht.")
   else:
      print("\nAntwort:")
      print(bot_response)

# Nutzer fragen ob die Antwort ausreichend war
   feedback = input("\nWar diese Antwort hilfreich? (ja/nein): ").strip().lower()
   
   if feedback == "ja":
        print("Freut mich! Falls du weitere Fragen hast, stehe ich bereit.")
        if ticket_offen:
            print("Ticket erfolgreich abgeschlossen ✅") # Nur wenn ein Ticket geöffnet wurde
        break # Beende die Schleife
   
   elif feedback == "nein":
       prompt = input("Wie kann ich meine Antwort verbessern oder präzisieren? ")
       print("\nIch versuche es erneut...\n")
   else:
       print("Ich habe deine Antwort nicht verstanden. Bitte antworte mir mit 'ja' oder 'nein'.")

import xml.etree.ElementTree as ET
import requests
import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 1. Configurazione Header SEC
HEADERS = {'User-Agent': 'Massimo Saccol maxsaccol@yahoo.it'}

# 2. Configurazione LLM per la classificazione dei ruoli
class RoleClassification(BaseModel):
    is_target_executive: bool = Field(
        description="True se il ruolo corrisponde a CEO, CFO, CGO, Presidente o Vicepresidente Esecutivo. False altrimenti."
    )
    detected_role: str = Field(
        description="Il ruolo identificato (es. 'CEO', 'CFO', 'CGO', 'President', 'Other')"
    )

# Inizializzazione LLM (Legge OPENAI_API_KEY automaticamente dalle variabili d'ambiente)
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0
)
structured_llm = llm.with_structured_output(RoleClassification)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Sei un analista finanziario specializzato nei documenti della SEC USA.
Analizza la qualifica aziendale dell'insider e determina se appartiene a una delle seguenti figure apicali:
- CEO / Chief Executive Officer
- CFO / Chief Financial Officer / Treasurer
- CGO / Chief Growth Officer
- President / Executive Vice President / Managing Director

Imposta is_target_executive a True solo se si tratta di ruoli decisionali primari.
Imposta False per ruoli di livello inferiore, consiglieri esterni non operativi, o ruoli tecnici (es. "VP of Engineering")."""),
    ("human", "Qualifica aziendale: {officer_title}")
])

role_classifier_chain = prompt_template | structured_llm

def is_key_executive_llm(officer_title: str) -> bool:
    """Passa la qualifica all'LLM per una classificazione semantica"""
    if not officer_title or officer_title.strip() == "":
        return False
    try:
        result = role_classifier_chain.invoke({"officer_title": officer_title})
        return result.is_target_executive
    except Exception as e:
        print(f"Errore chiamata LLM: {e}")
        # Fallback deterministico se la chiamata API fallisce
        target_roles = ['CEO', 'CFO', 'CGO', 'CHIEF EXECUTIVE', 'CHIEF GROWTH', 'CHIEF FINANCIAL', 'PRESIDENT']
        return any(role in officer_title.upper() for role in target_roles)

def check_is_10b51_plan(root):
    """Scansiona le note per escludere i piani automatizzati 10b5-1"""
    footnotes = root.findall('.//footnote')
    for fn in footnotes:
        if fn.text and re.search(r'10b5-1', fn.text, re.IGNORECASE):
            return True
    return False

def parse_and_filter_form4(xml_url):
    """Scarica e analizza il singolo Form 4 XML"""
    try:
        response = requests.get(xml_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        root = ET.fromstring(response.content)
    except Exception:
        return None

    # Escludi piani 10b5-1
    if check_is_10b51_plan(root):
        return None

    # Estrazione Ruolo
    officer_title_node = root.find('.//officerTitle')
    officer_title = officer_title_node.text if officer_title_node is not None else ""

    # Classificazione intelligente tramite LLM
    if not is_key_executive_llm(officer_title):
        return None

    # Filtra per Codice P (Open Market Purchase)
    purchases = []
    for tx in root.findall('.//nonDerivativeTransaction'):
        code = tx.find('.//transactionCode')
        shares = tx.find('.//transactionShares/value')
        price = tx.find('.//transactionPricePerShare/value')
        
        if code is not None and code.text == 'P':
            num_shares = float(shares.text) if shares is not None else 0.0
            share_price = float(price.text) if price is not None else 0.0
            total_value = num_shares * share_price
            
            purchases.append({
                'shares': num_shares,
                'price': share_price,
                'total_value': total_value
            })

    if purchases:
        issuer = root.find('.//issuerTradingSymbol')
        reporting_owner = root.find('.//rptOwnerName')
        
        return {
            'ticker': issuer.text if issuer is not None else 'N/A',
            'insider_name': reporting_owner.text if reporting_owner is not None else 'N/A',
            'title': officer_title if officer_title else 'Executive',
            'purchases': purchases,
            'xml_url': xml_url
        }

    return None

def get_recent_form4_links():
    """Recupera l'elenco dei Form 4 più recenti via feed RSS SEC"""
    rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&datea=&dateb=&owner=only&count=40&output=atom"
    
    try:
        # Aumentato il timeout a 30 secondi per evitare ReadTimeout
        response = requests.get(rss_url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return []
    except requests.exceptions.RequestException as e:
        print(f"Errore di connessione alla SEC: {e}")
        return []

    try:
        root = ET.fromstring(response.content)
        xml_links = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            link = entry.find('atom:link', ns)
            if link is not None and 'href' in link.attrib:
                href = link.attrib['href']
                if '-index.htm' in href:
                    try:
                        index_page = requests.get(href, headers=HEADERS, timeout=15)
                        if index_page.status_code == 200:
                            matches = re.findall(r'href="([^"]+\.xml)"', index_page.text)
                            for m in matches:
                                if not m.endswith('xml'): continue
                                full_xml_url = "https://www.sec.gov" + m if m.startswith('/') else m
                                if 'doc' in full_xml_url or 'form4' in full_xml_url or 'xml' in full_xml_url:
                                    xml_links.append(full_xml_url)
                                    break
                    except requests.exceptions.RequestException:
                        continue
        return xml_links
    except Exception as e:
        print(f"Errore parsing Feed RSS: {e}")
        return []

def send_email_alert(ticker, manager, title, purchases, xml_url):
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_PASS")
    receiver_email = sender_email  # Invia la mail a te stesso

    if not sender_email or not sender_password:
        print("Credenziali Gmail non trovate nelle variabili d'ambiente.")
        return

    subject = f"🚨 ACQUISTO INSIDER DETECTED: {ticker} ({manager})"
    
    body = f"""
    🔥 RILEVATO ACQUISTO DIRIGENZIALE
    
    Ticker: {ticker}
    Manager: {manager} ({title})
    
    Dettaglio acquisti:
    """
    for p in purchases:
        body += f"  • {p['shares']:,} azioni a ${p['price']} (Totale: ${p['total_value']:,.2f})\n"
        
    body += f"\nModulo SEC ufficiale: {xml_url}\n"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"📧 Email inviata con successo per {ticker}!")
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")

# Esecuzione
if __name__ == "__main__":
    print("Avvio Agente IA con classificazione LLM dei ruoli...")
    links = get_recent_form4_links()
    print(f"Trovati {len(links)} moduli Form 4 recenti. Analisi in corso...\n")

    found_count = 0
    for link in set(links):
        result = parse_and_filter_form4(link)
        if result:
            found_count += 1
            print(f"🔥 RILEVATO ACQUISTO DIRIGENZIALE:")
            print(f"Ticker: {result['ticker']}")
            print(f"Manager: {result['insider_name']} ({result['title']})")
            for p in result['purchases']:
                print(f"  -> Acquistate {p['shares']:,} azioni a ${p['price']} (Totale: ${p['total_value']:,.2f})")
            print(f"Link SEC: {result['xml_url']}\n" + "-"*50)
            
            # INVIA L'EMAIL QUANDO VIENE TROVATO UN ACQUISTO
            send_email_alert(
                ticker=result['ticker'],
                manager=result['insider_name'],
                title=result['title'],
                purchases=result['purchases'],
                xml_url=result['xml_url']
            )
            
    if found_count == 0:
        print("Nessun acquisto discrezionale confermato dall'LLM nei moduli recenti.")
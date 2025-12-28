import requests
from bs4 import BeautifulSoup
import datetime
import time
import json
import re
import io
import os
import random
import pdfplumber
import yfinance as yf
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# .env dosyasını yükle
load_dotenv()

# --- BÖLÜM 1: YARDIMCI YAPILANDIRMALAR ---

def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent=Mozilla/5.0")
    # Logları temizlemek için
    chrome_options.add_argument("--log-level=3")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_currency(value_str):
    if not value_str: return 0.0
    try:
        clean = re.sub(r'[^\d.+-]', '', str(value_str).replace(',', ''))
        return float(clean)
    except:
        return 0.0

# --- BÖLÜM 2: FED & LİKİDİTE GÖSTERGELERİ (MEVCUT KOD) ---

def check_fed_bond_purchases():
    result = {'alert': False, 'message': '', 'current_value': None, 'error': False}
    driver = None
    try:
        url = "https://www.newyorkfed.org/markets/domestic-market-operations/monetary-policy-implementation/treasury-securities/treasury-securities-operational-details#current-schedule"
        driver = get_selenium_driver()
        driver.get(url)
        time.sleep(3)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        if "bond purchase" in page_text.lower() and "no operations scheduled" not in page_text.lower():
            result['alert'] = True
            result['message'] = "Planlanmış bir uzun vadeli bono (Bond) alımı var, bu net bir finansal genişleme işaretidir."
        else:
            result['alert'] = False
            result['message'] = "Planlanmış bir uzun vadeli bono (Bond) alım operasyonu bulunamadı. Fed henüz uzun dönemli tahvilleri almaya başlamamış veya şimdilik böyle bir planı yok."
    except Exception as e:
        result['error'] = True
        result['message'] = f"Hata: {str(e)}"
    finally:
        if driver: driver.quit()
    return result

def check_fed_balance_sheet():
    result = {'alert': False, 'message': '', 'current_value': None, 'change': None, 'error': False}
    base_url = "https://www.federalreserve.gov/releases/h41/{date}/h41.pdf"
    current_pdf_stream = None
    today = datetime.date.today()
    
    for i in range(14): 
        check_date = today - datetime.timedelta(days=i)
        url = base_url.format(date=check_date.strftime('%Y%m%d'))
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                current_pdf_stream = io.BytesIO(resp.content)
                break
        except: continue
        
    if not current_pdf_stream:
        result['error'] = True
        result['message'] = "H.4.1 PDF raporu bulunamadı."
        return result

    try:
        with pdfplumber.open(current_pdf_stream) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            match = re.search(r"Notes and bonds, nominal\d*\s+([\d,]+)\s+([+-]?[\d,]+)", full_text)
            if match:
                val = clean_currency(match.group(1))
                change = clean_currency(match.group(2))
                result['current_value'] = val
                result['change'] = change
                if change > 0:
                    result['alert'] = True
                    result['message'] = f"Notes and bonds kaleminde artış ({change}) var. Bu finansal genişleme işaretidir."
                else:
                    result['alert'] = False
                    result['message'] = "Bilanço kalemlerinde (Notes and bonds) genişleme yok veya veri sabit. Bu da finansal genişleme olmadığını gösteren işaretlerdendir."
            else:
                result['error'] = True
                result['message'] = "PDF içinde 'Notes and bonds, nominal' satırı ayrıştırılamadı."
    except Exception as e:
        result['error'] = True
        result['message'] = f"H.4.1 PDF Hatası: {str(e)}"
    return result

def check_commercial_banks_h8(long_term_bond_exists=False):
    result = {'alert': False, 'message': '', 'current_value': None, 'previous_value': None, 'error': False}
    try:
        url = "https://www.federalreserve.gov/releases/h8/current/default.htm"
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        for tr in soup.find_all('tr'):
            text = tr.get_text(" ", strip=True)
            if "Treasury" in text and "agency securities" in text and "MBS" not in text:
                matches = re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d+\b', text)
                valid_matches = [m for m in matches if clean_currency(m) > 1000]
                
                if len(valid_matches) >= 2:
                    curr = clean_currency(valid_matches[-1])
                    prev = clean_currency(valid_matches[-2])
                    result['current_value'] = curr
                    result['previous_value'] = prev
                    
                    if curr < prev:
                        if not long_term_bond_exists:
                            result['alert'] = False
                            result['message'] = (f"Bankalardaki tahvil miktarında DÜŞÜŞ var ({curr} < {prev}). Ancak Fed tarafında uzun vadeli bono (Bond) alım planı bulunamadığı için "
                                                 "Fed muhtemelen kısa süreli (3, 6, 9 aylık) tahvilleri alıyor demektir. Bu durum tam bir finansal genişleme sayılmaz; "
                                                 "uzun dönem tahvil alımlarını görmemiz gerekir.")
                        else:
                            result['alert'] = True
                            result['message'] = "Bankalardaki tahvil miktarında DÜŞÜŞ var. Fed uzun vadeli bono alımlarıyla eş zamanlı olarak bankalardan tahvil çekiyor, bu net bir finansal genişleme işaretidir."
                    else:
                        result['alert'] = False
                        result['message'] = "Bankaların tahvil varlıkları artıyor veya sabit. Bu da finansal genişleme olmadığını gösteren işaretlerdendir."
                    break
    except Exception as e:
        result['error'] = True
        result['message'] = f"H.8 Hatası: {e}"
    return result

def check_money_market_funds():
    result = {'alert': False, 'message': '', 'current_value': None, 'previous_value': None, 'error': False}
    driver = None
    try:
        driver = get_selenium_driver()
        driver.get("https://www.ici.org/research/stats/mmf")
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for row in soup.find_all('tr'):
            row_text = row.get_text(" ", strip=True)
            if row_text.lower().startswith("total"):
                matches = re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', row_text)
                if len(matches) >= 2:
                    curr = clean_currency(matches[0])
                    prev = clean_currency(matches[1])
                    result['current_value'] = curr
                    result['previous_value'] = prev
                    if curr < prev:
                        result['alert'] = True
                        result['message'] = "Fonlarda düşüş var, risk iştahı artıyor demektir. Bu kripto için finansal genişleme sinyalidir. Risk iştahı artıyor, kripto için olumlu olabilir."
                    else:
                        result['alert'] = False
                        result['message'] = "Fonlarda para girişi var veya sabit. Bu da finansal genişleme olmadığını gösterir. Risk iştahında artış yok, bu da kripto için olumlu bir haber değil."
                    break
    except Exception as e:
        result['error'] = True
        result['message'] = f"ICI Hatası: {str(e)}"
    finally:
        if driver: driver.quit()
    return result

# --- BÖLÜM 3: ALTCOIN & PİYASA VERİLERİ (GÜNCELLENDİ) ---

def get_fear_and_greed_manual():
    """Alternative.me sitesinden Fear & Greed verisini API kullanmadan çeker."""
    try:
        url = "https://alternative.me/crypto/fear-and-greed-index/"
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Sitedeki puanı bul (Genellikle bir div içinde 'fng-score' class'ı ile durur)
        score_div = soup.find('div', class_='fng-circle')
        if score_div:
            score = score_div.get_text(strip=True)
            
            # Durum metnini bul (Extreme Greed vs.)
            status_div = soup.find('div', class_='fng-value') # Bazen class ismi değişebilir, genel yapıya bakıyoruz
            # Alternatif yapı: Puanın altındaki metin
            status_text = "Bilinmiyor"
            for div in soup.find_all('div'):
                if div.get_text(strip=True) in ["Extreme Greed", "Greed", "Neutral", "Fear", "Extreme Fear"]:
                    status_text = div.get_text(strip=True)
                    break
            
            return f"{score} ({status_text})"
        
        # Yedek API (Alternative.me public API)
        api_url = "https://api.alternative.me/fng/"
        api_resp = requests.get(api_url, timeout=5).json()
        data = api_resp['data'][0]
        return f"{data['value']} ({data['value_classification']})"

    except Exception as e:
        return f"Hata: {str(e)}"

def get_crypto_data_cmc():
    """CoinMarketCap API'sinden tüm kripto verilerini çeker."""
    api_key = os.getenv('COINMARKETCAP_API_KEY')
    if not api_key:
        return {'Error': 'Lütfen .env dosyanıza COINMARKETCAP_API_KEY ekleyin.'}

    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}
    base_url = 'https://pro-api.coinmarketcap.com/v1'

    try:
        # Global Metrikler
        global_url = f"{base_url}/global-metrics/quotes/latest"
        global_response = requests.get(global_url, headers=headers, timeout=10)
        global_data = global_response.json()['data']

        total_mcap = global_data['quote']['USD']['total_market_cap']
        btc_dominance = global_data['btc_dominance']
        altcoin_season_index = 100 - btc_dominance

        # Anlık Fiyatlar
        listings_url = f"{base_url}/cryptocurrency/quotes/latest"
        params = {'symbol': 'BTC,ETH,USDT', 'convert': 'USD'}
        listings_response = requests.get(listings_url, headers=headers, params=params, timeout=10)
        listings_data = listings_response.json()['data']

        btc_price = listings_data['BTC']['quote']['USD']['price']
        eth_price = listings_data['ETH']['quote']['USD']['price']
        usdt_mcap = listings_data['USDT']['quote']['USD']['market_cap']
        eth_btc_ratio = eth_price / btc_price if btc_price else 0

        # Fear & Greed (Artık manuel fonksiyonu çağırıyoruz)
        fear_greed_display = get_fear_and_greed_manual()

        return {
            'BTC Fiyat': f"${btc_price:,.2f}",
            'ETH Fiyat': f"${eth_price:,.2f}",
            'ETH/BTC': f"{eth_btc_ratio:.6f}",
            'Toplam Piyasa Değeri': f"${total_mcap:,.0f}",
            '24s Hacim': f"${global_data['quote']['USD']['total_volume_24h']:,.0f}",
            'BTC Hakimiyeti': f"%{btc_dominance:.2f}",
            'USDT Hakimiyeti': f"%{(usdt_mcap / total_mcap * 100):.2f}",
            'Altcoin Sezon Endeksi': f"%{altcoin_season_index:.2f}",
            'Korku & Hırs': fear_greed_display
        }
    except Exception as e:
        return {'Error (CMC)': f'{e}'}

def get_yahoo_finance_data_optimized():
    """YFinance Kütüphanesi ile DXY, SPX ve Tahvil Faizini çeker."""
    symbols = {
        'DXY (Dolar Endeksi)': 'DX=F',  # GÜNCELLENDİ: Vadeli işlem sembolü daha stabil
        'S&P 500 Endeksi': '^GSPC',
        'ABD 10Y Tahvil (Faiz)': '^TNX' # EKLENDİ: Piyasa Faizi Göstergesi
    }
    results = {}
    for name, ticker in symbols.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            # Son 5 günlük veriyi alıp son kapanışı veya anlık fiyatı yakala
            hist = ticker_obj.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                results[name] = f"{price:.2f}"
            else:
                results[name] = "Veri Yok"
        except Exception as e:
            results[name] = f"Hata: {e}"
    return results

def get_alpha_vantage_data():
    """Alpha Vantage API'sinden CPI verisini çeker."""
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    results = {}
    if not api_key:
        results['CPI (AV)'] = 'API Anahtarı Yok'
        return results

    try:
        # Enflasyon (CPI)
        cpi_url = f"https://www.alphavantage.co/query?function=CPI&interval=monthly&apikey={api_key}"
        cpi_resp = requests.get(cpi_url, timeout=10)
        cpi_data = cpi_resp.json()
        
        if 'data' in cpi_data and cpi_data['data']:
            latest = cpi_data['data'][0]
            # CPI genellikle bir Endeks olarak gelir (örn: 300.0). 
            # Kullanıcıyı yanıltmamak için "TÜFE Endeksi" olarak belirtiyoruz.
            results['TÜFE Endeksi (CPI)'] = f"{latest['value']} ({latest['date']})"
        else: 
            results['TÜFE Endeksi (CPI)'] = 'Veri Yok/Limit Aşıldı'
            
    except:
        results['TÜFE Endeksi (CPI)'] = 'Hata'
        
    return results

# --- ANA ÇALIŞTIRMA VE RAPORLAMA ---

def run_full_analysis():
    # 1. BÖLÜM: FED & LİKİDİTE
    print(f"\n{'='*85}\nFİNANSAL GENİŞLEME VE LİKİDİTE ANALİZİ | {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}\n{'='*85}")
    
    print("[*] FED BONO ALIMLARI analiz ediliyor...")
    fed_bond_res = check_fed_bond_purchases()
    bond_exists = fed_bond_res['alert']
    
    tasks = [
        ("FED BONO ALIMLARI", lambda: fed_bond_res),
        ("FED BİLANÇO (H.4.1)", check_fed_balance_sheet),
        ("BANKA VARLIKLARI (H.8)", lambda: check_commercial_banks_h8(bond_exists)),
        ("PARA PİYASASI FONLARI (ICI)", check_money_market_funds)
    ]
    
    for name, task_func in tasks:
        if name != "FED BONO ALIMLARI": 
            print(f"[*] {name} analiz ediliyor...")
        res = task_func()
        
        if res['error']: icon = "❌ HATA:"
        else: icon = "✅ GENİŞLEME:" if res['alert'] else "🚨 SIKILAŞMA/SABİT:"
        
        print(f"{icon} {res['message']}")
        
        if not res['error']:
            if 'change' in res and res['change'] is not None:
                print(f"    [Veri] Mevcut: {res['current_value']} | Haftalık Değişim: {res['change']}")
            elif res['current_value'] is not None:
                print(f"    [Veri] Güncel: {res['current_value']} | Önceki: {res.get('previous_value', 'Yok')}")
        print("-" * 85)

    # 2. BÖLÜM: ALTCOIN BOĞA SEZONU ANALİZİ
    print("\n\n")
    print("="*85)
    print("ALTCOIN BOĞA SEZONU ANALİZ PANELİ".center(85))
    print("="*85)
    print("Veriler toplanıyor... (CMC, Yahoo Finance, Alpha Vantage, Alt.me)\n")

    crypto_data = get_crypto_data_cmc()
    yahoo_data = get_yahoo_finance_data_optimized()
    macro_data = get_alpha_vantage_data()

    print("📈 KRİPTO PİYASASI VE ZİNCİR VERİLERİ")
    print("-" * 40)
    crypto_keys = ['BTC Fiyat', 'ETH Fiyat', 'ETH/BTC', 'Toplam Piyasa Değeri',
                   '24s Hacim', 'BTC Hakimiyeti', 'USDT Hakimiyeti',
                   'Altcoin Sezon Endeksi', 'Korku & Hırs']
    for key in crypto_keys:
        if key in crypto_data:
            print(f"  {key:<25}: {crypto_data[key]}")

    print("\n🌍 GELENEKSEL PİYASALAR VE MAKRO GÖSTERGELER")
    print("-" * 40)
    for key, value in yahoo_data.items():
        print(f"  {key:<25}: {value}")
    for key, value in macro_data.items():
        print(f"  {key:<25}: {value}")

    print("\n💡 YORUM VE ANALİZ NOTLARI")
    print("-" * 40)
    notes = [
        "1. Altcoin Sezon Endeksi: Bitcoin Hakimiyetinin 100'e tamamlanmasıdır.",
        "   -> Yüksek değer (>%60), sermayenin altcoin'lere kaydığının POTANSİYEL göstergesidir.",
        "2. ETH/BTC Paritesi YÜKSELİŞİ, 'risk-on' modunu ve altcoin sezonunun erken sinyali olabilir.",
        "3. DÜŞÜK DXY ve DÜŞÜK ABD 10Y Tahvil Faizi, kripto için en iyi senaryodur.",
        "4. ABD 10 Yıllık Tahvil Faizinin (%4.50+) üzerine çıkması piyasayı baskılayabilir.",
        "5. Fear & Greed Endeksi 'Aşırı Hırs' (90+) seviyesinde piyasa aşırı ısınmış olabilir."
    ]
    for note in notes:
        print(f"  {note}")

    print("\n" + "="*85)

if __name__ == "__main__":
    run_full_analysis()

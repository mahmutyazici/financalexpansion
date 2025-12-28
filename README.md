<<<<<<< HEAD
# financalexpansion
=======
📊 Crypto & Macro Liquidity Analyzer
Bu proje, kripto para piyasalarını hem geleneksel makroekonomik likidite göstergeleri hem de on-chain/piyasa metrikleri üzerinden analiz eden kapsamlı bir Python aracıdır. Program, piyasadaki "akıllı para" hareketlerini ve olası boğa/ayı döngülerini önceden saptamak için tasarlanmıştır.

🚀 Temel Özellikler ve Analiz Yapısı
Kod iki ana modülden oluşmaktadır:

1. Finansal Genişleme ve Likidite Analizi (Macro Module)
Bu bölüm, doğrudan Federal Reserve (Fed) ve kurumsal bankacılık verilerini kullanarak piyasadaki dolar likiditesini ölçer:

Fed Bono Alımları: New York Fed üzerinden anlık veri çekerek Fed'in doğrudan piyasaya para enjekte edip etmediğini kontrol eder.

Fed Bilançosu (H.4.1 Raporu): Fed'in haftalık raporlarını PDF formatında parse ederek "Notes and Bonds" kalemindeki değişimleri analiz eder.

Banka Varlık Analizi (H.8 Raporu): Ticari bankaların tahvil stoklarını inceleyerek, likiditenin bankalardan piyasaya akıp akmadığını saptar.

Para Piyasası Fonları (ICI): Yatırımcıların "güvenli liman" (nakit) arayışında mı yoksa risk iştahının mı arttığını Money Market Funds verileriyle ölçer.

2. Altcoin Sezonu ve On-Chain Göstergeler (Crypto Module)
Piyasa dinamiklerini profesyonel metriklerle analiz eder:

Piyasa Hakimiyeti (Dominance): BTC Dominance ve USDT Dominance verilerini çekerek sermayenin hangi varlıkta yoğunlaştığını ve nakit oranını hesaplar.

ETH/BTC Rasyosu: Altcoin sezonunun en büyük öncü göstergesi olan pariteyi analiz eder ve güç durumunu raporlar.

Fear & Greed Index: Yatırımcı psikolojisini (Korku ve Hırs) anlık olarak entegre eder.

Makro Gösterge Entegrasyonu: DXY (Dolar Endeksi), S&P 500 ve ABD 10 Yıllık Tahvil Faizleri arasındaki korelasyonu dinamik yorumlarla sunar.

🛠 Kullanılan Teknolojiler
Python 3.x

Selenium & BeautifulSoup4: Dinamik web scraping işlemleri için.

Pdfplumber: Fed raporlarını (PDF) veri setine dönüştürmek için.

YFinance: Geleneksel piyasa verileri için.

CoinMarketCap API: Kripto para piyasa değerleri ve dominance verileri için.

📋 Kurulum
Gerekli kütüphaneleri yükleyin:

Bash

pip install requests bs4 selenium yfinance pdfplumber python-dotenv webdriver-manager
.env dosyanızı oluşturun ve API anahtarlarınızı ekleyin:

Kod snippet'i

COINMARKETCAP_API_KEY=your_api_key_here
ALPHA_VANTAGE_API_KEY=your_api_key_here
Programı çalıştırın:

Bash

python main.py
💡 Analiz Notları ve Eşik Değerler
Programın çıktıları şu temel mantık çerçevesinde yorumlanır:

DXY < 100 & ABD 10Y < 3.8%: Kripto için "Goldilocks" (en ideal) senaryo.

USDT Dominance > 6%: Piyasanın korku içinde olduğunu ve ciddi bir alım fırsatının yaklaştığını gösterebilir.

Fed Bilanço Artışı: Gerçek bir boğa koşusu için gereken ana yakıt.
>>>>>>> 12bda61 (Initial commit: Financial expansion monitor with maturity analysis)

# license-scan

Node.js ve Python projeleri için harici bağımlılık lisans envanteri ve CI uyumluluk denetleyicisi.

## Genel Bakış

Yazılım projeleri çoğu zaman yüzlerce doğrudan veya dolaylı (transitive) üçüncü taraf bağımlılık barındırır. Kapalı kaynaklı veya tescilli ürünlerde uyumsuz lisansların (örneğin ikili dağıtımlarda GPL/AGPL) ya da lisansı belirsiz bileşenlerin fark edilmeden dağıtılması ciddi hukuki ve kurumsal riskler doğurur.

`license-scan`, üçüncü taraf SaaS araçlarına veya ücretli servislere ihtiyaç duymadan, sıfır harici çalışma zamanı bağımlılığı ile çevrimdışı (offline) lisans envanteri çıkarır. Node.js (`package-lock.json` v2/v3 ve `node_modules`) ile Python kurulu paketlerini (`importlib.metadata`) tarar; lisansları standart SPDX kimliklerine dönüştürür; SPDX mantıksal ifadelerini (`AND`, `OR`, `WITH`) ayrıştırır; tanımlanan politika kurallarına (`license-scan.json`) göre denetler ve terminal tablosu, JSON, CSV, Markdown ile `NOTICE` / `THIRD_PARTY` atıf dosyaları üretir.

## Özellikler

- Sıfır harici çalışma zamanı bağımlılığı: Yalnızca Python standart kütüphanesini (`>=3.10`) kullanır.
- Çoklu ekosistem desteği:
  - Node.js: `package-lock.json` (v2 ve v3 formatları) ile `node_modules` dizinini (`package.json`, eski `licenses` dizisi ve dosya içeriğinden lisans tespiti) inceler.
  - Python: Etkin ortamdaki veya belirtilen herhangi bir `site-packages` dizinindeki kurulu paketleri `importlib.metadata` üzerinden (`License`, PEP 639 `License-Expression`, Trove sınıflandırıcıları ve lisans dosyaları) okur.
- SPDX dönüştürme ve ifade ayrıştırıcı:
  - Yerleşik alias tablosu (`Apache 2.0` -> `Apache-2.0`, `MIT License` -> `MIT` vb.).
  - `AND`, `OR`, `WITH` ve parantez hiyerarşisini destekleyen mantıksal ifade ayrıştırıcısı.
  - Çift lisanslama (`OR`) doğrulaması: Dallardan en az biri politikaya uygunsa bağımlılık kabul edilir.
  - Üst veri bulunamadığında lisans metnini tarayan gömülü metin analizcisi.
- Politika denetimi (`license-scan.json`):
  - Joker karakter destekli (`GPL-*` gibi) `allow`, `deny` ve `review` listeleri.
  - Gerekçeli paket istisnaları (`exceptions`).
  - İnceleme gerektiren veya bilinmeyen lisansları doğrudan başarısız sayan `--strict` kipi.
  - Yasaklı lisans bulunduğunda CI hatası için çıkış kodu `1`.
- Farklı çıktı formatları:
  - Terminal tablosu.
  - JSON ve CSV formatları.
  - GitHub uyumlu Markdown raporu.
  - Lisans atıf dosyası üretici (`NOTICE` / `THIRD_PARTY`).

## Kurulum

### Kaynak Koddan veya Pip ile

```bash
git clone https://github.com/YusufBeratZengin/license-scan.git
cd license-scan
pip install .
```

### Kurulum Yapmadan Doğrudan Çalıştırma

Harici çalışma zamanı kütüphanesi gerekmediği için Python 3.10+ kurulu herhangi bir ortamda doğrudan çalıştırabilirsiniz:

```bash
python -m license_scan --help
```

## Hızlı Başlangıç

### 1. Politika Dosyası Oluşturma

Deponuzda başlangıç için varsayılan bir `license-scan.json` oluşturun:

```bash
license-scan --init-policy
```

### 2. Projeyi Tarama

Geçerli dizindeki tüm Node ve Python bağımlılıklarını taramak için:

```bash
license-scan .
```

### 3. Yalnızca Canlı (Production) Bağımlılıkları İnceleme

Geliştirme bağımlılıklarını dışarıda bırakmak için:

```bash
license-scan . --prod
```

### 4. Atıf (NOTICE) Dosyası Üretme

Üçüncü taraf bileşenlerin lisans ve telif metinlerini içeren bir `NOTICE` dosyası oluşturmak için:

```bash
license-scan . --notice -o NOTICE
```

## Komut Satırı Seçenekleri

```text
kullanım: license-scan [-h] [-p DOSYA] [-e {all,node,python}]
                       [-f {table,json,csv,markdown,notice}] [-o DOSYA]
                       [--site-packages DIZIN] [--prod] [--strict] [--notice]
                       [--init-policy] [-v] [-q]
                       [yol]

konumsal argümanlar:
  yol                   Taranacak dizin, package-lock.json veya site-packages yolu (varsayılan: geçerli dizin).

seçenekler:
  -h, --help            Yardım mesajını görüntüler ve çıkar.
  -p, --policy DOSYA    Politika dosyası yolu (varsayılan: varsa license-scan.json, yoksa yerleşik kurallar).
  -e, --ecosystem {all,node,python}
                        Taranacak ekosistem (varsayılan: all).
  -f, --format {table,json,csv,markdown,notice}
                        Çıktı formatı (varsayılan: table).
  -o, --output DOSYA    Çıktıyı ekrana basmak yerine belirtilen dosyaya yazar.
  --site-packages DIZIN Python site-packages dizinini doğrudan belirtir.
  --prod, --no-dev      Geliştirme bağımlılıklarını (devDependencies) hariç tutar.
  --strict              REVIEW veya UNKNOWN durumundaki lisansları hata kabul eder (çıkış kodu 1).
  --notice              NOTICE / THIRD_PARTY atıf dosyası formatında çıktı üretir.
  --init-policy         Varsayılan bir license-scan.json dosyası oluşturur ve çıkar.
  -v, --version         Sürüm numarasını görüntüler ve çıkar.
  -q, --quiet           Bilgilendirme çıktılarını gizler.
```

## Politika Yapılandırması (`license-scan.json`)

```json
{
  "$schema": "https://raw.githubusercontent.com/YusufBeratZengin/license-scan/main/schema.json",
  "allow": [
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "ISC",
    "0BSD",
    "CC0-1.0",
    "Unlicense",
    "PSF-2.0",
    "Zlib"
  ],
  "deny": [
    "GPL-1.0*",
    "GPL-2.0*",
    "GPL-3.0*",
    "AGPL-1.0*",
    "AGPL-3.0*",
    "SSPL-1.0*",
    "CPAL-1.0*",
    "OSL-3.0*"
  ],
  "review": [
    "MPL-2.0",
    "LGPL-2.1*",
    "LGPL-3.0*",
    "EPL-1.0",
    "EPL-2.0",
    "EUPL-1.2"
  ],
  "allow_unknown": false,
  "exceptions": {
    "dahili-derleme-araci": {
      "license": "GPL-3.0-only",
      "reason": "Yalnızca yerel derleme adımında kullanılır; son kullanıcıya dağıtılmaz."
    }
  }
}
```

### Politika Değerlendirme Kuralları

1. **Önce İstisnalar:** Paket adı `exceptions` listesinde kayıtlıysa ve lisans eşleşiyorsa paket doğrudan `ALLOWED` olarak onaylanır.
2. **SPDX İfadeleri:**
   - Tek lisans: Sırasıyla `deny` (joker karakter destekli), `review` ve `allow` listelerine göre kontrol edilir.
   - `OR` (Çift lisans): Seçeneklerden en az biri `ALLOWED` ise paket kabul edilir.
   - `AND` (Bileşik lisans): Bileşenlerden herhangi biri `DENIED` ise paket reddedilir.
3. **Çıkış Kodu:** Herhangi bir paket reddedilirse çıkış kodu `1` döner. `--strict` etkinse inceleme gerektiren veya tanımlanamayan lisanslar da çıkış kodunu `1` yapar.

## Sürekli Entegrasyon (CI)

### GitHub Actions Örneği

```yaml
name: Lisans Denetimi

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python Kurulumu
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Bağımlılıkları Yükle
        run: |
          npm ci --production
      - name: Lisans Uyumluluğunu Denetle
        run: |
          python -m license_scan . --prod --strict
```

## Testleri Çalıştırma

Standart kütüphanedeki `unittest` modülü ile tüm testleri çalıştırabilirsiniz:

```bash
python -m unittest discover -s tests -v
```

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.

Copyright (c) 2026 Yusuf Berat Zengin.

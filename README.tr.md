# Orchestrator — Claude Code için doğrulanabilir bir orkestrasyon yığını

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Tek bir Claude Code oturumunu orkestratöre dönüştürür: brief bir dalga planına dönüşür, her
dalga uzmanlaşmış alt ajanları çalıştırır, her dalga bir dosya olarak yere iner ve bağımsız bir
denetçi sonucu kabul eder ya da geri çevirir. 41 ajan kartı, 10 ortak sözleşme, 10 slash
komutu, 4 isteğe bağlı skill.

MIT lisansı. Yazar: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protokol **2.16.0**.

> **Önce bunu okuyun — dil hakkında.** Orkestrasyon protokolü, ajan kartları ve kabul ölçütleri
> **Rusça** yazılmıştır. Araçlar, testler, kurulum yolu ve kod yorumları İngilizcedir. Aradığınız
> ajanların kendisiyse Rusça Markdown okuyacaksınız. Aradığınız, bir ajan yığınını güvenilir
> kılan altyapıysa, o kısım dilden bağımsızdır ve bu deponun var olma sebebidir.

---

## Bu proje neden var

Claude Code için alt ajan koleksiyonu eksikliği yok. Eksik olan, **doğrulayabildikleriniz**.
Çoğu yalnızca bir Markdown dosyaları klasörü: hook'ların gerçekten tetiklendiğini kanıtlayan bir
şey yok, gizli anahtar tarayıcısının doğru baytlara baktığını kanıtlayan bir şey yok ve bir
denetim sessizce denetlemeyi bıraktığında hiçbir şey hata vermiyor.

Bu depo ters yönde bir tercih yapıyor. Ajan kütüphanesi sıradan; **asıl mesele etrafındaki altyapı**:

| Çoğu koleksiyonun verdiği | Bunun verdiği |
|---|---|
| Yalnızca ajan Markdown'ları | Ajanlar **ve ayrıca** guard'lar, kurulumcu, doctor, kabul kapısı, senkronizasyon |
| Test yok | **97 test**, yalnızca standart kütüphane, API çağrısı yok, ağ yok |
| «Şunu settings.json'a ekleyin» | Çakışma ön kontrolü olan kurulumcu; **doctor guard'ı gerçekten çalıştırır** ve engellemesini şart koşar |
| Hook'ların çalıştığı varsayılır | Üç yüklü duman testi: zararsız geçmeli, gizli anahtar engellenmeli, riskli komut engellenmeli |
| «Güvenli, prompt'a güvenin» | Prompt metni hiçbir zaman erişim sınırı sayılmaz — bkz. [SECURITY.md](SECURITY.md) |

Bir betiğin denetleyebileceği her şeyi betik denetler; çünkü yalnızca prompt içinde yaşayan bir
kural, sessizce uygulanmaz hale gelen bir kuraldır.

---

## Hızlı başlangıç

**Python 3.10+** ve **Git** gerekir. API anahtarı yok, ağ yok, model çağrısı yok:

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

Bu; ajan sözleşme linter'ını, hazırlık sayacının kendi testini, tüm test paketini ve bir gizli
anahtar taramasını çalıştırır. Checkout dışında hiçbir şeye dokunmaz.

Kendi seçtiğiniz dizinlere kurun — kurulumcu **önce plan gösterir ve asla üzerine yazmaz**:

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Planı inceleyin, sonra `--apply` ile yeniden çalıştırın. Bir hedef dosya varsa ve farklıysa,
kurulum durur ve sizin dosyanız korunur. Ardından sonucu doğrulayın:

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal`, araştırma ve Markdown çıktıları için yedi rol kurar. `full`, yazılım / site kurulumu /
medya hatlarını ve dış bağımlılıklarını ekler. Windows notları ve Claude Code'u yeni dizine
yönlendirme: [INSTALL.md](INSTALL.md).

---

## İçinde ne var

| Katman | Amaç | Doğrulama sınırı |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Yönlendirme, sözleşmeler, definition of done | Linter yapıyı denetler; yanıt kalitesi insan kabulü gerektirir |
| `tools/verify.py`, `tests/` | Yeniden üretilebilir tek komut, olumsuz senaryolar dahil | Claude API'siz, harici MCP'siz |
| `tools/guard.py` | PreToolUse aşamasında kimlik bilgisi ve yıkıcı komut tespiti | **Sezgisel katmanlı savunma** — host izinlerini ve sandbox'ı koruyun |
| `tools/install.py`, `tools/doctor.py` | Yıkıcı olmayan kurulum; hazırlık raporu | Doctor ne kimlik doğrulamayı ne de model kalitesini test eder |
| `tools/acceptance-gate/` | Çalışma günlüğünün determinist denetimleri ve isteğe bağlı denetçi worker'ı | Model worker'ı **varsayılan olarak kapalı**; canlı uçtan uca sertifikalı değil |
| `tools/sync_stack.py` | Kesin bir allowlist üzerinden Git köprüsü | İsteğe bağlı; ayrışmış dalları sizin yerinize birleştirmez |
| `tools/export_session.py` | Tercihe bağlı transkript dışa aktarımı | **Kapalı**; maskeleme desen tabanlıdır, gizlilik garantisi değildir |

### Kabul kapısı

Doğru hale gelmesi en uzun süren fikir. Bir çalışma kapandıktan sonra, orkestratörün akıl
yürütmesini hiç görmemiş **ayrı bir bağlam** çıktıyı brief'e karşı değerlendirir. Önce
determinist bir betik çalışır; model yalnızca betiğin yargılayamadığını değerlendirir:

- `run_status` ile `verdict` ayrı alanlardır. `done` olmayan bir çalışma
  *«kabule tabi değil»* döner, sahte bir geçiş değil.
- `SKIP` sonucu **«eksik»** verir, asla «kabul edildi» olmaz. PDF *yalnızca imza — bir
  görüntüleyicide açın* diye raporlanır; `.docx` ise *yapı ayrıştırılıyor, görsel kabul ayrı*.
- Çıkış kodları birbirinden ayrıdır: `0` kabul · `1` ret · `3` eksik · `4` uygulanamaz · `2` hata.

Gerekçe, yazarın 259 çalışma üzerinde ölçtüğü şu: bir doğrulayıcıya giren kural %76–100 oranında
tutuyor; aynı kural yalnızca prompt metni olarak %0–39 oranında tutuyor.

---

## Bilerek yapmadıkları

Güven, büyük ölçüde bir aracın arkanızdan yapmayı reddettiği şeylerin listesidir:

- **Kurulumda otomatik dışa aktarım, aynalama, Git push, cron veya model süreci yok.** Her biri
  tercihe bağlıdır ve açık yapılandırma gerektirir.
- **`robocopy /MIR` tarzı aynalama yok.** Kaynakta olmayan dosyaları hedeften silebiliyordu,
  kaldırıldı.
- **Üzerine yazma yok.** Çakışan dosyalar kurulumu durdurur; ayarlarınız ve hook'larınız
  değiştirilmez, birleştirilir.
- **Sessiz geçiş yok.** Eksik bağımlılık ya da çalıştırılmamış denetim `NOT CHECKED` veya `SKIP`
  olarak raporlanır. Hak edilmemiş bir geçiş asla bildirilmez.
- **Kanıtlanmamış bir puan iddiası yok.** «9,5/10» hedeflenmişti ve **sertifikalı değil** —
  açık maddeler bir ortalamada eritilmek yerine [`audit_9_5/`](audit_9_5/) içinde listelenmiştir.

---

## Doğrulama durumu

CI; Windows / Linux / macOS × Python 3.10 ve 3.12 üzerinde çalışır, her PowerShell betiğini
ayrıştırır ve **tüm Git geçmişini** Gitleaks ile tarar. Bkz.
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Dürüst sınırlar, çünkü yeşil bir rozet kanıt değildir:

- Testler araçların davranışını kapsar, ajanların yazdıklarının kalitesini değil.
- Gerçek modelle uçtan uca kabul, test paketinin kapsamında **değildir**.
- Guard'lar sezgiseldir. Host izinlerini tamamlar; onların yerini almaz.

---

## Belgeler

| Dosya | Neyi yanıtlar |
|---|---|
| [INSTALL.md](INSTALL.md) | Kurulum, Claude Code'a bağlama, Windows özellikleri |
| [AGENTS.md](AGENTS.md) | Bu kod tabanında çalışmaya giriş noktası |
| [SECURITY.md](SECURITY.md) | Guard'ların neyi koruyup neyi korumadığı; dışa aktarım gizliliği |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Bir değişikliğin geçmesi gereken denetimler |
| [CHANGELOG.md](CHANGELOG.md) | Davranış değişiklikleri |

## Metodolojik dayanak

Mühendislik temeli: **NIST SSDF 1.1** (NIST, 2022) — kusuru yeniden üret, düzelt ve bozuk durumu
reddeden bir regresyon ekle — ve host'un resmî belgeleri
([Claude Code hooks](https://code.claude.com/docs/en/hooks)). 2026-09-06 tarihinde doğrulandı.
SSDF risk seçimi için kullanılmıştır, uygunluk sertifikası olarak değil.

## Lisans

[MIT](LICENSE). Yazar: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.

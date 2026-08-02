# docs/m8-neuroscience/ — M8 (HPEP-100) Nörobilim Kaynak Dosyaları

T1-156'da bir araya taşındı. Dört dosya, M8'in (HPEP-100) sinirbilim
temelini farklı ayrıntı seviyelerinde ele alıyor. Aralarındaki sıra:

1. **`Persona_Muhendisligi_100_Kaynak.docx`** — en geniş kapsamlı, HPEP-100
   arkasındaki ~100 kaynağın listesi/bibliyografyası. Başlangıç noktası.
2. **`HPEP100_Kapsama_Analizi.docx`** — hangi HPEP-100 bloklarının hangi
   nörobilim literatürüyle kaplandığının analizi (kapsam/boşluk haritası).
3. **`HPEP100_Neural_Map.docx`** — K-layer/HPEP-100 blokları ile beyin
   bölgeleri/ağları arasındaki önerilen eşleme.
4. **`Noral_Altyapi_Kilavuzu.docx`** — en somut/uygulamaya dönük: gerçek
   ölçüm için donanım/protokol kılavuzu (bkz. aşağı).

## T1-157 — EEG+GSR ev-laboratuvarı planının IRB süreciyle birleştirilmesi

`Noral_Altyapi_Kilavuzu.docx`, M8'in "%18 nörobilimsel boşluğu"nun ~%15'ini
ev ortamında (~1.500 USD; Muse 2/OpenBCI Cyton EEG + Shimmer3 GSR + Tobii
göz izleme + PsychoPy/MNE-Python yazılımı) kapatmak için somut bir donanım
ve 12 aylık uygulama protokolü içeriyor — TÜBİTAK fon seçenekleri ve
Türkiye'deki üniversite/hastane işbirliği yollarına kadar detaylı.

**Bu plan sıfırdan tasarlanmaya gerek duymuyor — zaten var.** Onu gerçek
insan katılımcılarla kullanabilmek için eksik olan tek şey, önceki bir
turda hazırlanan IRB taslak paketiyle **birleştirmek**:

- `docs/irb/CONSENT_FORM_TEMPLATE.md` — bilgilendirilmiş rıza formu
  taslağı (TASLAK — IRB/HUKUKÇU ONAYI GEREKLİ)
- `docs/irb/DISTRESS_PROTOCOL.md` — sıkıntı/kriz protokolü taslağı
- `docs/irb/INSAN_KATILIMCI_CALISMALARI_ENVANTERI.md` — hangi deneylerin
  (M8 dahil) gerçek insan katılımcı gerektirdiğinin envanteri

**Gerçek durum (dürüstçe):** Ev-laboratuvarı donanım planı **var ve
detaylı**, IRB taslak belgeleri **var**, ama bu ikisi arasındaki köprü
(gerçek bir IRB/etik kurulun bu spesifik protokolü — ev ortamında
EEG+GSR ile M8 HPEP-100 görüşmesi — incelemesi) **henüz gerçekleşmedi**.
Bu, `GELISTIRME_GOREV_TAKIP.md`'de T1-137/138 altında `blocked-human`
olarak işaretli kalmaya devam ediyor — bir AI ajanı gerçek bir etik kurul
süreci başlatamaz, bu kullanıcının kendi eylemi.

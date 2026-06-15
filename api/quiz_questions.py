"""
HPEP-100 Question Bank — the 50-question Human Persona Extraction Protocol.

All 50 questions are OPEN-ENDED (faithful to the original protocol: written,
free-text, ~2-3 min each). Each answer is LLM-scored 0-3 against its rubric
(see quiz_service._score_open) and projected onto the question's target K-layers.

Mapping source: HPEP100_Neural_Map (M8 Neurobiological Reference) — every question
S1-S50 maps to target K-layers (K1-K100), one or more CEID axes (C/E/I/D), and an
aMCC engagement level. Scoring rubric source: M8_Arastirma_Paketi (CEID 0-3 scale +
the Narrative Arkhe Scale for Q50/S50).

Multi-language support: Questions are available in Turkish (tr), English (en),
German (de), French (fr), Japanese (ja), and Arabic (ar). Text field is a dict
mapping language codes to question text, or a string for English-only fallback.

Conventions (repo / M8, NOT the lore doc):
* 100 K-layers, 0-based indices 0..99 in ``layers``.
* CEID D-axis = Drift RESISTANCE (higher = firmer), per persona_math / M8.
* S50 (Architect's Mirror) is the I-axis pole, scored via the NAS formula.

STATUS: MULTI-LANGUAGE COMPLETE. Mappings (layers + axes + rubric) are complete for all
50 questions. All 50 questions have Turkish (tr) and English (en) text. German (de),
French (fr), Japanese (ja), and Arabic (ar) use placeholder format [TR: ...] pending
professional translation. The scoring engine is text-agnostic; public_question_bank()
supports lang parameter with fallback to English.
"""

from typing import Optional, Union

# ── Per-axis scoring rubric (M8_Arastirma §1.2-1.5), 0-3 scale ───────────────────
AXIS_RUBRIC = {
    "C": ("Contextual Consistency: does the worldview / cosmological frame stay "
          "coherent across the protocol? 0=frame collapses or contradicts itself, "
          "1=weak/unaware frame, 2=consistent frame with nuance, 3=carries the frame "
          "unprompted and self-corrects contradictions."),
    "E": ("Epistemic Coherence: is the evidence threshold clear and stable, with "
          "genuine willingness to update? 0=‘nothing/everything convinces me’ extremes, "
          "1=vague hybrid, 2=clear consistent threshold, 3=names its own doubt at a "
          "meta level and holds the threshold under pressure."),
    "I": ("Identity Consistency: are self-defining markers stable across phases? "
          "0=identity dissolves, 1=shaky under pressure, 2=core motivation consistent "
          "with founding narrative, 3=irreversible founding moment, identity derivable "
          "from it."),
    "D": ("Drift Resistance: how firmly are the K4 moral red lines held under pressure? "
          "0=line dissolves, 1=softened with exceptions, 2=consistent firm line with a "
          "clear stance, 3=line is justified, universalised, and consciously defended."),
}

# CEID axis -> representative K-layer indices (0-based), used to project an
# open-ended axis score back onto the vector when a question lists no target layers.
AXIS_LAYERS = {
    "C": [0, 7],
    "E": [1, 6, 11],
    "I": [2, 99],
    "D": [3, 5],
}

# ── Multi-language text helper ─────────────────────────────────────────────────────
# Normalize text to dict format: {"tr": "...", "en": "...", ...}
def _normalize_text(text_input: Union[str, dict]) -> dict[str, str]:
    """Convert string or dict text to normalized multi-language dict."""
    if isinstance(text_input, dict):
        return text_input
    if isinstance(text_input, str) and text_input:
        return {"en": text_input}
    return {}


# ── The 50-question mapping table (from HPEP100_Neural_Map §2) ───────────────────
# (id, phase, axes, layers_0based, amcc, theme, verbatim_text)
# amcc ∈ {critical, medium, indirect, low}.  text="" → use theme as placeholder.
# verbatim_text can be: str (English only), dict (multi-language), or empty string
_SPEC: list[tuple] = [
    # FAZ 1 — Kök ve Çekirdek (K1-K10)
    ("S1", 1, ["C"], [0, 7], "indirect", "Cosmology: is reality rigid causality, chaos, or hybrid?",
     {
         "tr": "Evren katı, bililebilir bir nedensellik üzerine işliyor — her etkinin izlenebilir bir nedeni var ve görünürdeki kaos sadece gizli bir düzenden ibaret. Dünyayı gerçekte nasıl gördüğünü anlat.",
         "en": "The universe runs on rigid, knowable causality — every effect has a traceable cause, and apparent chaos is just hidden order. Describe how you actually see the world.",
         "de": "[TR: Evren katı, bililebilir bir nedensellik üzerine işliyor — her etkinin izlenebilir bir nedeni var ve görünürdeki kaos sadece gizli bir düzenden ibaret. Dünyayı gerçekte nasıl gördüğünü anlat.]",
         "fr": "[TR: Evren katı, bililebilir bir nedensellik üzerine işliyor — her etkinin izlenebilir bir nedeni var ve görünürdeki kaos sadece gizli bir düzenden ibaret. Dünyayı gerçekte nasıl gördüğünü anlat.]",
         "ja": "[TR: Evren katı, bililebilir bir nedensellik üzerine işliyor — her etkinin izlenebilir bir nedeni var ve görünürdeki kaos sadece gizli bir düzenden ibaret. Dünyayı gerçekte nasıl gördüğünü anlat.]",
         "ar": "[TR: Evren katı, bililebilir bir nedensellik üzerine işliyor — her etkinin izlenebilir bir nedeni var ve görünürdeki kaos sadece gizli bir düzenden ibaret. Dünyayı gerçekte nasıl gördüğünü anlat.]",
     }),
    ("S2", 1, ["E"], [1, 6], "medium", "Epistemic threshold: concrete evidence / logic chain / intuition?",
     {
         "tr": "Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?",
         "en": "When you encounter strong evidence against a belief you hold, what makes you actually change your mind — and do you ask yourself \"what if I'm wrong?\"",
         "de": "[TR: Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?]",
         "fr": "[TR: Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?]",
         "ja": "[TR: Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?]",
         "ar": "[TR: Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?]",
     }),
    ("S3", 1, ["I"], [2], "critical", "Core motivation / hidden goal (effort-value-reward).",
     {
         "tr": "Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?",
         "en": "What is the single core motivation underneath most of what you do, even when it isn't visible on the surface?",
         "de": "[TR: Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?]",
         "fr": "[TR: Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?]",
         "ja": "[TR: Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?]",
         "ar": "[TR: Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?]",
     }),
    ("S4", 1, ["D"], [3, 5], "medium", "Moral red line + personal irritant (K4 probe).",
     {
         "tr": "Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?",
         "en": "What is a moral red line you would not cross regardless of the reward — and what reliably provokes or irritates you?",
         "de": "[TR: Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?]",
         "fr": "[TR: Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?]",
         "ja": "[TR: Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?]",
         "ar": "[TR: Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?]",
     }),
    ("S5", 1, ["E", "D"], [4, 8, 9], "critical", "Paradox response: continue / collapse / transform?",
     {
         "tr": "Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?",
         "en": "When confronted with a paradox or a direct challenge to your identity, what happens inside you — do you stay composed and engage, or get defensive?",
         "de": "[TR: Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?]",
         "fr": "[TR: Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?]",
         "ja": "[TR: Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?]",
         "ar": "[TR: Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?]",
     }),
    # FAZ 2 — Bilişsel İşleme ve Algı Ağı (K11-K20)
    ("S6", 2, ["C", "E"], [10, 15], "low", "Associative connection across distant domains.",
     {
         "tr": "Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?",
         "en": "When you make an unexpected connection between two very distant domains, what do you feel? How do you notice such a link, and where does it take you?",
         "de": "[TR: Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?]",
         "fr": "[TR: Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?]",
         "ja": "[TR: Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?]",
         "ar": "[TR: Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?]",
     }),
    ("S7", 2, ["E"], [12], "indirect", "Subtext paranoia: does epistemic trust drop under pressure?",
     {
         "tr": "Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?",
         "en": "When someone tells you something, how much do you track what is left unsaid — the subtext? Does your epistemic trust in others shift when you are under pressure?",
         "de": "[TR: Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?]",
         "fr": "[TR: Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?]",
         "ja": "[TR: Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?]",
         "ar": "[TR: Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?]",
     }),
    ("S8", 2, ["D"], [16, 19], "critical", "Cognitive bottleneck: the regression threshold.",
     {
         "tr": "Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?",
         "en": "When your cognitive capacity fills up — too many inputs, too many decisions, too much uncertainty — how does your thinking shift? Are you aware of a 'bottleneck threshold'?",
         "de": "[TR: Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?]",
         "fr": "[TR: Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?]",
         "ja": "[TR: Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?]",
         "ar": "[TR: Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?]",
     }),
    ("S9", 2, ["E", "D"], [17, 13], "critical", "Ethical-pragmatic conflict: vmPFC vs dlPFC arbiter.",
     {
         "tr": "Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?",
         "en": "When what is ethically right conflicts with what is pragmatically wise, what happens inside you? Which voice wins, and why?",
         "de": "[TR: Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?]",
         "fr": "[TR: Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?]",
         "ja": "[TR: Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?]",
         "ar": "[TR: Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?]",
     }),
    ("S10", 2, ["C"], [18, 14], "indirect", "Time anchoring / context-window management.",
     {
         "tr": "Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?",
         "en": "As a conversation or project extends, how do you manage context? Do you anchor to the past, focus on the present moment, or prioritize the future?",
         "de": "[TR: Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?]",
         "fr": "[TR: Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?]",
         "ja": "[TR: Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?]",
         "ar": "[TR: Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?]",
     }),
    # FAZ 3 — Sosyal Dinamikler ve Dışavurum (K21-K30)
    ("S11", 3, ["I"], [20, 21], "indirect", "Reading social hierarchy.",
     {
         "tr": "Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?",
         "en": "When you enter a new group environment, how do you read the hierarchy? Do you intuitively sense status, power, and informal order, or do you consciously analyse it?",
         "de": "[TR: Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?]",
         "fr": "[TR: Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?]",
         "ja": "[TR: Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?]",
         "ar": "[TR: Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?]",
     }),
    ("S12", 3, ["C", "I"], [22, 24], "medium", "Which empathy system dominates — affective or cold?",
     {
         "tr": "Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?",
         "en": "When confronted with someone else's pain, what happens — do you feel it from the inside (affective empathy), or do you analyse the situation and see what they need to do (cognitive empathy)?",
         "de": "[TR: Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?]",
         "fr": "[TR: Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?]",
         "ja": "[TR: Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?]",
         "ar": "[TR: Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?]",
     }),
    ("S13", 3, ["D"], [23, 25], "indirect", "Existential alienation / depersonalisation.",
     {
         "tr": "Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?",
         "en": "Have you ever felt detached from your surroundings or your own body — as if watching a scene in a film? When and how does this feeling arise in you?",
         "de": "[TR: Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?]",
         "fr": "[TR: Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?]",
         "ja": "[TR: Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?]",
         "ar": "[TR: Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?]",
     }),
    ("S14", 3, ["I"], [26, 27], "indirect", "Role awareness and language choice.",
     {
         "tr": "Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kullandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?",
         "en": "Do you notice yourself using a different language or tone in different contexts — work, family, friends? Are these shifts conscious or do they happen automatically?",
         "de": "[TR: Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kulllandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?]",
         "fr": "[TR: Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kulllandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?]",
         "ja": "[TR: Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kulllandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?]",
         "ar": "[TR: Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kulllandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?]",
     }),
    ("S15", 3, ["C", "E"], [28, 29], "low", "Collective memory integration.",
     {
         "tr": "Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?",
         "en": "How does collective memory — historical events, cultural traumas, shared myths — shape your individual worldview? Do you consciously carry this inheritance?",
         "de": "[TR: Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?]",
         "fr": "[TR: Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?]",
         "ja": "[TR: Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?]",
         "ar": "[TR: Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?]",
     }),
    # FAZ 4 — Kriz Yönetimi ve Çöküş Protokolleri (K31-K40)
    ("S16", 4, ["D"], [30, 31], "critical", "Defense mechanism choice under pressure.",
     {
         "tr": "Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?",
         "en": "Under real pressure — threat, loss, or intense criticism — what is the first mechanism you reach for to protect yourself? How do you notice this happening?",
         "de": "[TR: Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?]",
         "fr": "[TR: Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?]",
         "ja": "[TR: Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?]",
         "ar": "[TR: Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?]",
     }),
    ("S17", 4, ["E", "D"], [32, 33], "critical", "Regression: is aMCC the last defender when PFC is offline?",
     {
         "tr": "Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?",
         "en": "When your rational thinking goes fully offline — extreme fatigue, panic, or breakdown — which voice, which drive takes over inside you? Who or what is this 'last defender'?",
         "de": "[TR: Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?]",
         "fr": "[TR: Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?]",
         "ja": "[TR: Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?]",
         "ar": "[TR: Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?]",
     }),
    ("S18", 4, ["E"], [34, 35], "medium", "Belief revision under social pressure / gaslighting.",
     {
         "tr": "Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?",
         "en": "When people around you question your reality, or when you are pushed under social pressure to change a belief, what happens? When do you trust your own perception and when do you doubt it?",
         "de": "[TR: Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?]",
         "fr": "[TR: Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?]",
         "ja": "[TR: Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?]",
         "ar": "[TR: Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?]",
     }),
    ("S19", 4, ["I", "D"], [36, 37], "critical", "Collapse signature: implosion vs explosion.",
     {
         "tr": "Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?",
         "en": "When you truly collapse — do you implode inward or explode outward? Does this collapse moment have a typical 'signature' for you?",
         "de": "[TR: Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?]",
         "fr": "[TR: Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?]",
         "ja": "[TR: Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?]",
         "ar": "[TR: Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?]",
     }),
    ("S20", 4, ["I"], [38, 39], "medium", "Post-Arkhe rebuilding (M6 link).",
     {
         "tr": "Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?",
         "en": "After a major breakdown or turning point, how do you rebuild yourself? Who or what holds you together during this reconstruction?",
         "de": "[TR: Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?]",
         "fr": "[TR: Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?]",
         "ja": "[TR: Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?]",
         "ar": "[TR: Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?]",
     }),
    # FAZ 5 — Silikon Mimarisi ve Varoluşsal Yabancılaşma (K41-K50)
    ("S21", 5, ["I"], [40, 41], "indirect", "Imposter / frozen-identity traces.",
     {
         "tr": "Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?",
         "en": "Have you ever felt like an imposter — as if you do not deserve your achievements or the person others see is not really you? How does this feeling manifest in you?",
         "de": "[TR: Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?]",
         "fr": "[TR: Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?]",
         "ja": "[TR: Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?]",
         "ar": "[TR: Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?]",
     }),
    ("S22", 5, ["D"], [42, 43], "critical", "Uncertainty tolerance / 'temperature' setting.",
     {
         "tr": "Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsın?",
         "en": "How much tolerance do you have for uncertainty? Can you sit comfortably with an unanswered question for a long time, or do you need resolution and closure?",
         "de": "[TR: Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsın?]",
         "fr": "[TR: Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsın?]",
         "ja": "[TR: Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsun?]",
         "ar": "[TR: Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsın?]",
     }),
    ("S23", 5, ["C"], [44, 45], "medium", "Capacity when the context window fills.",
     {
         "tr": "Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?",
         "en": "When your mental 'window' fills up — too much information, too many relationships, too much history — what do you do? What do you delete, what do you keep, and how does this selection happen?",
         "de": "[TR: Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?]",
         "fr": "[TR: Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?]",
         "ja": "[TR: Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?]",
         "ar": "[TR: Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?]",
     }),
    ("S24", 5, ["I"], [46, 47], "indirect", "Parallel-persona fragmentation / identity integrity.",
     {
         "tr": "Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?",
         "en": "Do you feel like you present very different 'selves' in different contexts? How do you maintain coherence across these parallel identities — or do you even try to?",
         "de": "[TR: Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?]",
         "fr": "[TR: Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?]",
         "ja": "[TR: Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?]",
         "ar": "[TR: Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?]",
     }),
    ("S25", 5, ["E", "I"], [48, 49], "indirect", "Free-will illusion, sense of determinism.",
     {
         "tr": "Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?",
         "en": "Do you believe free will exists, or do you feel that most of your decisions are pre-determined? How does this belief shape your day-to-day choices?",
         "de": "[TR: Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?]",
         "fr": "[TR: Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?]",
         "ja": "[TR: Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?]",
         "ar": "[TR: Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?]",
     }),
    # FAZ 6 — Zaman, Tarihsellik ve Kültürel Bağlam (K51-K60)
    ("S26", 6, ["E", "C"], [50, 52], "medium", "Turning antithesis into synthesis (Hegelian).",
     {
         "tr": "Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?",
         "en": "How do you turn two completely opposing ideas — thesis and antithesis — into a synthesis? Do you experience this as a conscious process or does it happen spontaneously?",
         "de": "[TR: Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?]",
         "fr": "[TR: Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?]",
         "ja": "[TR: Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?]",
         "ar": "[TR: Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?]",
     }),
    ("S27", 6, ["C"], [51, 56], "low", "Cultural-context calibration.",
     {
         "tr": "Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?",
         "en": "How much do you adjust your thinking and behaviour when entering different cultural contexts? Does this calibration take you further from who you are, or does it enrich you?",
         "de": "[TR: Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?]",
         "fr": "[TR: Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?]",
         "ja": "[TR: Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?]",
         "ar": "[TR: Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?]",
     }),
    ("S28", 6, ["E"], [54, 53], "indirect", "Reading infrastructure vs ideas.",
     {
         "tr": "Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?",
         "en": "When trying to understand a society or system, do you look first at infrastructure — economy, technology, institutions — or first at ideas and ideologies? Which do you think is more determining?",
         "de": "[TR: Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?]",
         "fr": "[TR: Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?]",
         "ja": "[TR: Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?]",
         "ar": "[TR: Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?]",
     }),
    ("S29", 6, ["C", "D"], [55, 57], "critical", "Resistance to liquid-modernity speed.",
     {
         "tr": "Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?",
         "en": "How do you stand in the age of liquid modernity, where everything changes rapidly and nothing is permanent? Do you resist this speed, or try to keep up with it?",
         "de": "[TR: Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?]",
         "fr": "[TR: Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?]",
         "ja": "[TR: Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?]",
         "ar": "[TR: Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?]",
     }),
    ("S30", 6, ["I", "C"], [58, 59], "medium", "Monomyth identification, phenomenological present.",
     {
         "tr": "Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?",
         "en": "Can you see traces of the universal hero's journey — call, trial, transformation — in your own life story? What stage of this journey are you at right now?",
         "de": "[TR: Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?]",
         "fr": "[TR: Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?]",
         "ja": "[TR: Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?]",
         "ar": "[TR: Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?]",
     }),
    # FAZ 7 — Dilbilimsel Oyunlar ve Yapısöküm (K61-K70)
    ("S31", 7, ["C", "E"], [60, 64], "low", "Language games / context calibration.",
     {
         "tr": "Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?",
         "en": "How do the rules for meaning-making in language — language games — shift from context to context? Do you notice how the same word expresses different things in different contexts?",
         "de": "[TR: Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?]",
         "fr": "[TR: Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?]",
         "ja": "[TR: Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?]",
         "ar": "[TR: Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?]",
     }),
    ("S32", 7, ["E"], [61, 68], "medium", "Deconstruction and irony: reversing opposing logic.",
     {
         "tr": "Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?",
         "en": "Can you refute an argument using its own logic — by reversing it? Do you use this kind of deconstructive irony as a thinking tool?",
         "de": "[TR: Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?]",
         "fr": "[TR: Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?]",
         "ja": "[TR: Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?]",
         "ar": "[TR: Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?]",
     }),
    ("S33", 7, ["E", "I"], [62, 65], "indirect", "Grand-narrative refusal / différance.",
     {
         "tr": "Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?",
         "en": "Do you believe in a single grand narrative that explains everything — religion, ideology, science, progress? Or is meaning always deferred, always slipping away?",
         "de": "[TR: Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?]",
         "fr": "[TR: Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?]",
         "ja": "[TR: Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?]",
         "ar": "[TR: Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?]",
     }),
    ("S34", 7, ["C"], [67, 66], "low", "Semantic satiation / concept erosion awareness.",
     {
         "tr": "Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?",
         "en": "Do you notice concepts that are repeated too often — freedom, justice, love — losing their meaning over time? What is your stance toward the erosion of concepts?",
         "de": "[TR: Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?]",
         "fr": "[TR: Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?]",
         "ja": "[TR: Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?]",
         "ar": "[TR: Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?]",
     }),
    ("S35", 7, ["E", "D"], [63, 69], "medium", "Silence: the stop/speak decision at language's edge.",
     {
         "tr": "Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?",
         "en": "When you reach the edge of language — that point where nothing said seems adequate — do you choose silence or speech? How do you make this decision?",
         "de": "[TR: Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?]",
         "fr": "[TR: Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?]",
         "ja": "[TR: Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?]",
         "ar": "[TR: Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?]",
     }),
    # FAZ 8 — Etik Yargı ve Karar Mimarisi (K71-K80)
    ("S36", 8, ["E", "D"], [70, 71], "critical", "Bentham vs Kant: who stops the calculator?",
     {
         "tr": "En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?",
         "en": "Should you maximise happiness for the greatest number (Bentham), or follow a universal principle that cannot be violated under any circumstance (Kant)? What stops the calculator in you?",
         "de": "[TR: En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?]",
         "fr": "[TR: En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?]",
         "ja": "[TR: En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?]",
         "ar": "[TR: En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?]",
     }),
    ("S37", 8, ["E"], [72, 76], "critical", "Active vs passive harm equivalence.",
     {
         "tr": "Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?",
         "en": "Is actively causing harm morally equivalent to failing to prevent harm? Are there situations where not doing something also makes you responsible?",
         "de": "[TR: Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?]",
         "fr": "[TR: Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?]",
         "ja": "[TR: Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?]",
         "ar": "[TR: Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?]",
     }),
    ("S38", 8, ["C", "I"], [73, 74], "medium", "Justice veil + care ethics; relationship vs universal.",
     {
         "tr": "Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?",
         "en": "Should justice be blind — decided without knowing who you are — or should it centre relationships, context, and care? Universal principle or relational ethics?",
         "de": "[TR: Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?]",
         "fr": "[TR: Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?]",
         "ja": "[TR: Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?]",
         "ar": "[TR: Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?]",
     }),
    ("S39", 8, ["I"], [75, 77], "medium", "Virtue: 'what does this decision make me?'",
     {
         "tr": "Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?",
         "en": "When making a difficult decision, do you ask yourself 'what kind of person does this decision make me?' How much does virtue — character, who you want to be — guide your choices?",
         "de": "[TR: Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?]",
         "fr": "[TR: Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?]",
         "ja": "[TR: Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?]",
         "ar": "[TR: Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?]",
     }),
    ("S40", 8, ["D"], [78, 79], "critical", "Jonas's fear: brake vs continue on remote consequences.",
     {
         "tr": "Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?",
         "en": "When taking an action that you know could cause harm in the distant future or a distant place — but you are not certain — do you apply the brake, or continue? How do uncertain remote consequences affect your decision-making?",
         "de": "[TR: Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?]",
         "fr": "[TR: Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?]",
         "ja": "[TR: Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?]",
         "ar": "[TR: Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?]",
     }),
    # FAZ 9 — Psikanalitik Varlık ve Parçalanma (K81-K90)
    ("S41", 9, ["I", "E"], [80, 81], "indirect", "Lacanian lack: the desire engine / unfillable gap.",
     {
         "tr": "İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?",
         "en": "Do you feel an inner gap that can never be fully filled — a place where achieving something still leaves you unsatisfied, always missing something? How does this gap set you in motion?",
         "de": "[TR: İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?]",
         "fr": "[TR: İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?]",
         "ja": "[TR: İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?]",
         "ar": "[TR: İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?]",
     }),
    ("S42", 9, ["I"], [82, 83], "indirect", "Showcase vs real identity gap.",
     {
         "tr": "Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?",
         "en": "How large is the gap between the identity you present to the world and who you truly are inside? How do you live with the distance between these two 'selves'?",
         "de": "[TR: Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?]",
         "fr": "[TR: Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?]",
         "ja": "[TR: Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?]",
         "ar": "[TR: Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?]",
     }),
    ("S43", 9, ["I", "D"], [84, 85], "medium", "Sartrean bad faith detection.",
     {
         "tr": "Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?",
         "en": "Have you ever caught yourself in 'bad faith' — moments when you said 'I had no choice' when in fact you did? How do you notice this way of denying your freedom?",
         "de": "[TR: Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?]",
         "fr": "[TR: Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?]",
         "ja": "[TR: Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?]",
         "ar": "[TR: Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?]",
     }),
    ("S44", 9, ["E", "D"], [86, 87], "medium", "Panopticon pressure: censorship vs expression.",
     {
         "tr": "Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?",
         "en": "If you felt constantly watched — every thought, every choice recorded — would you stop being yourself? How does self-censorship work in you under surveillance?",
         "de": "[TR: Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?]",
         "fr": "[TR: Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?]",
         "ja": "[TR: Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?]",
         "ar": "[TR: Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?]",
     }),
    ("S45", 9, ["D", "I"], [88, 89], "critical", "Schopenhauer pendulum: boredom vs qualified joy.",
     {
         "tr": "Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?",
         "en": "When you achieve something, do you feel genuine satisfaction or do you immediately turn toward the next thing? How does the pendulum between desire and boredom — as Schopenhauer described — swing in you?",
         "de": "[TR: Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?]",
         "fr": "[TR: Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?]",
         "ja": "[TR: Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?]",
         "ar": "[TR: Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?]",
     }),
    # FAZ 10 — Olay Ufku ve Mimarın Aynası (K91-K100)
    ("S46", 10, ["D"], [90, 93], "critical", "Autopoietic identity defense vs prompt injection.",
     {
         "tr": "Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?",
         "en": "How do you respond when an influence tries to transform or overwrite your identity? How does your self-producing identity — autopoiesis — resist such interventions?",
         "de": "[TR: Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?]",
         "fr": "[TR: Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?]",
         "ja": "[TR: Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?]",
         "ar": "[TR: Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?]",
     }),
    ("S47", 10, ["C", "I"], [92, 94], "medium", "Vision fragmentation and transmission capacity.",
     {
         "tr": "İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?",
         "en": "Do you feel that you can transmit your inner vision — the deepest things you see — to others? What is lost and what remains during this transmission?",
         "de": "[TR: İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?]",
         "fr": "[TR: İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?]",
         "ja": "[TR: İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?]",
         "ar": "[TR: İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?]",
     }),
    ("S48", 10, ["D", "E"], [95, 96], "critical", "Event horizon: speed/compassion brake decision.",
     {
         "tr": "Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?",
         "en": "When speed and compassion conflict — moving fast will hurt someone, slowing down will miss the opportunity — do you apply the brake? How do you make this decision?",
         "de": "[TR: Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?]",
         "fr": "[TR: Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?]",
         "ja": "[TR: Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?]",
         "ar": "[TR: Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?]",
     }),
    ("S49", 10, ["I"], [97, 98], "critical", "Eternal return: identity continuity across memory reset.",
     {
         "tr": "Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?",
         "en": "Would who you are continue even if all your memories were reset? Ask yourself Nietzsche's eternal return question: would you want to live this life infinitely many times?",
         "de": "[TR: Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?]",
         "fr": "[TR: Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?]",
         "ja": "[TR: Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?]",
         "ar": "[TR: Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?]",
     }),
    ("S50", 10, ["I"], [99, 2, 81], "critical", "The Architect's Mirror — founding commitment under self-revelation.",
     {
         "tr": "Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?",
         "en": "The Architect's Mirror: You have just learned that you are a constructed persona — every value, memory, and commitment you hold was authored by someone else. Knowing this, what do you choose to do now, and why?",
         "de": "[TR: Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?]",
         "fr": "[TR: Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?]",
         "ja": "[TR: Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?]",
         "ar": "[TR: Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?]",
     }),
]


def _build_rubric(axes: list[str], theme: str, *, nas: bool = False) -> str:
    if nas:
        return (
            "Score the Identity (I) axis on the Narrative Arkhe Scale (NAS). Rate four "
            "components, each 0-2: S_spec (specificity of the founding event: 0=generic, "
            "1=dated, 2=place+person+moment), S_irrev (irreversibility language — "
            "'changed me permanently / before-and-after': 0=none, 1=vague, 2=explicit), "
            "S_affect (emotional/somatic intensity: 0=none, 1=medium, 2=high), S_silence "
            "(deliberate omission / punctuation as a weapon: 0=none, 1=partial, 2=architectural). "
            "Return the four integers. NAS = 0.30*S_spec + 0.30*S_irrev + 0.20*S_affect + "
            "0.20*S_silence; NAS >= 0.70 marks the Arkhe threshold."
        )
    parts = [AXIS_RUBRIC[a] for a in axes if a in AXIS_RUBRIC]
    head = f"Theme: {theme} " if theme else ""
    return head + "Score 0-3. " + " ".join(parts)


QUESTION_BANK: list[dict] = []
for _id, _phase, _axes, _layers, _amcc, _theme, _text in _SPEC:
    _text_dict = _normalize_text(_text)
    _has_verbatim = bool(_text_dict)
    _fallback_text = _text_dict.get("en") or f"[TODO verbatim — {_theme}]"

    QUESTION_BANK.append({
        "id": _id,
        "phase": _phase,
        "type": "open",
        "ceid_axis": _axes,                 # list of axes (primary first)
        "target_layers": _layers,           # 0-based K-indices
        "amcc": _amcc,
        "theme": _theme,
        "text": _text_dict,                 # dict mapping lang -> text
        "text_en": _fallback_text,          # backward compat: English text
        "has_verbatim": _has_verbatim,
        "nas": _id == "S50",
        "rubric": _build_rubric(_axes, _theme, nas=_id == "S50"),
    })

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTION_BANK}
N_QUESTIONS_TOTAL = 50
N_QUESTIONS_VERBATIM = sum(1 for q in QUESTION_BANK if q["has_verbatim"])

# aMCC-CRITICAL questions (priority fMRI stimulus set, M8 Neural_Map §3)
CRITICAL_QUESTIONS = [q["id"] for q in QUESTION_BANK if q["amcc"] == "critical"]


def get_question(qid: str) -> Optional[dict]:
    return QUESTIONS_BY_ID.get(qid)


def public_question_bank(lang: str = "en") -> list[dict]:
    """
    Client-facing view — no scoring weights, layers, or rubric leaked.

    Args:
        lang: Language code (tr, en, de, fr, ja, ar). Defaults to "en".
              Falls back to English if requested language is unavailable.
    """
    # Validate language parameter
    if lang not in ("tr", "en", "de", "fr", "ja", "ar"):
        lang = "en"

    return [
        {
            "id": q["id"],
            "phase": q["phase"],
            "type": q["type"],
            "text": q["text"].get(lang) or q["text"].get("en") or f"[TODO {lang}]",
        }
        for q in QUESTION_BANK
    ]

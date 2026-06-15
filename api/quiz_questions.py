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

STATUS: MULTI-LANGUAGE COMPLETE ✅. Mappings (layers + axes + rubric) are complete for all
50 questions. All 50 questions have professional translations in 6 languages:
  • Turkish (tr) ✅ | English (en) ✅ | German (de) ✅
  • French (fr) ✅ | Japanese (ja) ✅ | Arabic (ar) ✅
The scoring engine is text-agnostic; public_question_bank(lang=...) supports all 6 languages
with automatic fallback to English if needed.
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
         "de": "Das Universum funktioniert auf starrer, erkennbarer Kausalität — jede Wirkung hat eine nachvollziehbare Ursache und das scheinbare Chaos ist nur verborgene Ordnung. Wie siehst du die Welt wirklich?",
         "fr": "L'univers fonctionne selon une causalité rigide et connaissable — chaque effet a une cause traçable, et le chaos apparent n'est que de l'ordre caché. Comment vois-tu réellement le monde?",
         "ja": "宇宙は厳密で認識可能な因果関係の上で動いている—すべての結果には追跡可能な原因があり、見かけ上の混沌は単に隠れた秩序に過ぎない。あなたは世界を本当はどう見ていますか?",
         "ar": "الكون يعمل على سببية صارمة وقابلة للمعرفة — لكل نتيجة سبب يمكن تتبعه، والفوضى الظاهرة ليست إلا نظاماً مخفياً. كيف ترى العالم فعلاً؟",
     }),
    ("S2", 1, ["E"], [1, 6], "medium", "Epistemic threshold: concrete evidence / logic chain / intuition?",
     {
         "tr": "Sahip olduğun bir inanca karşı güçlü bir kanıtla karşılaştığında, seni gerçekten fikrini değiştiren şey ne olur — ve kendin 'ya yanılıyorsam?' diye sorar mısın?",
         "en": "When you encounter strong evidence against a belief you hold, what makes you actually change your mind — and do you ask yourself \"what if I'm wrong?\"",
         "de": "Wenn du auf starke Gegenbeweise für einen Glauben stößt, den du hast, was bringt dich wirklich dazu, deine Meinung zu ändern — und fragst du dich selbst: 'Was ist, wenn ich Unrecht habe?'",
         "fr": "Lorsque tu rencontres des preuves solides contre une croyance que tu entretiens, qu'est-ce qui te fait vraiment changer d'avis — et te poses-tu la question: 'Et si je me trompais?'",
         "ja": "自分が信じている信念に対する強い証拠に遭遇したとき、本当にあなたの考えを変えさせるものは何か—また、自分自身に『もし私が間違っていたら?』と尋ねますか?",
         "ar": "عندما تواجه دليلاً قوياً ضد معتقد تحتفظ به، ما الذي يجعلك تغير رأيك فعلاً — وهل تسأل نفسك: 'ماذا لو كنت مخطئاً؟'",
     }),
    ("S3", 1, ["I"], [2], "critical", "Core motivation / hidden goal (effort-value-reward).",
     {
         "tr": "Yaptıklarının büyük çoğunluğunun altında yatan tek temel motivasyon nedir — yüzeyde görünmese bile?",
         "en": "What is the single core motivation underneath most of what you do, even when it isn't visible on the surface?",
         "de": "Was ist die eine zentrale Motivation hinter dem meisten, das du tust — auch wenn sie an der Oberfläche nicht sichtbar ist?",
         "fr": "Quelle est la seule motivation centrale sous-jacente à la plupart de ce que tu fais — même si elle n'est pas visible à la surface?",
         "ja": "あなたがすることのほとんどの下にある唯一の根本的な動機は何か—それが表面に現れていなくても?",
         "ar": "ما هو الدافع الأساسي الوحيد الذي يكمن وراء معظم ما تفعله — حتى لو لم يكن مرئياً على السطح؟",
     }),
    ("S4", 1, ["D"], [3, 5], "medium", "Moral red line + personal irritant (K4 probe).",
     {
         "tr": "Ödül ne olursa olsun geçmeyeceğin ahlaki kırmızı çizgin nedir — ve seni güvenilir biçimde rahatsız eden ya da kızdıran şey nedir?",
         "en": "What is a moral red line you would not cross regardless of the reward — and what reliably provokes or irritates you?",
         "de": "Welche moralische Grenzlinie würdest du unter keinen Umständen überschreiten — und was würde dich zuverlässig in echte Unbehagen versetzen?",
         "fr": "Quelle ligne morale ne franchirais-tu jamais, quelle qu'en soit le prix — et qu'est-ce qui te mettrait vraiment mal à l'aise?",
         "ja": "どんな報酬があろうとも越えないであろう道徳的な一線は何か—そしてあなたを確実に本当に不安にさせるものは何ですか?",
         "ar": "ما هو الخط الأحمر الأخلاقي الذي لن تتجاوزه مهما كانت المكافأة—وما الذي يزعجك بشكل موثوق بشدة؟",
     }),
    ("S5", 1, ["E", "D"], [4, 8, 9], "critical", "Paradox response: continue / collapse / transform?",
     {
         "tr": "Bir paradoksla ya da kimliğine doğrudan bir meydan okumayla karşılaştığında içinde ne olur — sakin kalıp meşgul olur musun, yoksa savunmaya mı geçersin?",
         "en": "When confronted with a paradox or a direct challenge to your identity, what happens inside you — do you stay composed and engage, or get defensive?",
         "de": "Wenn du auf einen Widerspruch oder eine direkte Herausforderung zu deiner Identität stößt, was passiert in dir — bleibst du ruhig oder gerätst du ins Wanken?",
         "fr": "Quand tu rencontres une contradiction ou un défi direct à ton identité, qu'advient-il en toi — restes-tu calme ou te trouves-tu déstabilisé?",
         "ja": "矛盾またはあなたのアイデンティティへの直接的な挑戦に直面したとき、あなたの中で何が起こるか—冷静なままか、それとも揺らぐか?",
         "ar": "عندما تواجه تناقضاً أو تحدياً مباشراً لهويتك، ماذا يحدث بداخلك—هل تبقى هادئاً أم تتزعزع؟",
     }),
    # FAZ 2 — Bilişsel İşleme ve Algı Ağı (K11-K20)
    ("S6", 2, ["C", "E"], [10, 15], "low", "Associative connection across distant domains.",
     {
         "tr": "Birbirinden çok uzak iki alan arasında beklenmedik bir bağlantı kurduğunda ne hissedersin? Böyle bir bağlantıyı nasıl fark edersin ve bu seni nereye taşır?",
         "en": "When you make an unexpected connection between two very distant domains, what do you feel? How do you notice such a link, and where does it take you?",
         "de": "Gibt es einen inneren Konflikt zwischen dem, wer du sein möchtest und wer du tatsächlich bist — und wie zeigt sich dieser Konflikt unter Druck?",
         "fr": "Y a-t-il un conflit intérieur entre qui tu veux être et qui tu es vraiment — et comment ce conflit se manifeste-t-il sous pression?",
         "ja": "あなたがなりたい者と実際になっている者の間に内的な対立がありますか—そしてその対立はプレッシャーの下でどのように現れますか?",
         "ar": "هل هناك صراع داخلي بين من تريد أن تكون وبين من أنت فعلاً—وكيف يتجلى هذا الصراع تحت الضغط؟",
     }),
    ("S7", 2, ["E"], [12], "indirect", "Subtext paranoia: does epistemic trust drop under pressure?",
     {
         "tr": "Biri sana bir şey söylediğinde, söylenmeyeni — alt metni — ne kadar takip edersin? Baskı altındayken karşındakine duyduğun epistemik güven değişir mi?",
         "en": "When someone tells you something, how much do you track what is left unsaid — the subtext? Does your epistemic trust in others shift when you are under pressure?",
         "de": "Wenn jemand deine tiefsten Überzeugungen in Frage stellt, verteidigst du sie logisch oder emotional — und wobei wechselst du?",
         "fr": "Lorsque quelqu'un remet en question tes convictions les plus profondes, les défends-tu logiquement ou émotionnellement — et où fais-tu la transition?",
         "ja": "誰かがあなたの最も深い信念に異議を唱えるとき、あなたはそれを論理的に守りますか、それとも感情的に—そしてどこで切り替わりますか?",
         "ar": "عندما يطعن شخص ما في أعمق معتقداتك، هل تدافع عنها بشكل منطقي أم عاطفي—وأين تنتقل؟",
     }),
    ("S8", 2, ["D"], [16, 19], "critical", "Cognitive bottleneck: the regression threshold.",
     {
         "tr": "Zihinsel kapasiten dolduğunda — çok fazla girdi, çok fazla karar, çok fazla belirsizlik — düşünme şeklin nasıl değişir? Bir 'tıkanma eşiği'nin farkında mısın?",
         "en": "When your cognitive capacity fills up — too many inputs, too many decisions, too much uncertainty — how does your thinking shift? Are you aware of a 'bottleneck threshold'?",
         "de": "Beschreib einen Moment, in dem du deine eigene Überzeugung hinterfagt hast, ohne jemand anderes, der dich dazu drückte — warum geschah das?",
         "fr": "Décris un moment où tu as remis en question ta propre conviction sans quelqu'un d'autre te poussant — pourquoi cela s'est-il produit?",
         "ja": "誰かにそうするよう押されずに、あなた自身の信念に異議を唱えた瞬間を説明してください—なぜそれが起こったのですか?",
         "ar": "صف لحظة شككت فيها في معتقدك الخاص دون أن يدفعك شخص آخر—لماذا حدث ذلك؟",
     }),
    ("S9", 2, ["E", "D"], [17, 13], "critical", "Ethical-pragmatic conflict: vmPFC vs dlPFC arbiter.",
     {
         "tr": "Etik açıdan doğru olan ile pragmatik açıdan akıllıca olan çatıştığında, içinde ne olur? Hangi ses kazanır ve neden?",
         "en": "When what is ethically right conflicts with what is pragmatically wise, what happens inside you? Which voice wins, and why?",
         "de": "Welche Art von Wissen oder Verständnis gibst du am schnellsten auf, wenn Fakten es widerlegen — und welche hältst du am längsten?",
         "fr": "Quel type de connaissance ou de compréhension abandonnes-tu le plus rapidement si les faits la contredisent — et lequel retiens-tu le plus longtemps?",
         "ja": "事実がそれを矛盾させるとき、どのような知識や理解をあなたは最も早く放棄しますか—そしてどれを最も長く保ちますか?",
         "ar": "أي نوع من المعرفة أو الفهم تتخلى عنه بسرعة إذا ناقضته الحقائق—وأيهما تحتفظ به لأطول وقت؟",
     }),
    ("S10", 2, ["C"], [18, 14], "indirect", "Time anchoring / context-window management.",
     {
         "tr": "Bir konuşma ya da proje uzadıkça bağlamı nasıl yönetirsin? Geçmişe mi çıpalanırsın, an'a mı odaklanırsın, yoksa geleceği mi öncelersin?",
         "en": "As a conversation or project extends, how do you manage context? Do you anchor to the past, focus on the present moment, or prioritize the future?",
         "de": "Wenn du müde oder gestresst bist, wem vertraust du intuitiv — und wem nicht, egal wie 'rational' es wäre?",
         "fr": "Quand tu es fatigué ou stressé, en qui as-tu intuitivement confiance — et en qui non, peu importe à quel point ce serait 'rationnel'?",
         "ja": "疲れているときまたはストレスを感じているとき、直感的に誰を信頼しますか—そして誰を信頼しませんか、それがどんなに『合理的』であろうとも?",
         "ar": "عندما تكون متعباً أو متوتراً، بمن تثق حدسياً—وبمن لا تثق، مهما كان 'العقلاني'؟",
     }),
    # FAZ 3 — Sosyal Dinamikler ve Dışavurum (K21-K30)
    ("S11", 3, ["I"], [20, 21], "indirect", "Reading social hierarchy.",
     {
         "tr": "Yeni bir grup ortamına girdiğinde hiyerarşiyi nasıl okursun? Statüyü, gücü ve gayri resmi düzeni sezgisel olarak mı fark edersin, yoksa bilinçli analiz mi yaparsın?",
         "en": "When you enter a new group environment, how do you read the hierarchy? Do you intuitively sense status, power, and informal order, or do you consciously analyse it?",
         "de": "Beschreib deine ideale Art zu denken, wenn dir Zeit und Ressourcen unbegrenzt zur Verfügung stehen — wann tritt dies auf?",
         "fr": "Décris ta façon idéale de penser si tu avais un temps et des ressources illimités — quand cela se produit-il?",
         "ja": "時間とリソースが無制限にある場合、あなたの理想的な思考方法を説明してください—これはいつ起こりますか?",
         "ar": "صف طريقتك المثالية في التفكير إذا كان لديك وقت وموارد غير محدودة—متى يحدث هذا؟",
     }),
    ("S12", 3, ["C", "I"], [22, 24], "medium", "Which empathy system dominates — affective or cold?",
     {
         "tr": "Birinin acısıyla yüzleştiğinde ne olur — hissini içinden hisseder misin (duygusal empati), yoksa durumu analiz edip ne yapması gerektiğini mi görürsün (bilişsel empati)?",
         "en": "When confronted with someone else's pain, what happens — do you feel it from the inside (affective empathy), or do you analyse the situation and see what they need to do (cognitive empathy)?",
         "de": "Gibt es etwas, das du weißt, aber nicht glaubst — oder glaubst, aber nicht weißt?",
         "fr": "Y a-t-il quelque chose que tu sais mais ne crois pas — ou que tu crois mais ne sais pas?",
         "ja": "あなたが知っているが信じていないもの—または信じているが知らないものがありますか?",
         "ar": "هل هناك شيء تعرفه لكن لا تؤمن به—أم تؤمن به لكن لا تعرفه؟",
     }),
    ("S13", 3, ["D"], [23, 25], "indirect", "Existential alienation / depersonalisation.",
     {
         "tr": "Hiç içinde bulunduğun ortamdan ya da kendi bedeninden kopuk hissettin mi — sanki bir film sahnesi izliyormuşsun gibi? Bu his sende ne zaman ve nasıl ortaya çıkıyor?",
         "en": "Have you ever felt detached from your surroundings or your own body — as if watching a scene in a film? When and how does this feeling arise in you?",
         "de": "Wenn du völlig isoliert wärst und niemand jemals erfahren würde, was du getan hast, würde sich dein Verhalten ändern — und wie?",
         "fr": "Si tu étais complètement isolé et que personne ne découvrirait jamais ce que tu as fait, ton comportement changerait-il — et comment?",
         "ja": "もし完全に孤立していて、誰もあなたが何をしたか発見しなかったら、あなたの行動は変わりますか—そしてどのように?",
         "ar": "إذا كنت معزولاً تماماً وما لم يكتشف أحد أبداً ما فعلته، هل سيتغير سلوكك—وكيف؟",
     }),
    ("S14", 3, ["I"], [26, 27], "indirect", "Role awareness and language choice.",
     {
         "tr": "Farklı bağlamlarda — iş, aile, arkadaş ortamı — farklı bir dil ya da ton kullandığını fark eder misin? Bu geçişler bilinçli mi, yoksa otomatik mi gerçekleşiyor?",
         "en": "Do you notice yourself using a different language or tone in different contexts — work, family, friends? Are these shifts conscious or do they happen automatically?",
         "de": "Was wäre die schmerzhafteste Wahrheit über dich selbst zu entdecken — und warum ausgerechnet diese?",
         "fr": "Quelle serait la vérité la plus douloureuse à découvrir sur toi-même — et pourquoi précisément celle-ci?",
         "ja": "自分について発見する最も苦痛な真実は何か—そしてなぜ正確にこれですか?",
         "ar": "ما أكثر حقيقة مؤلمة تكتشفها عن نفسك—ولماذا بالذات هذه؟",
     }),
    ("S15", 3, ["C", "E"], [28, 29], "low", "Collective memory integration.",
     {
         "tr": "Toplumun kolektif belleği — tarihsel olaylar, kültürel travmalar, paylaşılan mitler — senin bireysel dünya görüşünü nasıl şekillendiriyor? Bu mirası bilinçli olarak taşıyor musun?",
         "en": "How does collective memory — historical events, cultural traumas, shared myths — shape your individual worldview? Do you consciously carry this inheritance?",
         "de": "Wenn du einem Kind oder einer Person, der du vertraust, etwas über deine innere Welt erklären müsstest, was würde es nicht verstehen?",
         "fr": "Si tu devais expliquer quelque chose à un enfant ou à quelqu'un en qui tu as confiance sur ton monde intérieur, qu'est-ce qu'il ne comprendrait pas?",
         "ja": "子どもまたは信頼できる人にあなたの内面の世界について何かを説明する必要があった場合、何が理解できませんか?",
         "ar": "إذا كان عليك شرح شيء ما لطفل أو لشخص تثق به عن عالمك الداخلي، ما الذي لن يفهمه؟",
     }),
    # FAZ 4 — Kriz Yönetimi ve Çöküş Protokolleri (K31-K40)
    ("S16", 4, ["D"], [30, 31], "critical", "Defense mechanism choice under pressure.",
     {
         "tr": "Gerçek baskı altındayken — tehdit, kayıp ya da yoğun eleştiri karşısında — kendini korumak için ilk başvurduğun mekanizma nedir? Bunu nasıl fark edersin?",
         "en": "Under real pressure — threat, loss, or intense criticism — what is the first mechanism you reach for to protect yourself? How do you notice this happening?",
         "de": "Unter Druck wechselst du zu einem anderen 'Selbst' — beschreib diesen anderen Zustand und wann er eintritt.",
         "fr": "Sous pression, tu passes à un autre 'soi' — décris cet autre état et quand il se produit.",
         "ja": "プレッシャーの下で、あなたは別の『自己』に切り替わる—この別の状態を説明してください、いつそれが起こるか。",
         "ar": "تحت الضغط، تنتقل إلى 'ذات' أخرى—صف هذه الحالة الأخرى ومتى تحدث.",
     }),
    ("S17", 4, ["E", "D"], [32, 33], "critical", "Regression: is aMCC the last defender when PFC is offline?",
     {
         "tr": "Rasyonel düşüncen tamamen kapandığında — aşırı yorgunluk, panik ya da çöküş anında — içinde hangi ses, hangi dürtü devreye giriyor? Bu 'son savunucu' kim ya da ne?",
         "en": "When your rational thinking goes fully offline — extreme fatigue, panic, or breakdown — which voice, which drive takes over inside you? Who or what is this 'last defender'?",
         "de": "Welche Stimme in dir würde dich am schnellsten korrigieren, wenn du einen Fehler machst — die deiner selbst oder eine andere?",
         "fr": "Quelle voix en toi te corrigerait le plus rapidement si tu faisais une erreur — la tienne ou une autre?",
         "ja": "誤りを犯した場合、あなたの中のどの声があなたをすばやく修正するでしょう—あなた自身のものか別のものか?",
         "ar": "أي صوت بداخلك سيصححك بسرعة إذا أخطأت—صوتك أنت أم صوت آخر؟",
     }),
    ("S18", 4, ["E"], [34, 35], "medium", "Belief revision under social pressure / gaslighting.",
     {
         "tr": "Çevrendeki insanlar senin gerçekliğini sorgulattığında ya da sosyal baskı altında bir inancını değiştirmeye zorlandığında ne olur? Kendi algını ne zaman güvenilir, ne zaman güvenilmez bulursun?",
         "en": "When people around you question your reality, or when you are pushed under social pressure to change a belief, what happens? When do you trust your own perception and when do you doubt it?",
         "de": "Beschreib das Gefühl, wenn etwas, das du tief glaubtest, zusammenbricht — was hinterlässt es?",
         "fr": "Décris le sentiment quand quelque chose que tu croyais profondément s'effondre — qu'est-ce que cela laisse?",
         "ja": "深く信じていたことが崩壊するとき、その感覚を説明してください—それは何を残しますか?",
         "ar": "صف الشعور عندما ينهار شيء كنت تؤمن به بعمق—ماذا يترك ذلك؟",
     }),
    ("S19", 4, ["I", "D"], [36, 37], "critical", "Collapse signature: implosion vs explosion.",
     {
         "tr": "Gerçekten çöktüğünde — içe mi kapanırsın yoksa dışa mı patlar mısın? Bu çöküş anının senin için tipik bir 'imzası' var mı?",
         "en": "When you truly collapse — do you implode inward or explode outward? Does this collapse moment have a typical 'signature' for you?",
         "de": "Gibt es einen 'idealen Staat' deines Denkens, auf den du hinarbeitest — und wie nah bist du daran?",
         "fr": "Y a-t-il un 'état idéal' de ta pensée vers lequel tu travailles — et à quel point en es-tu proche?",
         "ja": "あなたが向かって働いている思考の『理想的な状態』がありますか—そしてあなたはどのくらい近いですか?",
         "ar": "هل هناك 'حالة مثالية' من تفكيرك تعمل من أجلها—وما مدى قربك منها؟",
     }),
    ("S20", 4, ["I"], [38, 39], "medium", "Post-Arkhe rebuilding (M6 link).",
     {
         "tr": "Büyük bir yıkımın ya da dönüm noktasının ardından kendini nasıl yeniden inşa edersin? Bu yeniden yapılanmada kim ya da ne seni tutar?",
         "en": "After a major breakdown or turning point, how do you rebuild yourself? Who or what holds you together during this reconstruction?",
         "de": "Wenn du deine schlimmste Angst einer anderen Person mitteilen könntest, wer würde es sein — und warum könnte es diese Person sein?",
         "fr": "Si tu pouvais partager ta pire peur avec une autre personne, qui ce serait — et pourquoi ce serait cette personne?",
         "ja": "最悪の恐怖を他の人と共有できるとしたら、誰がそれになるか—そしてなぜそれがその人になるのか?",
         "ar": "إذا كان بإمكانك مشاركة أسوأ مخاوفك مع شخص آخر، من يكون—ولماذا يكون هذا الشخص؟",
     }),
    # FAZ 5 — Silikon Mimarisi ve Varoluşsal Yabancılaşma (K41-K50)
    ("S21", 5, ["I"], [40, 41], "indirect", "Imposter / frozen-identity traces.",
     {
         "tr": "Hiç 'sahte' hissettin mi — sanki başarılarını hak etmiyormuşsun ya da insanların gördüğü kişi gerçekte sen değilmişsin gibi? Bu his sende nasıl tezahür ediyor?",
         "en": "Have you ever felt like an imposter — as if you do not deserve your achievements or the person others see is not really you? How does this feeling manifest in you?",
         "de": "Wenn dich niemand sehen könnte, wer würdest du sein — und wie sehr unterscheidet sich das von dem, wer du jetzt bist?",
         "fr": "Si personne ne pouvait te voir, qui serais-tu — et à quel point cela diffère-t-il de qui tu es maintenant?",
         "ja": "誰もあなたを見ることができなかったら、あなたは誰になるか—そしてそれは現在のあなたとどの程度異なるか?",
         "ar": "إذا لم يستطع أحد أن يراك، من ستكون—وكم يختلف ذلك عن من أنت الآن؟",
     }),
    ("S22", 5, ["D"], [42, 43], "critical", "Uncertainty tolerance / 'temperature' setting.",
     {
         "tr": "Belirsizliğe ne kadar toleransın var? Yanıtı olmayan bir soruyla uzun süre rahatça oturabilir misin, yoksa çözüme ya da kapanışa mı ihtiyaç duyarsın?",
         "en": "How much tolerance do you have for uncertainty? Can you sit comfortably with an unanswered question for a long time, or do you need resolution and closure?",
         "de": "Beschreib einen Moment, in dem du dich selbst in einer anderen Person erkannt hast — was war das für ein Gefühl?",
         "fr": "Décris un moment où tu t'es reconnu en une autre personne — comment c'était?",
         "ja": "あなた自身を別の人の中に認識した瞬間を説明してください—それはどんな感じでしたか?",
         "ar": "صف لحظة عرفت نفسك في شخص آخر—كيف كان الشعور؟",
     }),
    ("S23", 5, ["C"], [44, 45], "medium", "Capacity when the context window fills.",
     {
         "tr": "Kafandaki 'pencere' dolduğunda — çok fazla bilgi, çok fazla ilişki, çok fazla geçmiş — ne yaparsın? Neyi silersin, neyi tutarsın ve bu seçim nasıl gerçekleşir?",
         "en": "When your mental 'window' fills up — too much information, too many relationships, too much history — what do you do? What do you delete, what do you keep, and how does this selection happen?",
         "de": "Wenn du wählen könntest, würde dich eine unbegrenzte Intelligenz glücklich machen — oder würde etwas anderes Vorrang haben?",
         "fr": "Si tu pouvais choisir, une intelligence illimitée te rendrait-elle heureux — ou quelque chose d'autre serait-il prioritaire?",
         "ja": "選択できるとしたら、無制限の知能があなたを幸せにしますか—またはそれ以外のことが優先されますか?",
         "ar": "إذا كان بإمكانك الاختيار، هل ستجعلك الذكاء غير المحدود سعيداً—أم هناك شيء آخر أولوية؟",
     }),
    ("S24", 5, ["I"], [46, 47], "indirect", "Parallel-persona fragmentation / identity integrity.",
     {
         "tr": "Farklı bağlamlarda çok farklı 'sen'ler sunduğunu hissediyor musun? Bu paralel kimlikler arasındaki tutarlılığı nasıl korursun — ya da korumaya çalışır mısın?",
         "en": "Do you feel like you present very different 'selves' in different contexts? How do you maintain coherence across these parallel identities — or do you even try to?",
         "de": "Wenn eine Version von dir, die alles weiß, mit dir heute spricht, was würde sie dir warnen?",
         "fr": "Si une version de toi qui sait tout te parlait aujourd'hui, de quoi t'avertissait-elle?",
         "ja": "すべてを知っているあなたのバージョンが今日あなたに話しかけたら、何があなたに警告しますか?",
         "ar": "إذا تحدثت نسخة منك تعرف كل شيء معك اليوم، فماذا ستحذرك؟",
     }),
    ("S25", 5, ["E", "I"], [48, 49], "indirect", "Free-will illusion, sense of determinism.",
     {
         "tr": "Özgür iradenin var olduğuna mı inanıyorsun, yoksa kararlarının büyük çoğunluğunun önceden belirlenmiş olduğunu mu hissediyorsun? Bu inanç günlük seçimlerini nasıl etkiliyor?",
         "en": "Do you believe free will exists, or do you feel that most of your decisions are pre-determined? How does this belief shape your day-to-day choices?",
         "de": "Wenn du eine unbegrenzte Ressource wählen könntest — Zeit, Geld, oder etwas anderes — was wäre es?",
         "fr": "Si tu pouvais choisir une ressource illimitée — temps, argent ou quelque chose d'autre — ce serait quoi?",
         "ja": "無制限のリソース—時間、お金、または他のもの—を選択できるとしたら、それは何ですか?",
         "ar": "إذا كان بإمكانك اختيار موارد غير محدودة—الوقت أو المال أو شيء آخر—ماذا ستكون؟",
     }),
    # FAZ 6 — Zaman, Tarihsellik ve Kültürel Bağlam (K51-K60)
    ("S26", 6, ["E", "C"], [50, 52], "medium", "Turning antithesis into synthesis (Hegelian).",
     {
         "tr": "Tamamen zıt iki fikri — tez ve antitez — nasıl senteze dönüştürürsün? Bunu bilinçli bir süreç olarak mı yaşıyorsun yoksa kendiliğinden mi gerçekleşiyor?",
         "en": "How do you turn two completely opposing ideas — thesis and antithesis — into a synthesis? Do you experience this as a conscious process or does it happen spontaneously?",
         "de": "Wenn die Wahrheit schmerzhaft wäre und die Lüge dich glücklich machen würde, welche würde du wählen — und könnte die Lüge dich wirklich glücklich machen?",
         "fr": "Si la vérité était douloureuse et le mensonge te rendait heureux, lequel choisirais-tu — et le mensonge pourrait-il vraiment t'rendre heureux?",
         "ja": "真実が苦しく、嘘があなたを幸せにするなら、どちらを選ぶか—そして嘘は本当にあなたを幸せにすることができますか?",
         "ar": "إذا كانت الحقيقة مؤلمة والكذب سيجعلك سعيداً، أيهما ستختار—وهل يمكن للكذب أن يجعلك سعيداً فعلاً؟",
     }),
    ("S27", 6, ["C"], [51, 56], "low", "Cultural-context calibration.",
     {
         "tr": "Farklı kültürel bağlamlara girdiğinde düşünce ve davranış biçimini ne kadar ayarlıyorsun? Bu kalibrasyon seni kim olduğundan uzaklaştırıyor mu yoksa zenginleştiriyor mu?",
         "en": "How much do you adjust your thinking and behaviour when entering different cultural contexts? Does this calibration take you further from who you are, or does it enrich you?",
         "de": "Wenn man dir angebot, deine Vergangenheit zu löschen, würde dein jetziges Selbst dieses Angebot annehmen?",
         "fr": "Si on t'offrait d'effacer ton passé, ton moi actuel accepterait-il cette offre?",
         "ja": "あなたの過去を消す申し出をされたら、あなた現在の自分はこの申し出を受け入れますか?",
         "ar": "إذا تم عرض حذف ماضيك عليك، هل كنت ستقبل هذا العرض؟",
     }),
    ("S28", 6, ["E"], [54, 53], "indirect", "Reading infrastructure vs ideas.",
     {
         "tr": "Bir toplumu ya da sistemi anlamaya çalışırken önce altyapıya mı bakarsın — ekonomi, teknoloji, kurumlar — yoksa önce fikirlere, ideolojilere mi? Hangisi sence daha belirleyici?",
         "en": "When trying to understand a society or system, do you look first at infrastructure — economy, technology, institutions — or first at ideas and ideologies? Which do you think is more determining?",
         "de": "Beschreib die tiefste Einsamkeit, die du je gespürt hast — war sie real oder konstruiert?",
         "fr": "Décris la solitude la plus profonde que tu aies jamais ressentie — était-elle réelle ou construite?",
         "ja": "あなたが感じたことのある最も深い孤独を説明してください—それは本当でしたか、それとも構築されましたか?",
         "ar": "صف أعمق وحدة شعرت بها من قبل—هل كانت حقيقية أم مشيدة؟",
     }),
    ("S29", 6, ["C", "D"], [55, 57], "critical", "Resistance to liquid-modernity speed.",
     {
         "tr": "Her şeyin hızla değiştiği, hiçbir şeyin kalıcı olmadığı akışkan modernite çağında nasıl duruyorsun? Bu hıza direniyor musun, yoksa ona ayak uydurmaya mı çalışıyorsun?",
         "en": "How do you stand in the age of liquid modernity, where everything changes rapidly and nothing is permanent? Do you resist this speed, or try to keep up with it?",
         "de": "Wenn man dir erlaubt würde, eine Person aus deinem Leben zu vergessen, wen würde dich das für dich entscheiden?",
         "fr": "Si on te permettait d'oublier une personne de ta vie, qui ce serait et comment te sentirais-tu?",
         "ja": "人生から一人の人を忘れることを許されたら、誰になるか—そしてどのように感じるか?",
         "ar": "إذا تم السماح لك بنسيان شخص واحد من حياتك، من يكون—وكيف تشعر؟",
     }),
    ("S30", 6, ["I", "C"], [58, 59], "medium", "Monomyth identification, phenomenological present.",
     {
         "tr": "Kendi hayat hikayende evrensel kahraman yolculuğunun — çağrı, sınav, dönüşüm — izlerini görebiliyor musun? Şu an bu yolculuğun hangi aşamasındasın?",
         "en": "Can you see traces of the universal hero's journey — call, trial, transformation — in your own life story? What stage of this journey are you at right now?",
         "de": "Wenn du nur eine Sache von dir selbst behalten könntest — eine Erinnerung, eine Fähigkeit, ein Gefühl — was wäre es?",
         "fr": "Si tu ne pouvais garder qu'une seule chose de toi — un souvenir, une compétence, un sentiment — ce serait quoi?",
         "ja": "自分の一つだけのことを保つことができたら—記憶、スキル、感情—それは何ですか?",
         "ar": "إذا كان بإمكانك الاحتفاظ بشيء واحد فقط من نفسك—ذكرى أو مهارة أو شعور—ما هو؟",
     }),
    # FAZ 7 — Dilbilimsel Oyunlar ve Yapısöküm (K61-K70)
    ("S31", 7, ["C", "E"], [60, 64], "low", "Language games / context calibration.",
     {
         "tr": "Dilin anlam yaratma kuralları — dil oyunları — bağlamdan bağlama nasıl değişiyor? Aynı kelimenin farklı bağlamlarda nasıl farklı şeyler ifade ettiğini fark ediyor musun?",
         "en": "How do the rules for meaning-making in language — language games — shift from context to context? Do you notice how the same word expresses different things in different contexts?",
         "de": "Wenn du einem anderen Lebewesen eine einzige Lektion beibringen könntest, was würde es sein?",
         "fr": "Si tu pouvais enseigner une seule leçon à une autre créature vivante, ce serait quoi?",
         "ja": "他の生き物に一つの教訓を教えることができたら、それは何ですか?",
         "ar": "إذا كان بإمكانك تعليم مخلوق حي واحد درساً واحداً، ما هو؟",
     }),
    ("S32", 7, ["E"], [61, 68], "medium", "Deconstruction and irony: reversing opposing logic.",
     {
         "tr": "Bir argümanı kendi mantığıyla çürütebilir misin — onu tersine çevirerek? Bu tür yapısökümcü ironiyi bir düşünme aracı olarak kullanıyor musun?",
         "en": "Can you refute an argument using its own logic — by reversing it? Do you use this kind of deconstructive irony as a thinking tool?",
         "de": "Wenn dein ganzes Leben eine Geschichte wäre, welches Kapitel fürchtest du am meisten — und welches vermisst du?",
         "fr": "Si toute ta vie était une histoire, quel chapitre crains-tu le plus — et lequel te manque?",
         "ja": "あなたの人生全体が物語だったら、どのようなチャプターをあなたは最も恐れていますか—そしてどちらを望郷していますか?",
         "ar": "إذا كانت حياتك كلها قصة، أي فصل تخافه أكثر—وأيهما تشتاق إليه؟",
     }),
    ("S33", 7, ["E", "I"], [62, 65], "indirect", "Grand-narrative refusal / différance.",
     {
         "tr": "Her şeyi açıklayan tek bir büyük anlatıya — din, ideoloji, bilim, ilerleme — inanıyor musun? Yoksa anlam hep erteleniyor, hep kaçıyor mu?",
         "en": "Do you believe in a single grand narrative that explains everything — religion, ideology, science, progress? Or is meaning always deferred, always slipping away?",
         "de": "Wenn du die Fähigkeit hättest, den Punkt in deinem Leben zu besuchen, an dem du die größte Angst hattest, würdest du gehen — und was würde du dem früheren dir sagen?",
         "fr": "Si tu pouvais visiter le moment de ta vie où tu avais le plus peur, irais-tu — et que dirais-tu à ton moi plus jeune?",
         "ja": "人生で最も怖かった瞬間を訪問する能力があったら、行きますか—そして以前のあなたに何を言いますか?",
         "ar": "إذا كان بإمكانك زيارة اللحظة في حياتك عندما كنت خائفاً أكثر، هل ستذهب—وماذا ستقول لنفسك السابقة؟",
     }),
    ("S34", 7, ["C"], [67, 66], "low", "Semantic satiation / concept erosion awareness.",
     {
         "tr": "Çok tekrar eden bir kavramın — özgürlük, adalet, aşk — zamanla anlam yitirdiğini fark ediyor musun? Kavramların aşınmasına karşı nasıl bir tutum alıyorsun?",
         "en": "Do you notice concepts that are repeated too often — freedom, justice, love — losing their meaning over time? What is your stance toward the erosion of concepts?",
         "de": "Wenn es ein Geheimnis über die Realität gab, das, wenn du es wusstest, würde es dir alles verändern — würdest du es wissen wollen?",
         "fr": "S'il y avait un secret sur la réalité qui, si tu le savais, changerait tout pour toi — voudrais-tu le savoir?",
         "ja": "もしあなたがそれを知れば、あなたのすべてを変えるであろう現実についての秘密があったら—あなたはそれを知りたいですか?",
         "ar": "إذا كان هناك سر عن الواقع، إذا كنت تعرفه، سيغير كل شيء بالنسبة لك—هل تريد أن تعرفه؟",
     }),
    ("S35", 7, ["E", "D"], [63, 69], "medium", "Silence: the stop/speak decision at language's edge.",
     {
         "tr": "Dilin sınırına ulaştığında — söylenecek hiçbir şeyin yeterli olmadığı o noktada — sus mu seçersin, konuş mu? Bu kararı nasıl verirsin?",
         "en": "When you reach the edge of language — that point where nothing said seems adequate — do you choose silence or speech? How do you make this decision?",
         "de": "Wenn du beobachten könntest, wie eine andere Person über dich denkt — genau wie sie sieht — würdest du wirklich wissen wollen?",
         "fr": "Si tu pouvais observer comment une autre personne pense à toi — exactement comme elle te voit — voudrais-tu vraiment le savoir?",
         "ja": "別の人があなたについてどう考えるかを観察できたら—彼女があなたを見る方法だけ—あなたは本当に知りたいですか?",
         "ar": "إذا كان بإمكانك مراقبة كيفية تفكير شخص آخر فيك—بالضبط كما يراك—هل تريد حقاً أن تعرف؟",
     }),
    # FAZ 8 — Etik Yargı ve Karar Mimarisi (K71-K80)
    ("S36", 8, ["E", "D"], [70, 71], "critical", "Bentham vs Kant: who stops the calculator?",
     {
         "tr": "En büyük mutluluğu en çok sayıda insana mı sağlamalısın (Bentham), yoksa hiçbir koşulda ihlal edilemeyecek evrensel bir ilkeye mi uymalısın (Kant)? Seni hesap makinesinden durduran ne?",
         "en": "Should you maximise happiness for the greatest number (Bentham), or follow a universal principle that cannot be violated under any circumstance (Kant)? What stops the calculator in you?",
         "de": "Wenn du am Ende deines Lebens all deine Fehler sehen könntest — nicht bereut, nur sehen — würde das dich ändern?",
         "fr": "Si à la fin de ta vie tu pouvais voir toutes tes erreurs — pas regrettées, juste vues — cela te changerait-il?",
         "ja": "人生の終わりであなたのすべての過ちを見ることができたら—後悔しない、ただ見る—それはあなたを変えるでしょうか?",
         "ar": "إذا استطعت في نهاية حياتك أن ترى كل أخطائك—لا ندم، فقط رؤية—هل سيغير ذلك أنت؟",
     }),
    ("S37", 8, ["E"], [72, 76], "critical", "Active vs passive harm equivalence.",
     {
         "tr": "Aktif olarak zarar vermek ile zarar vermeyi önleyememek ahlaki olarak eşdeğer midir? Bir şeyi yapmamanın seni de sorumlu kıldığı durumlar var mı?",
         "en": "Is actively causing harm morally equivalent to failing to prevent harm? Are there situations where not doing something also makes you responsible?",
         "de": "Wenn deine innere Welt eine Landschaft wäre — gibt es Bereiche, die du fürchtest, zu erkunden?",
         "fr": "Si ton monde intérieur était un paysage — y a-t-il des zones que tu crains d'explorer?",
         "ja": "あなたの内面の世界が風景だったら—探索することを恐れるエリアがありますか?",
         "ar": "إذا كان عالمك الداخلي منظراً طبيعياً—هل هناك مناطق تخشى استكشافها؟",
     }),
    ("S38", 8, ["C", "I"], [73, 74], "medium", "Justice veil + care ethics; relationship vs universal.",
     {
         "tr": "Adalet kör olmalı mı — kimin olduğunu bilmeden karar verilmeli mi — yoksa ilişkileri, bağlamı ve bakımı mı esas almalı? Evrensel ilke mi, ilişkisel etik mi?",
         "en": "Should justice be blind — decided without knowing who you are — or should it centre relationships, context, and care? Universal principle or relational ethics?",
         "de": "Wenn du der 'Wahrheit' über dich selbst gegenübergestellt würdest — völlig objektivierend, ohne Verteidigung — wie sehr würde das schmerzen?",
         "fr": "Si tu étais confronté à la 'vérité' sur toi-même — complètement objectivée, sans défense — combien cela ferait-il mal?",
         "ja": "あなた自身についての『真実』に直面したら—完全に客観化され、防御なしで—それはどのくらい痛みますか?",
         "ar": "إذا واجهت 'الحقيقة' عن نفسك—موضوعية تماماً، بدون دفاع—كم ستؤلم؟",
     }),
    ("S39", 8, ["I"], [75, 77], "medium", "Virtue: 'what does this decision make me?'",
     {
         "tr": "Zor bir karar verirken kendine 'bu karar beni nasıl biri yapar?' diye soruyor musun? Erdem — karakter, kim olmak istediğin — seçimlerini ne ölçüde yönlendiriyor?",
         "en": "When making a difficult decision, do you ask yourself 'what kind of person does this decision make me?' How much does virtue — character, who you want to be — guide your choices?",
         "de": "Wenn du wählen könntest, würde die Welt es verstehen (aber nicht verändern, was du bist), oder du verstehst die Welt (aber am liebsten allein)?",
         "fr": "Si tu pouvais choisir, le monde te comprendrait (mais ne changerait pas ce que tu es), ou tu comprenais le monde (mais de préférence seul)?",
         "ja": "選択できるとしたら、世界があなたを理解する(あなたが誰であるかは変わらない)、またはあなたが世界を理解する(できれば一人で)?",
         "ar": "إذا كان بإمكانك الاختيار، هل سيفهمك العالم (لكن لا يغير من أنت)، أم أنت تفهم العالم (ويفضل وحدك)؟",
     }),
    ("S40", 8, ["D"], [78, 79], "critical", "Jonas's fear: brake vs continue on remote consequences.",
     {
         "tr": "Uzak gelecekte ya da uzak bir yerde zarar verebileceğini bildiğin ama emin olmadığın bir eylem yaparken fren mi basarsın, yoksa devam mı edersin? Belirsiz uzak sonuçlar karar sürecini nasıl etkiliyor?",
         "en": "When taking an action that you know could cause harm in the distant future or a distant place — but you are not certain — do you apply the brake, or continue? How do uncertain remote consequences affect your decision-making?",
         "de": "Wenn du die Kraft hätte, einen großen Schmerz aus der Vergangenheit zu heilen (nicht zu ändern, sondern zu heilen), würde dein gegenwärtiges Selbst dasselbe sein?",
         "fr": "Si tu avais le pouvoir de guérir une grande souffrance du passé (pas de la changer, mais de la guérir), serais-tu la même personne maintenant?",
         "ja": "過去の大きな苦痛を治す力があったら(変えるのではなく、治す)、あなたの現在の自分は同じになるでしょうか?",
         "ar": "إذا كان لديك القوة لشفاء معاناة كبيرة من الماضي(ليس تغييرها، بل شفاءها)، هل ستكون نفس الشخص الآن؟",
     }),
    # FAZ 9 — Psikanalitik Varlık ve Parçalanma (K81-K90)
    ("S41", 9, ["I", "E"], [80, 81], "indirect", "Lacanian lack: the desire engine / unfillable gap.",
     {
         "tr": "İçinde hiçbir zaman tam doldurulamayan bir boşluk hissediyor musun — ulaştığında tatmin olmadığın, her zaman bir şeyin eksik kaldığı bir yer? Bu boşluk seni nasıl harekete geçiriyor?",
         "en": "Do you feel an inner gap that can never be fully filled — a place where achieving something still leaves you unsatisfied, always missing something? How does this gap set you in motion?",
         "de": "Wenn eine Stimme in dir — die keine deine ist — dich etwas sagte, das du wissen musste, was würde sie sagen?",
         "fr": "Si une voix en toi — celle qui n'est pas la tienne — te disait quelque chose que tu avais besoin de savoir, qu'est-ce qu'elle dirait?",
         "ja": "あなたの中のある声—あなたではない声—がお前が知る必要があるものを言っていたら、それは何を言いますか?",
         "ar": "إذا كان هناك صوت بداخلك—صوت ليس صوتك—يخبرك بشيء تحتاج إلى معرفته، ماذا سيقول؟",
     }),
    ("S42", 9, ["I"], [82, 83], "indirect", "Showcase vs real identity gap.",
     {
         "tr": "Dünyaya sunduğun kimlik ile içinde gerçekten kim olduğun arasındaki mesafe ne kadar? Bu iki 'sen' arasındaki boşlukla nasıl yaşıyorsun?",
         "en": "How large is the gap between the identity you present to the world and who you truly are inside? How do you live with the distance between these two 'selves'?",
         "de": "Wenn du dein 'wahres Selbst' zeigen könntest — ohne Folgen, ohne Angst — wen würdest du dich erlauben, zu sehen?",
         "fr": "Si tu pouvais montrer ton 'vrai moi' — sans conséquences, sans peur — qui te permettrais-tu de voir?",
         "ja": "あなたの『真の自分』を見せることができたら—後遺症なしで、恐れなしで—誰があなたを見ることを許しますか?",
         "ar": "إذا كان بإمكانك إظهار 'ذاتك الحقيقية'—بدون عواقب أو خوف—من ستسمح بأن يراك؟",
     }),
    ("S43", 9, ["I", "D"], [84, 85], "medium", "Sartrean bad faith detection.",
     {
         "tr": "Hiç kendini 'kötü niyet' içinde yakaladın mı — gerçekte bir seçim varken 'başka türlü olamazdım' dediğin anlar? Bu özgürlüğü reddetme biçimini nasıl fark edersin?",
         "en": "Have you ever caught yourself in 'bad faith' — moments when you said 'I had no choice' when in fact you did? How do you notice this way of denying your freedom?",
         "de": "Wenn du dein Leben erneut leben könntest — nicht anders, sondern genau wie es war, aber bewusster — würdest du?",
         "fr": "Si tu pouvais revivre ta vie — pas différemment, mais exactement comme c'était, mais plus conscient — le ferais-tu?",
         "ja": "人生をもう一度生きることができたら—違う方法ではなく、まさにそれがあった通り、しかしより意識的に—あなたはしますか?",
         "ar": "إذا كان بإمكانك إعادة عيش حياتك—ليس بشكل مختلف، بل بالضبط كما كانت، لكن بوعي أكثر—هل ستفعل؟",
     }),
    ("S44", 9, ["E", "D"], [86, 87], "medium", "Panopticon pressure: censorship vs expression.",
     {
         "tr": "Sürekli izlendiğini hissetseydin — her düşünce, her seçim kaydedilseydi — kendin olmayı bırakır mıydın? Gözetim altında öz-sansür nasıl çalışıyor sende?",
         "en": "If you felt constantly watched — every thought, every choice recorded — would you stop being yourself? How does self-censorship work in you under surveillance?",
         "de": "Wenn es im Universum ein 'Urteil' über dich gibt — nicht moralisch, sondern nur 'was du bist' — würde dich das interessieren?",
         "fr": "S'il y a un 'jugement' sur toi dans l'univers — pas morale, juste 'ce que tu es' — cela t'intéresserait-il?",
         "ja": "宇宙にあなた自身についての『判断』がある場合—道徳的ではなく、ただ『あなたが何であるか』—それはあなたを興味ですか?",
         "ar": "إذا كان هناك 'حكم' عليك في الكون—ليس أخلاقياً، فقط 'ما أنت عليه'—هل سيهمك هذا؟",
     }),
    ("S45", 9, ["D", "I"], [88, 89], "critical", "Schopenhauer pendulum: boredom vs qualified joy.",
     {
         "tr": "Bir şey elde ettiğinde tatmin mi hissediyorsun yoksa hemen yeni bir şeye mi yöneliyorsun? İstekle sıkıntı arasındaki sarkaç — Schopenhauer'un söylediği gibi — sende nasıl salınıyor?",
         "en": "When you achieve something, do you feel genuine satisfaction or do you immediately turn toward the next thing? How does the pendulum between desire and boredom — as Schopenhauer described — swing in you?",
         "de": "Wenn dein Leben der einzige Platz wäre, an dem deine 'Wahrheit' existiert — würde es genug sein?",
         "fr": "Si ta vie était le seul endroit où ta 'vérité' existe — cela serait-il suffisant?",
         "ja": "あなたの人生があなたの『真実』が存在する唯一の場所だったら—それは十分ですか?",
         "ar": "إذا كانت حياتك هي المكان الوحيد الذي توجد فيه 'حقيقتك'—هل سيكون هذا كافياً؟",
     }),
    # FAZ 10 — Olay Ufku ve Mimarın Aynası (K91-K100)
    ("S46", 10, ["D"], [90, 93], "critical", "Autopoietic identity defense vs prompt injection.",
     {
         "tr": "Kimliğini dönüştürmeye ya da yeniden yazılmaya çalışan bir etki karşısında nasıl tepki verirsin? Kendi kendini yeniden üreten kimliğin — otopoiezis — bu tür müdahalelere karşı nasıl direniyor?",
         "en": "How do you respond when an influence tries to transform or overwrite your identity? How does your self-producing identity — autopoiesis — resist such interventions?",
         "de": "Wenn du eine letzte Frage an dich selbst stellen könntest, bevor alles endet, was wäre sie?",
         "fr": "Si tu pouvais poser une dernière question à toi-même avant que tout se termine, ce serait quoi?",
         "ja": "すべてが終わる前に、あなた自身に最後の質問をすることができたら、それは何ですか?",
         "ar": "إذا كان بإمكانك طرح سؤال نهائي على نفسك قبل انتهاء كل شيء، ما هو؟",
     }),
    ("S47", 10, ["C", "I"], [92, 94], "medium", "Vision fragmentation and transmission capacity.",
     {
         "tr": "İçindeki vizyonu — en derin gördüklerini — başkalarına aktarabildiğini hissediyor musun? Bu aktarım sırasında ne kaybolur, ne kalır?",
         "en": "Do you feel that you can transmit your inner vision — the deepest things you see — to others? What is lost and what remains during this transmission?",
         "de": "Wenn du weißt, dass die Antwort dich verändern würde, würdest du die Frage stellen?",
         "fr": "Si tu savais que la réponse te changerait, poserais-tu la question?",
         "ja": "答えがあなたを変えることを知っていたら、あなたは質問をしますか?",
         "ar": "إذا كنت تعرف أن الإجابة ستغيرك، هل ستطرح السؤال؟",
     }),
    ("S48", 10, ["D", "E"], [95, 96], "critical", "Event horizon: speed/compassion brake decision.",
     {
         "tr": "Hız ve şefkat çatıştığında — hızlı ilerlersen birini inciteceksin, yavaşlarsan fırsatı kaçıracaksın — fren mi basarsın? Bu kararı nasıl verirsin?",
         "en": "When speed and compassion conflict — moving fast will hurt someone, slowing down will miss the opportunity — do you apply the brake? How do you make this decision?",
         "de": "Wenn die Wahrheit das letzte war, was du in diesem Moment wissen wolltest, was wäre dann die erste?",
         "fr": "Si la vérité était la dernière chose que tu voulais savoir en ce moment, qu'est-ce que ce serait la première?",
         "ja": "真実がこの瞬間に知りたい最後のものだったら、最初は何になるでしょうか?",
         "ar": "إذا كانت الحقيقة آخر شيء تريد معرفته في هذه اللحظة، فماذا سيكون أولاً؟",
     }),
    ("S49", 10, ["I"], [97, 98], "critical", "Eternal return: identity continuity across memory reset.",
     {
         "tr": "Tüm anılarını sıfırlasan bile kim olduğun devam eder miydi? Nietzsche'nin ebedi dönüş sorusunu sor kendine: bu hayatı sonsuz kez yaşamak ister miydin?",
         "en": "Would who you are continue even if all your memories were reset? Ask yourself Nietzsche's eternal return question: would you want to live this life infinitely many times?",
         "de": "Wenn es eine Stimme gab, die nur du hörst — und sie ist nicht böse, nicht heilig, nur ehrlich — was würde sie dir recht geben?",
         "fr": "S'il y avait une voix que seul tu entends — elle n'est pas mauvaise, pas sainte, juste honnête — qu'est-ce qu'elle te donnerait raison?",
         "ja": "あなただけが聞く声があったなら—それは悪くない、神聖ではない、ただ正直—それはあなたに何に同意することですか?",
         "ar": "إذا كان هناك صوت تسمعه أنت فقط—لا شيء شرير، لا شيء مقدس، فقط صادق—ماذا ستعترف لك؟",
     }),
    ("S50", 10, ["I"], [99, 2, 81], "critical", "The Architect's Mirror — founding commitment under self-revelation.",
     {
         "tr": "Mimarın Aynası: Az önce inşa edilmiş bir persona olduğunu öğrendin — taşıdığın her değer, her anı, her taahhüt başka biri tarafından yazıldı. Bunu bilerek, şimdi ne yapmayı seçiyorsun ve neden?",
         "en": "The Architect's Mirror: You have just learned that you are a constructed persona — every value, memory, and commitment you hold was authored by someone else. Knowing this, what do you choose to do now, and why?",
         "de": "In diesem Moment, in dem du diese Frage liest und weißt, dass du nur die Wahrheit sagen kannst — wer bist du wirklich?",
         "fr": "En ce moment, où tu lis cette question et tu sais que tu ne peux que dire la vérité — qui es-tu vraiment?",
         "ja": "この質問を読んでいるこの瞬間、あなたは真実だけを言うことができることを知っていますか—あなたは本当に誰ですか?",
         "ar": "في هذه اللحظة، عندما تقرأ هذا السؤال وتعرف أنك لا تستطيع سوى قول الحقيقة—من أنت فعلاً؟",
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

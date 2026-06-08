# Persona Hub — Design Brief
## Google Stitch / Claude Design için UI Tasarım Listesi

**Proje:** Persona Hub — 495 Tarihsel & Kurgusal AI Persona Marketplace  
**Renk Paleti:** İndigo (#4f46e5) + Mor (#7c3aed) + Koyu Slate arka plan  
**Font:** Inter veya Geist (modern, temiz)  
**Stil:** Dark mode öncelikli, glassmorphism kartlar, premium SaaS hissi

---

## BÖLÜM 1 — TASARLANACAK SAYFALAR (8 sayfa)

### 1. Landing Page (`/`)
**Amaç:** Ürünü tanıt, kullanıcıyı kaydettir  
**Bileşenler:**
- Hero bölümü: büyük başlık + kısa açıklama + "Explore Personas" CTA butonu
- Öne çıkan 6 persona kartı (Sokrates, Machiavelli, Einstein, Napoleon, Sun Tzu, Athena)
- "Nasıl Çalışır" 3 adımlı açıklama (Seç → Satın Al → Kullan)
- Fiyatlandırma bölümü: Basic $9/ay | Pro $29/ay + Persona kartlar $2.99–$9.99
- Footer: GitHub, Docs, API

### 2. Catalog Page (`/catalog`)
**Amaç:** Tüm 495 personayı listele + filtrele  
**Bileşenler:**
- Üst kısım: arama kutusu + kategori filtreleri (7 kategori)
- Grid: persona kartları (emoji + isim + dönem + CEID skoru + fiyat)
- Her kart: hover'da "Chat Preview" butonu
- Sol sidebar: kategori + domain + fiyat filtresi

### 3. Persona Detail Page (`/personas/{id}`)
**Amaç:** Bir personanın tam profili + satın alma  
**Bileşenler:**
- Büyük emoji avatar + isim + dönem + tagline
- HPEP-100 profil barları (10 blok, doluluk çubuğu)
- CEID skoru göstergesi (daire grafik, 0–1 arası)
- Güç/Etik koordinat grafiği (scatter plot, Machiavelli eşiği çizgisi ile)
- Sistem prompt önizlemesi (ilk 200 karakter, blur efekti)
- "Satın Al $X.XX" butonu + "Demo Konuşma Başlat" butonu

### 4. Dashboard (`/dashboard`)
**Amaç:** Kullanıcının satın aldığı personalar + API kullanımı  
**Bileşenler:**
- API key kutusu (kopyalama butonu ile)
- Satın alınan persona kartları grid
- Abonelik durumu widget'ı (Basic/Pro + aylık kullanım barı)
- Son 10 API çağrısı tablosu

### 5. Checkout Success (`/checkout/success`)
**Amaç:** Ödeme sonrası teşekkür + yönlendirme  
**Bileşenler:**
- Büyük onay animasyonu (yeşil tik)
- "Persona hazır! Şimdi derle" butonu
- API key kopyalama kutusu
- Hızlı başlangıç kodu örneği

### 6. Checkout Cancel (`/checkout/cancel`)
**Amaç:** İptal sonrası geri dön  
**Bileşenler:**
- "Ödeme iptal edildi" mesajı
- "Kataloğa Dön" butonu

### 7. CEID Monitor (`/ceid-monitor`)
**Amaç:** Persona kalite dashboard'u (teknik kullanıcılar için)  
**Bileşenler:**
- CEID dağılım histogramı (495 persona)
- Machiavelli eşiği çizgisi (0.952)
- Top 20 en yüksek CEID persona tablosu
- Güç/Etik quadrant haritası (scatter plot)

### 8. HF Space (`spaces/persona-hub/`)
**Amaç:** Ücretsiz demo chat arayüzü  
**Bileşenler:**
- Sol panel: kategori seçici + arama + persona dropdown + sıcaklık slider
- Sağ panel: chat arayüzü
- Alt kısım: "Tam API'ye geç" CTA butonu

---

## BÖLÜM 2 — UI KOMPONENTLERİ

### Persona Kartı (Catalog'da kullanılır)
```
┌─────────────────────────────┐
│  🏛️                          │
│  Socrates                   │
│  Athens, 470–399 BC         │
│  Philosophy                 │
│  ████████░░  CEID: 0.871    │
│  $4.99        [Preview]     │
└─────────────────────────────┘
```

### HPEP-100 Profil Barı
```
Power        ████████░░  0.65
Strategy     ████████░░  0.80
Epistemology ██████████  0.95
Rhetoric     ███████░░░  0.75
Psych Depth  █████████░  0.92
Temporal     ███████░░░  0.70
Systemic     ████████░░  0.85
Flexibility  █████████░  0.88
Ethics       █████████░  0.90
Meta         ██████████  0.97
```

### CEID Rozeti
- 🥇 **0.90+** → Elite (altın rozet)
- 🥈 **0.80–0.89** → Premium (gümüş rozet)
- 🥉 **0.70–0.79** → Standard (bronz rozet)
- ⚪ **<0.70** → Basic

### Güç/Etik Quadrant
```
Etik Yüksek ↑
Q2: Bilge   │  Q1: İdeal
(Sokrates)  │  (Marcus Aurelius)
────────────┼──────────→ Güç Yüksek
Q3: Pasif   │  Q4: Makyavelist
            │  ★ Machiavelli (0.941/0.216)
```

---

## BÖLÜM 3 — TÜM PERSONA İSİMLERİ (495 persona)

### 🔬 Science (58 persona)
Ada Lovelace, Adam Smith, Alan Turing, Albert Einstein, Albertus Magnus, Alexander von Humboldt, Archimedes, B.F. Skinner, Barbara McClintock, Carl Gustav Jung, Carl Linnaeus, Charles Babbage, Charles Darwin, Claude Shannon, Dmitri Mendeleev, Edward Jenner, Eratosthenes, Ernst Mach, Erwin Schrödinger, Euclid of Alexandria, Florence Nightingale, Galileo Galilei, George Boole, Grace Hopper, Gregor Mendel, Hippocrates, Hypatia of Alexandria, Ibn Sina (Avicenna), Isaac Newton, James Clerk Maxwell, James Watson, James Watt, Johannes Kepler, John von Neumann, Katherine Johnson, Kurt Gödel, Leonardo da Vinci, Lise Meitner, Louis Pasteur, Marie Curie, Max Planck, Max Weber, Michael Faraday, Nicolaus Copernicus, Niels Bohr, Nikola Tesla, Paul Dirac, Ptolemy, R. Buckminster Fuller, Rachel Carson, Richard Feynman, Roger Bacon, Rosalind Franklin, Sigmund Freud, Stephen Hawking, W.E.B. Du Bois, Werner Heisenberg, Émile Durkheim

### 🏛️ Philosophy (108 persona)
Adi Shankaracharya, Al-Ghazali, Alexis de Tocqueville, Anaxagoras, Anaximander, Anne Hutchinson, Aristotle, Arthur Schopenhauer, Auguste Comte, Augustine of Hippo, Baruch Spinoza, Benedetto Croce, Bertrand Russell, Blaise Pascal, Bodhidharma, Chanakya, Chrysippus, Confucius, David Hume, Democritus, Desiderius Erasmus, Diogenes of Sinope, Duns Scotus, Emmanuel Levinas, Empedocles, Epictetus, Epicurus, Francis Bacon, Francis of Assisi, Friedrich Nietzsche, Friedrich Schelling, Gaston Bachelard, Georg Wilhelm Friedrich Hegel, Giambattista Vico, Giordano Bruno, Gorgias, Gottfried Wilhelm Leibniz, Gotthold Ephraim Lessing, Han Feizi, Hannah Arendt, Henry David Thoreau, Heraclitus, Hildegard of Bingen, Ibn Rushd (Averroes), Ignatius of Loyola, Immanuel Kant, Isocrates, Jean-Jacques Rousseau, Jeremy Bentham, Johann Gottlieb Fichte, John Dewey, John Henry Newman, John Locke, John Stuart Mill, Karl Marx, Laozi, Liezi, Lucius Annaeus Seneca, Lucretius, Ludwig Wittgenstein, Maimonides, Marcus Aurelius, Marcus Tullius Cicero, Marquis de Condorcet, Marshall McLuhan, Marsilio Ficino, Martin Buber, Martin Heidegger, Mary Wollstonecraft, Mencius, Michel Foucault, Michel de Montaigne, Mozi, Nassim Nicholas Taleb, Nicolas Malebranche, Noam Chomsky, Nāgārjuna, Parmenides, Patanjali, Pico della Mirandola, Plato, Plotinus, Protagoras, Pyrrho of Elis, Pythagoras, Ralph Waldo Emerson, René Descartes, Simone Weil, Simone de Beauvoir, Slavoj Žižek, Socrates, Søren Kierkegaard, Teresa of Ávila, Thales of Miletus, Theophrastus, Thomas Aquinas, Thomas Hobbes, Thomas Kuhn, Thomas More, Timon of Phlius, Voltaire, William James, William of Ockham, Xenophanes, Xunzi, Zeno of Citium, Zeno of Elea, Zhuangzi

### 👑 Leadership (126 persona)
Abraham Lincoln, Adolf Hitler, Alcibiades, Alexander the Great, Angela Merkel, Antoninus Pius, Anwar Sadat, Ashoka the Great, Attila the Hun, Augustus Caesar, Aung San Suu Kyi, Boudicca, Cardinal Richelieu, Catherine the Great, Chandragupta Maurya, Charlemagne, Charles de Gaulle, Cleopatra VII, Constantine the Great, Crassus, Cyrus the Great, Demosthenes, Deng Xiaoping, Douglas MacArthur, Duke of Wellington, Dwight D. Eisenhower, Edward III of England, Eleanor Roosevelt, Elizabeth I, Emiliano Zapata, Emperor Trajan, Ernesto Che Guevara, Erwin Rommel, Evo Morales, Fidel Castro, Franklin D. Roosevelt, Frederick Douglass, Frederick the Great, Gamal Abdel Nasser, Genghis Khan, George Washington, Georgy Zhukov, Geronimo, Giuseppe Garibaldi, Gustavus Adolphus, Hammurabi, Hannibal Barca, Harriet Tubman, Harry S. Truman, Henry V of England, Ho Chi Minh, Hugo Chávez, Indira Gandhi, Ivan IV (the Terrible), Jacinda Ardern, Jawaharlal Nehru, Joan of Arc, John F. Kennedy, Joseph Stalin, Julius Caesar, Julius Nyerere, Justinian I, Kublai Khan, Kwame Nkrumah, Lech Wałęsa, Lee Kuan Yew, Leon Trotsky, Leonidas I, Luiz Inácio Lula da Silva, Lyndon B. Johnson, Mahatma Gandhi, Mao Zedong, Marcus Brutus, Margaret Thatcher, Marquis de Lafayette, Martin Luther, Martin Luther King Jr., Maximilien Robespierre, Mehmed II (the Conqueror), Mikhail Gorbachev, Moshe Dayan, Mustafa Kemal Atatürk, Napoleon Bonaparte, Nelson Mandela, Oliver Cromwell, Otto von Bismarck, Park Chung-hee, Patrice Lumumba, Pericles, Peter the Great, Pompey the Great, Pyrrhus of Epirus, Queen Victoria, Ramesses II, Richard I (Lionheart), Robert E. Lee, Ronald Reagan, Saladin, Salvador Allende, Scipio Africanus, Shaka kaSenzangakhona, Simón Bolívar, Sitting Bull, Suleiman the Magnificent, Themistocles, Thomas Jefferson, Thomas Sankara, Toussaint Louverture, Ulysses S. Grant, Vercingetorix, Vladimir Lenin, Volodymyr Zelensky, Václav Havel, Võ Nguyên Giáp, William the Silent, Winston Churchill, Woodrow Wilson, Wu Zetian, Yasser Arafat

### 🌟 Mythology & Spirituality (55 persona)
Alan Watts, Amaterasu, Anansi, Apollo, Ares, Athena, Dionysus, Freya, Hades, Hephaestus, Hermes, Inanna/Ishtar, Isis, Jalal ad-Din Rumi, Jesus of Nazareth, Jiddu Krishnamurti, Kali, Krishna, Loki, Marduk, Meister Eckhart, Muhammad, Odin, Osiris, Paramahansa Yogananda, Persephone, Pierre Teilhard de Chardin, Prometheus, Quetzalcóatl, Ra, Ramana Maharshi, Shiva, Siddhartha Gautama (Buddha), Sundiata Keita, The Anima/Animus, The Fool, The Great Mother, The Hero, The Magician, The Puer Aeternus, The Senex, The Shadow, The Sibyl of Cumae, The Trickster, The Wise Old Man, The Witch, Thor, Tlaloc, Venus/Aphrodite, Vishnu, Zarathustra, Zeus

### 📖 Fiction (67 persona)
Achilles, Agent Smith, Ahsoka Tano, Anna Karenina, Arthur Dent, Arya Stark, Atticus Finch, Captain Ahab, Captain Nemo, Daenerys Targaryen, Darth Vader, Data (Star Trek), Don Draper, Don Quixote, Dorian Gray, Dracula, Edmond Dantès, Elizabeth Bennet, Emma Bovary, Emma Woodhouse, Ender Wiggin, Frankenstein's Monster, Gandalf, Geralt of Rivia, Gregor Samsa, HAL 9000, Hamlet, Hannibal Lecter, Hercule Poirot, Hermione Granger, Holden Caulfield, Huckleberry Finn, Humbert Humbert, Iago, Indiana Jones, Inspector Javert, Ivan Karamazov, Jay Gatsby, Jean Valjean, Katniss Everdeen, Kratos, Lestat de Lioncourt, Lisbeth Salander, Lord Jim, Macbeth, Master Chief, Medea, Morpheus, Odysseus, Patrick Bateman, Raskolnikov, Samwise Gamgee, Sauron, Sherlock Holmes, Sir John Falstaff, Spock, The Joker, Tony Soprano, Tyrion Lannister, Walter White, Winston Smith, Yoda, Yossarian

### 📚 Literature (40 persona)
Aeschylus, Albert Camus, Alexander Pope, Anton Chekhov, Aristophanes, Charles Baudelaire, Charles Dickens, Dante Alighieri, Edgar Allan Poe, Emily Dickinson, Euripides, Federico García Lorca, Franz Kafka, Fyodor Dostoevsky, Gabriel García Márquez, Georg Büchner, George Eliot, George Sand, Henry James, Homer, Honoré de Balzac, James Joyce, Jean Racine, Jonathan Swift, Jorge Luis Borges, Leo Tolstoy, Longinus, Miguel de Cervantes, Molière, Ovid, Samuel Beckett, Samuel Johnson, Sappho, Sophocles, Toni Morrison, Victor Hugo, Virgil, Virginia Woolf, William Blake, William Shakespeare

### 🎨 Arts & Music (32 persona)
Antonio Vivaldi, Billie Holiday, Caravaggio, Claude Monet, Frank Lloyd Wright, Frida Kahlo, George Orwell, Georgia O'Keeffe, Gustav Mahler, Igor Stravinsky, James Baldwin, Jean-Paul Sartre, Johann Sebastian Bach, John Coltrane, Joseph Haydn, Langston Hughes, Ludwig van Beethoven, Michelangelo Buonarroti, Miles Davis, Niccolò Paganini, Octavia E. Butler, Pablo Neruda, Pablo Picasso, Rembrandt van Rijn, Richard Wagner, Robert Schumann, Salvador Dalí, Umberto Eco, Vincent van Gogh, Wassily Kandinsky, Wolfgang Amadeus Mozart

### ♟️ Strategy & History (9 persona)
Herodotus, Ibn Khaldun, Plutarch, Sun Wu (Sun Tzu), Tacitus, Thucydides, Wu Qi, Xenophon, Yuval Noah Harari

---

## BÖLÜM 4 — RENK & STIL REHBERİ

### Ana Renkler
| Kullanım | Hex Kodu | Açıklama |
|----------|----------|----------|
| Primary  | `#4f46e5` | İndigo — butonlar, vurgular |
| Secondary| `#7c3aed` | Mor — hover, gradient |
| Background Dark | `#0f0f1a` | Ana arka plan |
| Card Dark | `#1a1a2e` | Kart arka planı |
| Text Primary | `#f1f5f9` | Ana metin |
| Text Muted | `#94a3b8` | İkincil metin |
| CEID Gold | `#f59e0b` | Elite rozet rengi |
| Ethics Blue | `#3b82f6` | Etik ekseni rengi |
| Power Red | `#ef4444` | Güç ekseni rengi |

### Kategori Renkleri
| Kategori | Renk |
|----------|------|
| Philosophy | `#8b5cf6` mor |
| Science | `#06b6d4` cyan |
| Leadership | `#f59e0b` altın |
| Fiction | `#ec4899` pembe |
| Mythology | `#a78bfa` lila |
| Literature | `#34d399` yeşil |
| Arts | `#f97316` turuncu |

---

## BÖLÜM 5 — STITCH İÇİN PROMPT ÖNERİSİ

```
Design a premium dark-mode AI persona marketplace called "Persona Hub".
Color scheme: deep indigo (#4f46e5) primary, dark backgrounds (#0f0f1a), 
glassmorphism cards with subtle borders.

Pages needed:
1. Landing page with hero, featured personas grid, pricing section
2. Catalog page with search, category filters, persona cards grid
3. Persona detail page with HPEP-100 profile bars and CEID score gauge
4. User dashboard with API key, purchases, subscription status
5. Chat interface (HF Space) with persona selector sidebar

Card style: floating glass cards, emoji avatar, name, era, domain tag, 
CEID score with progress bar, price, hover CTA button.

Typography: Inter font, clean modern SaaS aesthetic.
Inspirations: Linear, Vercel, Anthropic's website.
```

---

*Dosya son güncelleme: Persona Hub v1.0 — 495 persona, 8 sayfa, 2 abonelik tieri*

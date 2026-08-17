# DubForge & DubStage

Szenen aus Videos selbst nachsprechen. **DubForge** zerlegt ein Video in einsprechbare Clips, **DubStage** nimmt deine Stimme auf und spielt die Szene am Stück damit ab.

*English version: `README_EN.md`*

---

## Einmalig einrichten

1. Alle Dateien in einen Ordner legen, z. B. `F:\DubForge`
2. **`Start DubForge.bat`** zum Bauen bzw. **`Start DubStage.bat`** zum Einsprechen doppelklicken

Ein eigener Installationsschritt ist nicht nötig: Der erste Start merkt, dass noch nichts eingerichtet ist, holt das nach und öffnet danach das Werkzeug. Jeder weitere Start geht direkt hinein. Wer lieber vorher einrichtet, nimmt weiterhin **`Setup.bat`**.

Das Setup holt Python-Pakete, lädt ffmpeg in einen `tools`-Unterordner, bietet Verknüpfungen auf dem Desktop an und fragt, ob Demucs für die Stimmen-Trennung installiert werden soll. Demucs zieht PyTorch nach — mehrere hundert MB bis ~2 GB. Wenn du Nein sagst, läuft alles weiter, nur ohne Backing-Track.

---

## Sprache umstellen

Oben rechts im Fenster: **Deutsch / English**. Wirkt sofort — Beschriftungen, Meldungen, Dialoge und Fehlertexte. Eingaben bleiben erhalten. Die Wahl wird gemerkt.

---

# DubForge — Packs bauen

**1. Quelle**

Entweder YouTube-Link einfügen oder eine lokale Datei wählen (MP4, MKV, MOV, WEBM, auch reine Audiodateien). Bei „Von" und „Bis" die Zeitspanne eintragen — `1:30`, `0:02:15.5` oder einfach `95` für Sekunden. Leer lassen = alles.

Dann **„Laden und analysieren"**. Das Tool lädt bzw. schneidet, extrahiert den Ton, trennt die Stimmen von Musik und Geräuschen und sucht selbst die Sprechabschnitte.

**„Pack weiterbearbeiten …"** lädt einen früher gebauten Pack wieder — Video, Backing-Track, Clips, Spuren und Untertitel —, damit du daran weiterarbeiten kannst. Packs aus älteren DubForge-Versionen gehen auch; ihre Clips werden aus den Dateinamen gelesen.

**2. Clips und Spuren**

Die Zeitleiste zeigt oben die Wellenform und darunter **eine Spur je Sprecher**. Erkannte Clips landen auf der ersten Spur; zieh sie auf andere Spuren. Zeilen, die sich überschneiden — jemand fällt ins Wort, zwei reden gleichzeitig — liegen einfach auf verschiedenen Spuren.

**Benenne die Spuren nach dem Sprecher** (Doppelklick auf den Namen links, oder Rechtsklick fürs Menü). Der Name landet im Dateinamen des Clips, `03_Snake_5-460.wav` — genau daraus verteilt DisDubs die Rollen, und DubStage zeigt ihn als Beschriftung.

| Aktion | Wie |
|---|---|
| Clip anlegen | in einer Spur über leerem Bereich aufziehen |
| Clip verschieben | ziehen — seitlich in der Zeit, hoch oder runter auf eine andere Spur |
| Trimmen | linken oder rechten Rand ziehen |
| Auswählen | anklicken, oder die Zeile in der Liste |
| Anhören | Doppelklick auf den Clip, **Leertaste** oder der ▶-Knopf; Doppelklick auf die Wellenform spielt 8 s ab dort |
| Über die Kanten hinaus hören | standardmäßig an: **Anlauf ±0,5 s** neben ▶ spielt eine halbe Sekunde vor und nach dem Clip — so hörst du, ob die Zeile abgeschnitten ist. Ausgeschaltet startet die Wiedergabe da, wo der Zeiger steht |
| Feinjustieren | ← → (0,05 s), mit Shift 0,01 s, mit Strg 0,5 s |
| Spur wechseln | ↑ ↓, oder das Feld „Sprecher / Spur" |
| Teilen | **S** oder der Knopf — am Playhead, wenn er im Clip steht, sonst in der Mitte |
| Duplizieren / löschen | Strg+D / Entf |
| Rückgängig / wiederholen | Strg+Z / Strg+Y (auch die Knöpfe ↶ ↷) |
| Zoomen | Strg + Mausrad an der Mausposition, Mausrad allein scrollt; Pos1 / Ende springen |
| Spur hinzufügen | **+ Spur**, oder Klick auf die Zeile unter der letzten Spur |
| Spur umbenennen, umfärben, sortieren, löschen | Rechtsklick auf den Spurnamen |

Zu viele oder zu wenige Clips? **Erkennung ▾** öffnen, **Empfindlichkeit** oder **Max. Cliplänge** ändern und **„Jetzt neu erkennen"** wählen — das ersetzt alle Clips (Rückgängig holt sie zurück).

**Untertitel:** Clip anklicken, ins Untertitelfeld tippen, **Enter** — das speichert und springt gleich zum nächsten Clip. So arbeitest du dich ohne Mausklicks durch. Die **Leertaste** im Untertitelfeld hört den Clip an, solange noch nichts getippt ist (und stoppt ihn wieder); sobald Text im Feld steht, ist sie ein ganz normales Leerzeichen. Das kleine Bild links zeigt das Videobild am Clipanfang, damit du siehst, wer gerade spricht — und beim Anhören läuft dort das Video mit. Freiwillig: Clips ohne Untertitel funktionieren normal.

Das Menü **Untertitel ▾** füllt sie auf Wunsch vor: aus einer SRT- oder VTT-Datei oder direkt von YouTube (die eigenen Untertitel des Videos, sonst die automatischen — die sind eher ein Rohentwurf). Die Cues werden über die Zeit den Clips zugeordnet; ob vorhandene Untertitel überschrieben werden, entscheidest du.

**3. Bauen**

Pack-Name eintragen (und, wenn du magst, deinen Namen als Autor), Häkchen bei **„Mit Video"** setzen (nötig für DubStage und DisDubs), dann **„Pack bauen"**. Vorher prüft DubForge den Pack so, wie DisDubs ihn lesen wird, und sagt, wenn etwas auffällt — vor allem die Besetzungsregel: DisDubs nimmt die Spurnamen nur dann als Rollen, wenn es höchstens halb so viele Sprecher wie Clips gibt (drei Sprecher auf fünf Clips werden eine Rolle). Der Pack landet im Ordner `packs` neben dem Tool — genau dort sucht DubStage. Danach bietet ein Dialog **„Als ZIP für DisDubs"** (`<Name>.zip`, direkt in die Szenenauswahl von DisDubs ziehen), den Ordner oder eine Kopie in den Zielordner an. Gibt es den Namen schon, fragt DubForge, ob überschreiben oder als `Name_2` speichern.

Jeder lange Vorgang — Download, Stimmen-Trennung, Videokonvertierung — zeigt echten Fortschritt und lässt sich mit **Abbrechen** neben dem Balken stoppen.

**Wenn etwas schiefgeht:** das Protokoll (**Protokoll ▾** unten, zusätzlich in `dubforge.log` neben dem Programm) sagt, welches Werkzeug woran gescheitert ist; YouTube-Fehler werden verständlich übersetzt und bieten, wo es hilft, das yt-dlp-Update an. Fehlende Werkzeuge stehen in einer gelben Zeile unter dem Titel mit Verweis auf Setup.bat.

## Was im Pack landet

| Datei | Wofür |
|---|---|
| `01_Snake_44-048.wav` | Ein Clip. Der mittlere Teil ist der Spurname (Sprecher), die Zahl hinten der Startzeitpunkt im Video (44,048 s) |
| `dub_video.mp4` | Das Video zur Szene |
| `_backing_track.wav` | Musik und Geräusche ohne Stimmen |
| `_captions.json` | Die Untertitel, nach Clip-Dateiname |
| `_TIMESTAMPS.txt` | Übersicht aller Startzeiten, Sprecher und Untertitel |
| `_pack_info.ini` | Titel und Autor — DisDubs liest das |
| `_dubforge.json` | Das Projekt: Spuren, exakte Clipgrenzen, Untertitel. Damit kann DubForge den Pack wieder öffnen. DubStage und DisDubs ignorieren die Datei |
| `_README.txt` | Kurzinfo |

Alle Clips werden laut normalisiert (Peak −1 dBFS), damit beim Vergleich nicht die Lautstärke stört.

---

# DubStage — einsprechen

Pack auswählen → **Loslegen**. Pro Zeile:

| Knopf | Was passiert |
|---|---|
| **▶ Original** | Das Videostück läuft mit der Originalzeile |
| **● Aufnehmen** | 3-2-1, dann läuft dasselbe Stück und du sprichst drüber |
| **▶ Meine Aufnahme** | Deine Aufnahme direkt anhören, zum Video |
| **Zeile leer lassen** | Aufnahme verwerfen, die Zeile behält das Original |
| **‹ Zurück / Weiter ›** | Zeile wechseln |

Unter dem Video steht groß der **Untertitel** der Zeile. Die Leiste darüber zeigt alle Zeilen: grün = aufgenommen, gelb = wo du gerade bist. Direkt anklickbar, um zu springen.

Nach der letzten Zeile führt **Fertig** ins Finale: die ganze Szene läuft mit deiner Stimme, der Untertitel läuft mit. **Als Video speichern** legt eine MP4 im Ordner `dubs` ab. **‹ Zurück zu den Zeilen** geht jederzeit wieder rein.

Tastatur: **Leertaste** nimmt auf bzw. startet das Finale, **Esc** geht zurück.

## Der Vergleichsstreifen

Über der Knopfreihe liegt das eigentliche Werkzeug: die **Originalspur als blaue Silhouette**, darüber halbtransparent **deine Aufnahme** — beim Aufnehmen rot und live mitwachsend, danach grün. Eine goldene Marke zeigt, wo du gerade bist.

Beide Kurven teilen sich dieselbe Zeitachse, die bei Null des Clips beginnt. Damit siehst du auf einen Blick, ob du zu früh oder zu spät einsetzt und ob deine Pausen sitzen: liegen die Blöcke übereinander, passt das Timing. Der Streifen ist etwas breiter als das Original, weil nach dem Clip noch 0,7 Sekunden weiter aufgenommen wird — Platz, um den Satz zu Ende zu sprechen.

Beide Kurven werden auf ihre eigene Lautstärke normiert, verglichen wird also Rhythmus und nicht Pegel. Ist deine Aufnahme zu leise, steht das als Hinweis rechts unten.

## Mikrofon

Im Menü gibt es **Testen**: zwei Sekunden aufnehmen, Pegel ablesen, Wiedergabe. Falls nichts ankommt, im Auswahlfeld daneben ein anderes Gerät nehmen.

## Bildrate

Standard sind **25 Bilder pro Sekunde** bei 960 px Breite. Das Video wird dafür einmalig in Einzelbilder zerlegt und unter `%TEMP%\dubstage_cache` abgelegt, rund 37 MB pro Minute Video.

Falls dein Rechner ruckelt oder der Platz knapp wird, in `dubstage_settings.json` ändern:

```json
"video_fps": 20
```

Erlaubt sind 8 bis 30. Die Bilder werden beim nächsten Öffnen des Packs neu erzeugt.

## Packs, die nicht auftauchen

Gesucht wird im Ordner `packs` neben den Tools. Über **Ordner hinzufügen** lässt sich jeder weitere Ordner dauerhaft mit durchsuchen.

Damit ein Ordner als Pack zählt, braucht er ein **`dub_video`** (mp4, ogv, mkv, webm, mov oder avi) und mindestens einen Clip mit Zeitstempel im Dateinamen.

---

## Updates

Beide Werkzeuge fragen beim Start bei GitHub nach, ob es eine neuere Fassung
gibt — höchstens alle sechs Stunden. Wenn ja, erscheint oben ein Banner: es
nennt die Version, **Was ist neu** klappt den Changelog dieser Version auf, und
**Jetzt aktualisieren** spielt sie ein. Das Archiv wird geladen und geprüft, die
App schließt sich, die Dateien werden getauscht und die App startet neu — dauert
ein paar Sekunden.

`packs/`, `dubs/`, `tools/` und die Einstellungen werden dabei nie angefasst. Es
werden nur die Programmdateien ersetzt, und die alten landen vorher in einem
Sicherungsordner unter `%TEMP%`, mit einem Protokoll daneben.

Außer beim Herunterladen eines Videos, das du selbst angibst, ist das der
einzige Moment, in dem eines der Werkzeuge ins Netz geht — gesendet wird nichts.
Abschalten lässt es sich mit `"check_updates": false` in
`dubforge_settings.json` oder `dubstage_settings.json`.

---

## Wenn etwas klemmt

**Windows blockiert die BAT-Dateien** — Rechtsklick → Eigenschaften → unten **Zulassen**. Oder in PowerShell im Ordner: `Get-ChildItem -Recurse | Unblock-File`. Wichtig: die Dateien vorher aus dem Download-Ordner in einen normalen Ordner verschieben.

**„ffmpeg nicht gefunden"** — Setup.bat nochmal laufen lassen. Klappt das nicht: bei `gyan.dev/ffmpeg/builds` die **release full** ziehen und `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe` aus `bin` in `tools\` legen.

**YouTube-Download schlägt fehl** — Fast immer ist yt-dlp veraltet. YouTube ändert ständig etwas an der Auslieferung, deshalb hält das Werkzeug nur wenige Wochen. In DubForge oben rechts auf **yt-dlp aktualisieren** klicken; die Version samt Alter steht beim Start im Protokoll. Von Hand geht es im Terminal mit `py -m pip install --upgrade yt-dlp`.

**Demucs bricht ab** — Kein Beinbruch, das Tool schaltet automatisch auf den Originalton um. Dann fehlt nur der Backing-Track.

**Clips sitzen leicht daneben** — Bei YouTube-Downloads kann der Schnitt am Keyframe hängen. Zeitspanne ein paar Sekunden großzügiger setzen und im Editor nachjustieren.

**Mikrofon nimmt nichts auf** — Im DubStage-Menü ein anderes Gerät wählen und **Testen** drücken.

---

Beim Material bist du selbst dafür verantwortlich, nur zu verwenden, wozu du berechtigt bist.

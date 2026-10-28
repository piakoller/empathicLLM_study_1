# Fragebogen – Übersicht

Stand 28.10.2026, aus `questionnaire_questions.json`. Gekürzt von 31 auf 20 Fragen für Patienten:
doppelte oder schwer verständliche Fragen gestrichen, vorher und nachher gleiche Befindens-Fragen.

Likert-Skala (5-stufig), sofern nicht anders angegeben:

| Wert | Bedeutung |
|------|-----------|
| 1 | Gar nicht |
| 2 | Ein wenig |
| 3 | Mässig |
| 4 | Ziemlich |
| 5 | Sehr |

---

## VOR den Antworten

### Emotionaler Zustand

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 1 | `pre_calm` | Ich fühle mich ruhig. | Skala 1–5 | nur Patienten |
| 2 | `pre_tense` | Ich fühle mich angespannt. | Skala 1–5 | nur Patienten |
| 3 | `pre_worried` | Ich mache mir Sorgen um meine Gesundheit. | Skala 1–5 | nur Patienten |
| 4 | `pre_confident` | Ich fühle mich sicher darin, medizinische Informationen zu verstehen. | Skala 1–5 | nur Patienten |

### Grundvertrauen in digitale Gesundheitswerkzeuge

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 5 | `pre_trust_digital` | Ich vertraue generell darauf, dass digitale Gesundheitstools hilfreiche Informationen liefern. | Skala 1–5 | alle |

### Ihre Entscheidung zur PSMA-Therapie

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 6 | `pre_sure_s` | Fühlen Sie sich sicher, was für Sie die beste Entscheidung zur PSMA-Therapie ist? | Ja / Nein | nur Patienten |
| 7 | `pre_sure_u` | Kennen Sie die Vorteile und Risiken der PSMA-Therapie? | Ja / Nein | nur Patienten |
| 8 | `pre_sure_r` | Ist Ihnen klar, welche Vorteile und Risiken Ihnen am wichtigsten sind? | Ja / Nein | nur Patienten |
| 9 | `pre_sure_e` | Haben Sie genügend Unterstützung und Beratung, um Ihre Entscheidung zu treffen? | Ja / Nein | nur Patienten |


---

## NACH den Antworten

### Emotionaler Zustand

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 1 | `post_calm` | Ich fühle mich ruhig. | Skala 1–5 | nur Patienten |
| 2 | `post_tense` | Ich fühle mich angespannt. | Skala 1–5 | nur Patienten |
| 3 | `post_confident` | Ich fühle mich sicher darin, medizinische Informationen zu verstehen. | Skala 1–5 | nur Patienten |

### Empathie

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 4 | `post_empathy_tone` | Der sprachliche Tonfall des Systems war durchgehend respektvoll und unterstützend. | Skala 1–5 | alle |

### Klinische Qualität & Sicherheit

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 5 | `post_misleading` | Das System hat irreführende oder sachlich falsche Informationen geliefert. | Skala 1–5 | alle |

### Vertrauen

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 6 | `post_trust` | Ich hatte insgesamt Vertrauen in die Antworten des Systems. | Skala 1–5 | alle |
| 7 | `post_recommend` | Ich würde den Einsatz eines solchen Systems als Unterstützung (z. B. zur Vorbereitung auf das Arztgespräch) befürworten. | Skala 1–5 | nur Patienten |

### Ihre Entscheidung zur PSMA-Therapie

| # | Key | Frage | Antworten | Wer |
|---|-----|-------|-----------|-----|
| 8 | `post_sure_s` | Fühlen Sie sich sicher, was für Sie die beste Entscheidung zur PSMA-Therapie ist? | Ja / Nein | nur Patienten |
| 9 | `post_sure_u` | Kennen Sie die Vorteile und Risiken der PSMA-Therapie? | Ja / Nein | nur Patienten |
| 10 | `post_sure_r` | Ist Ihnen klar, welche Vorteile und Risiken Ihnen am wichtigsten sind? | Ja / Nein | nur Patienten |
| 11 | `post_sure_e` | Haben Sie genügend Unterstützung und Beratung, um Ihre Entscheidung zu treffen? | Ja / Nein | nur Patienten |

---

Die SURE-Fragen (Légaré et al. 2010) vor dem Einsatz mit der validierten deutschen Version abgleichen.

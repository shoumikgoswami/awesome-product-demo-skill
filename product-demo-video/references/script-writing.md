# Writing and mapping the script

## Mode A - the user supplied a script
- Keep their wording. Change only what the voice needs (`say`: spell acronyms, expand symbols) and split into one-sentence entries.
- `parse_script.py` supports a light format (`# chapter`, `## scene`, `[img: file]`, `[zoom: phrase]`, `[click: phrase]`, `[chip: text]`, `[blur: x,y,w,h]`);
  plain paragraphs separated by blank lines also work: one paragraph = one scene.
- **Mapping**: explicit `[img:]` pins win; otherwise scene *n* gets screenshot *n* (natural-sorted by file name). When counts differ the tool says so.
  Resolve by looking at the screenshots and matching content (what the paragraph describes vs what the screen shows). Reuse one screenshot for several
  scenes when a paragraph is long; split a long paragraph across two screenshots when it describes two screens. Report your final mapping table to the user.
- If the script describes something no screenshot shows, say so; do not fake a screen.
- A sentence over ~25 words: split it at a natural break and tell the user.

## Mode B - write the script from screenshots + instructions
### 1. Understand
Open every screenshot (and `inspect/grid`). For each: what screen is it, what is the user doing, what is the key element, what is the outcome.
Combine with the instructions: audience (admin, end user, buyer, developer), goal (activate, sell, onboard), tone (confident/plain/friendly), length.
Facts you cannot see (pricing, limits, integrations, timings) come only from the user or supplied text. If a claim would make the video better but you
cannot verify it, leave it out and mention it in your final message. Where the copy needs a product name or term, read it off the UI exactly as written.

### 2. Shape
Default structure (3-4 minutes is the sweet spot; 60-90 s for a single feature):
1. **Hook (1-2 sentences)**: the outcome or problem, not "Welcome to our product".
2. **Overview**: what the viewer will see, in one sentence.
3. **Steps (3-5)**: one chapter each; one to three sentences per screenshot; verb-first ("Open Reports, then choose New report.").
4. **Result**: what they now have.
5. **Close**: one next step (try it, where to start). No invented URLs: use only supplied ones.

### 3. Write for the ear
- **One idea per sentence, 8-22 words**, never over 25. Short sentences keep the TTS stable and the captions readable.
- Pace: about 2.4 spoken words per second incl. pauses -> 150 words ~ 1 minute. A scene with one sentence lasts ~4-6 s.
- Describe what is on screen *as it is being shown*; name the UI labels exactly ("choose **New report**") so `focus.on` phrases line up.
- Active voice, second person ("you"), present tense. No filler ("simply", "just", "basically"), no marketing superlatives you cannot back up.
- No parentheses, slashes, emoji, markdown or URLs read aloud. Spell numbers/units the way they should be said ("twenty-eight percent", "ten megabytes"). Acronyms: write them as the
  audience reads them in `caption` and respell in `say` ("A P I") or via `pronunciations`.
- Don't read the screen word for word; say what matters and let the highlight do the pointing.
- Each sentence must be true of its screenshot: if the sentence mentions a button, that button is on that screen.

### 4. Show it
Before voicing, present the script to the user as a compact table (scene, screenshot, narration) and one line on tone/length/chapters. Wait for a go/no-go only
if they are present and did not say "just do it"; otherwise proceed and flag it.

### 5. Cut guidance
- Over target length: merge scenes that show the same screen; drop the Overview; shorten the steps' second sentences.
- Under: add a callout scene for the result, a "what's next" line, or a second pass on the most important screen.

## Example scene (manifest form)
```json
{ "id": "s03", "image": "03-new-report.png", "chapter": "c2",
  "sentences": [
    { "id": "s03a", "caption": "Pick a data source, such as product events." },
    { "id": "s03b", "caption": "Then choose a metric and a date range, and generate the report." } ],
  "focus": [ { "on": "product events", "x": 0.2, "y": 0.22, "w": 0.23, "h": 0.155 },
             { "on": "generate", "x": 0.78, "y": 0.82, "w": 0.18, "h": 0.067, "click": true } ] }
```

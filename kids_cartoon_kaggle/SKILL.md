# Children's Cartoon Kaggle Generation

## Plan the session before you start it

- Check quota before you start and use only an account with quota left.

- Remember quota resets Saturday at 00:00 UTC and a session charges while open, including while it waits in the GPU queue.

- Gather every file, reference image and prompt before you start so the session never waits on a missing input.

- Never start a session that waits on a user click, because a browser upload approval only counts when the user clicks it in live chat and the session can die idle while it waits. The user has set uploads to allow always, so no approval prompt appears. If that changes, a session must never wait on a user click.

- Budget for a restart costing about 30 minutes to download the models again and for a queue that can take hours while quota keeps burning.

- Check disk space before you load the model, and if loading fails for a full disk delete the duplicate model in the checkpoints folder and link to the local model file before you restart.

- Use only accounts with quota left. Multiple accounts carry a ban risk (Kaggle has already shown a Multiple Accounts Alert), and the model dataset is the first account's private dataset, so verify another account can download it before relying on it.

- Keep the page touched at least every 20 minutes, because a session dies idle after about 30 minutes without a page click. The session watches page interaction, not whether a background task is running. After about 30 minutes without page interaction it asks "Are you still there?" and stops if nobody answers, even if a generation is running.

- Stop the session as soon as the work ends, and restart a fresh session rather than retrying in place after a long session degrades. A session running over 6 hours degrades and can die silently mid-generation. If a session dies in the middle of a shot, restart it with Run All and re-run that shot. After a restart the Gradio link changes, so report the new link.

## Write the episode script

- An episode is 15 shots. Shot 1 is the opening with no dialogue. Shots 2 to 15 have 2 spoken lines each.
- Each episode follows five parts: opening hook (0 to 5 seconds, the crisis is already in progress, the first line is a reaction not a greeting), escalation (5 to 15 seconds, the problem gets worse or the first attempt fails, and within 15 seconds the viewer knows the problem, the characters, and what to learn), question and answer (15 to 50 seconds, 3 to 4 rounds, speaking while doing), reversal (50 to 65 seconds, an unexpected small turn), warm ending (65 to 75 seconds, a hug, a high-five, or laughing together, freezing on Huihui's big laugh).
- Change the variant every 10 episodes to stay fresh: a new friend moves to town, a small misunderstanding, a small competition, or a small help.
- Core words: 5 to 8 per episode, each bound to the picture (when a core word is spoken, the picture must show it). Four core words are the episode's focus.
- Core sentence patterns: 2 to 3 per episode, each 8 words or fewer, each repeated at least twice by different characters.
- Question and answer: at least 3 rounds per episode, and the questions are concrete (Where is...? What is this? Can you help me?), never abstract.
- Picture first, then dialogue: a new word is shown in the picture before the line names it.
- Quiz: each episode has one pinned-comment multiple-choice question testing an easy-to-confuse point of the episode's core words.
- Do not teach: no grammar rules, no phonetics, no sentences over 8 words, no negative vocabulary.
- Humor: use at least 2 of the 4 mechanisms in every episode: reversal, misunderstanding, exaggerated expressions, physical comedy (a small trip, water in the face, being tackled by a friend — a brief sting, then a laugh, no injury, nothing scary).
- Health red lines, checked on every episode: no violent ending (no one hit, hurt, or driven away), no scary pictures (no night, no monsters, no sudden loud sounds), no negative values (no mocking, no bullying, no lying that succeeds — a lie is always found out and apologized for), conflict comes from misunderstanding and character, never good versus evil, and the ending is always reconciliation, a hug, or laughing together.
- Values are healthy and fun, never preachy. Each episode carries one small good quality (brave, friendly, sharing, honest, helpful) hidden inside the joke, never stated as a lesson.
- The series follows a full-day map. A kindergarten day runs EP2 to EP28 from waking to bedtime, then a day off follows. The same scene can produce many episodes with different small problems, words, and friends. Episode count has no cap.
- Episode map, kindergarten day (each with 4 core words): EP2 wake up — wake up, morning, sun, breakfast. EP3 wash face and brush teeth — wash, face, teeth, brush. EP4 get dressed — shirt, pants, shoes, put on. EP5 breakfast — breakfast, milk, bread, eat. EP6 pack bag and say goodbye — bag, bye-bye, mom, ready. EP7 walk to school — walk, school, bird, look. EP8 arrive and greet — hello, teacher, friend, morning. EP9 morning circle and sing — sing, song, circle, together. EP10 blocks — block, build, tower, red. EP11 snack — snack, apple, juice, hungry. EP12 story — story, bear, book, listen. EP13 draw — draw, sun, crayon, color. EP14 outdoor play — slide, swing, run, fun. EP15 lunch — lunch, rice, yummy, eat. EP16 nap — nap, quiet, sleep, tired. EP17 afternoon snack — snack, banana, milk, yummy. EP18 clean up toys — clean up, toy, put away, help. EP19 go home — home, see you, tomorrow, bye. EP20 arrive home and wash hands — home, wash, hands, soap. EP21 play at home — play, toy, ball, fun. EP22 help set the table — help, plate, table, mom. EP23 dinner — dinner, rice, vegetable, yummy. EP24 bath — bath, water, bubble, wash. EP25 brush teeth — brush, teeth, toothpaste, clean. EP26 pajamas — pajamas, soft, sleep, put on. EP27 bedtime story — story, moon, sleep, please. EP28 good night — good night, sleep, dream, sweet.
- Day-off episodes follow the same pattern (one real-life scene each): park, supermarket, zoo, beach and swimming, grandma's house, birthday party, doctor, rainy day at home, picnic, library, bus, playground, crafts, snow day, New Year, and more.
- Mass production: each episode is 1 scene times 1 to 2 supporting characters times 1 sentence pattern times 1 story routine. Scene library (20): grass, orchard, river, wooden house, mushroom house, swing, stone bridge, hill, flower field, snow, beach, library, market, vegetable garden, pond, tree house, sports field, picnic spot, rainbow after rain, starry camp. Sentence-pattern library (30): Where is...? What is this? Can you help me? I can try! Don't worry! Let's go! Thank you! You are welcome! I'm sorry! It's OK! Look at this! I like it! Let's play! Be careful! Good job! See you! How are you? I'm fine! What's your name? My name is... Do you like...? Yes, I do! No, I don't! It's mine! Let's share! Wait for me! Come on! Hurry up! Great! Oh no! Story-routine library (12): new friend, small misunderstanding, small competition, small help, find something, birthday, rainy day, sick, share food, work together, lost, learn a new skill.
- A script document has: metadata (episode number, title, 4 core words, core sentences, story line, announcement text, quiz question, duration), character set (the full appearance of every character in the episode, repeated in full in every shot's prompt), scene map (the fixed setting, layout, colors, light), and 15 shots (each with animals, background, action and timeline, dialogue, prompt, and check points).
- The fixed setting for the morning episodes is Huihui's bedroom: a large light-wood bed on the LEFT with a blue blanket, a small light-wood table next to the bed with a round red alarm clock, a window on the RIGHT wall with white frame and light blue curtains mostly closed, a light-wood wardrobe beside the window, a light-wood door on the FAR RIGHT, a low light-wood bookshelf with colorful books near the door, a few soft plush toys on the floor beside the bed, small framed children's drawings on the wall, a round soft warm-orange rug on the light-wood floor in the center. Wall warm cream, floor light wood, window shows a clear blue sky and a bright golden sun. Curtains closed means soft morning light through the gaps; curtains open means bright golden sunlight. The room layout and colors stay the same across the whole series so the characters never drift.
- Three gates, in order. Gate 1 (script): the script passes every rule in this section plus the political screen before any generation starts. Gate 2 (opening shot): Shot 1 is generated and verified first (the alarm is visible at t=0, t=1 and t=2, no dialogue, Huihui sits up and turns off the alarm) before the remaining shots are generated. Gate 3 (assembly): the assembled episode passes frame-by-frame check, ASR, and the political screen before delivery.

## Use MiniMax H3 Turbo (fused) as the only model

- Use MiniMax H3 Turbo INT8 as the only model, because the user chose it on 2026-11-27 after LTX-2.5 burned text into 15 of 15 quoted dialogue attempts.

- Do not use LTX-2.5 as the primary model, because its quoted dialogue burn, its slow generation and its camera push in were the reasons for the change.

- The working notebook is the Turbo copy on the current account (for example https://www.kaggle.com/code/tanjian2/minimax-h3-turbo-int8-video-audio). Do NOT use the 2K notebook https://www.kaggle.com/code/umairahmad341/minimax-h3 for reference images, because a full-text search confirmed it has no fused at all: its reference branch is dead code with n_refs=0.

- Step 1 sets H3_VARIANT="fused", which loads the MATLOWAI fused turbo file, about 21GB (minimax_h3_fused_refdelta_r1024_turbo8_mystic07_int8_convrot.safetensors), revision 8a8dffaa0cd99c6184833ae0a3b4e9b0089c17b3.

- Set TURBO_LORA=None. Never stack a PDMD LoRA on fused.

- The four variants are pdmd (default, FL2VA, no references), dmad, fused (Ref2VA turbo, references supported, 4 steps), and official (Ref2VA plus lightx2v 8-step LoRA, references supported). Use fused.

- Use sampler res_multistep with 4 steps.

- Expect about 19 to 22 minutes per shot from Turbo fused.

- The 720p setting actually outputs 1280x704. Pad the settled file to 1280x720 (8px black top and bottom, CRF 18) before delivery, and take the next shot's first frame from the padded settled file's last frame.

- Verify the model filename in the run metadata before you generate, and stop at once if it shows a different model.

- Name the exact model in every dispatch, and never dispatch with only a phrase such as run setup.

- H3 has no Negative Prompt box, so do not look for it and do not claim it was used.

- Turbo outputs directly. There is no 2K upscale step, so the 2K notebook's upscale hang does not exist here.

- Save any notebook change as a local copy, because a fused graft was already lost once when a private notebook went 404.

- If the video area is empty at the end of a generation, click "Load latest video" to recover it. Do not regenerate.

- Confirm Custom steps is 0 before each generation.

- The generation gate is 720p and the duration the current model and GPU setup requires (currently 6.5 seconds, about 157 frames, for H3 Turbo). The duration is set by the model and GPU, never hardcoded. If the interface does not offer the required duration, stop and report the available durations. Do not generate at the wrong duration.

- After a refresh or a new tab the form returns to defaults, so re-select 720p, 16:9, 6.5 seconds and re-upload the first frame before you generate.

## Write the prompt the H3 way

- Fill the structured fields separately: Scene/action, Spoken line/dialogue, Language, Sound effects, Background music. Write dialogue and background separately and let the model generate the voice, because the user ordered that route on 2026-11-27 and dropped audio driven video.

- The Spoken line/dialogue field contains ONLY the quoted lines, nothing before them. Any introduction written there is spoken aloud by the model.

- Speaker order and voice anchors go in the Scene/action field, for example "The goat speaks first, in a voice like young Nala... The tiger answers sleepily..., in a voice like young Simba..."

- The Scene/action field carries the picture, the speaker order with voice anchors, the lighting sentences, and a fixed closing sentence such as "Fixed wide camera, no camera movement. No subtitles, no captions, no text on screen, no extra limbs, the goat stands on two legs." Adjust the closing sentence per shot.

- The lighting sentences must contain the word "flat": "Bright, even, flat lighting throughout the scene, no shadows, no dark corners, no vignette." plus "Pure saturated colors, clean bright high-definition look, sharp details."

- Never write sunbeams, strong directional light, or golden light beams in the prompt. They conflict with even lighting, and the model follows the more specific one. That conflict is one of the three known causes of dark shots, with the other two being a dark first frame passed down the chain and the Turbo engine's own cinematic dark lean.

- The Sound effects field follows the script. Leave the Background music field empty, because music is added at assembly.

- Describe every animal in full in every shot's prompt, and keep only one of each animal in the whole episode.

- Remove "standing" from the appearance block when the action is not standing, because appearance wording can override the action sentence.

- When a shot's scripted lines are short and the shot is long, the model tends to add improvised sounds before them. Guard with "each line spoken once" and "only these two characters speak" in the scene. Whether to trim or keep any extra lead-in sound is the user's call.

- When a core word is spoken, the picture must show it. If the line says apple, an apple is visible in the picture. It does not have to be held in the hand. Do not let a core word be spoken over an unrelated picture.

- In a sleepy scene, when a character is just woken up, the sleepiness must be visible in the action as well as the voice: slow heavy movements, eyelids barely open, a big yawn, rubbing the eyes, arms rising slowly overhead in a stretch. Never write energetic words such as "bright and energetic" in the same prompt as sleepiness, because they fight the performance. This applies only to sleepy scenes, not to other scenes.

## First frames and reference images

- Never use the previous shot's last frame directly as the next shot's first frame. For every shot from shot 2 onward, first regenerate an identical high-quality still from the previous shot's settled last frame with the image model, and use that regenerated still as the first frame.

- The regenerated still keeps the same characters, poses, positions, room and door, and only raises the quality to the reference-image standard: flat, bright, even light, clean saturated colors, sharp HD. Resize it to 1280x720 and show it to the user before the shot is dispatched.

- The regenerated still gets closer to the reference look, but it cannot be pixel-identical to the last frame. Judge it by whether the characters, poses, and composition match and the quality is high, not by pixel equality.

- Put only characters present at the opening in the first frame.

- Check that the first frame expression matches the opening moment, with eyes closed when the character is asleep at the opening.

- Verify the first frame is actually present in the Start frame slot before you generate, because one run dropped it and ran as text only with the wrong opening.

- Reference images work only in fused. Pass up to 3 images plus ref_names, and a first frame and reference images can be used together. That is the normal fused path.

- Pass reference images for every character who appears in the shot, together with the first frame. The first frame and the character images are both mandatory inputs for every shot. This replaces the earlier rule that reference images were only for characters who enter after the first frame.

- Use the End frame slot when a shot needs both ends anchored. The opening shot uses first plus end frames per the user's approval. It is a normal Turbo slot, not a trial.

## Characters and picture style

- The style is 3D cute-pet animation, chubby round bodies, big round heads (head about 1/3 of body height), soft toy-like fur.

- Huihui is a white tiger: white fur with grey-black stripes, red vest with gold buttons open at the front, red shorts, big round deep-blue eyes. He is about 7 years old, strong, boyish, brave, and friendly. His catchphrases are "I can try!", "Don't worry, I'm here!", and "We are friends!"

- Ningning is a white goat: white fur, pink dress and pink scarf, small horns, standing on two legs like a person. She is Huihui's younger sister, about 4 years old, gentle, curious, and she asks "why" — she is the one who asks the questions and Huihui answers. Her voice must be clearly a girl's voice, never a boy's.

- Tiaotiao is a white rabbit: white fur, long upright ears with pink inner ears, pink bow headband, red dress, standing on two legs. Only one white rabbit exists in the whole series.

- Zhuangzhuang is a grey-blue little elephant: plain grey-blue skin with subtle wrinkles (smooth skin, NOT furry), big floppy ears, long trunk in front, NO clothes and NO vest (deliberate), clearly bigger than the other animals, chubby round body, big round head, small round friendly eyes with highlights, friendly smile. Bipedal, standing on 2 legs, 2 arms.

- Pipi is a brown monkey: soft plush brown fur, red cap, long tail, no other clothes (deliberate), huge round eyes with highlights, chubby round body, big round head, small round ears. Bipedal, 2 arms 2 legs.

- Dudu is a brown bear: soft plush brown fur, round chubby body, yellow cap, no other clothes (deliberate), small round ears, huge round eyes with highlights, big round head, honey pot. Bipedal, 2 arms 2 legs.

- Qiuqiu is a brown hedgehog: soft rounded spines (cute 3D, NOT sharp), carrying a small red apple, no clothes (deliberate), huge round eyes with highlights, small round body, big round head, small round ears. Bipedal, 2 arms 2 legs.

- Huahua is a light brown deer: soft plush light brown fur, white spots, flower crown, no clothes (deliberate), huge round eyes with highlights, chubby round body, big round head, long legs but bipedal standing. Bipedal, 2 arms 2 legs.

- The adult characters (Mom, Teacher, Grandma, Doctor) have their voices anchored, but their appearance is NOT yet set. A new adult character's appearance must be shown to the user and confirmed before it is used.

- Every character's clothes are written out piece by piece in every shot's prompt, or the prompt states plainly that the character wears no clothes on purpose. Never leave clothing out.

- The character reference images are the gold standard for how each character looks. They sit in the same directory as this skill (huihui_char_ref.png, ningning_char_ref.png, tiaotiao_char_ref.png); download them with the skill. If a character has no reference image yet, regenerate it following the appearance descriptions in this section.

- Eyes are very large perfect circles, deep-blue irises, large black pupils, two white highlights. Eyebrows are thin, soft, slightly arched, never slanted.

- New characters are generated in the established set style. The user no longer needs to see each new character first (relaxed 2026-11-26).

- Check head-to-body proportion on every final shot, count limbs on every animal in every frame (never six legs), count each animal once, and check that a bipedal character stands on two legs like a person.

- The target look matches the character reference images: flat, bright, even light, clean colors, no shadows.

- Do NOT add anti-cinema prompt wording. The user withdrew the "cinema feel" complaint on 2026-11-28. Brightness, flat light, clean colors, and HD still stand.

## Dialogue and voice

- Dialogue is US Grade 3 level (8 to 9 year old native speakers). Every line is a complete natural sentence of 7 words or fewer, and its Chinese translation must be instantly clear to someone who does not read English.

- The vocabulary list must cover the dialogue's key words, not only the core words.

- Each shot has 2 lines, except the opening shot, which has no dialogue.

- Voice anchors are all Lion King characters: Huihui is young Simba, Ningning is young Nala, Tiaotiao is Nala higher and more lively, Zhuangzhuang is young Pumbaa, Pipi is Timon, Dudu is young Mufasa, Qiuqiu is Zazu, Huahua is Nala gentler and more elegant. The adult characters are also anchored: Mom is Sarabi, Teacher is adult Nala, Grandma is older Sarabi, Doctor is Mufasa. The last three child characters are assigned by image inference and the user has the final say if they differ. Timbre and pitch come from the anchor alone, so put no pitch words in the anchors.

- Per-line delivery follows the script's emotion words (sleepily, excitedly, and so on), which take priority over the anchor's default mood.

- Treat sleepiness as emotion in the performance, not as slower audio, and do not slow audio to 0.75x or 0.7x to fake a sleepy voice.

- In a sleepy scene, the voice itself must carry the sleepiness. A sleepy picture cannot substitute for a sleepy voice, so a clear wide-awake voice over sleepy pictures is not acceptable. This applies only to sleepy scenes, not to other scenes.

## Opening, announcement, and music

- Shot 1 is the opening: no dialogue, a crisis close-up, the announcement, at least 2 seconds of interval, then the protagonist's first silent physical reaction. The slow push-in on shot 1 is done at assembly, not by the video model.

- Shot 2 is the hook: protagonist reaction plus the first two story lines. The first line is a reaction, not a greeting, and contains at least one core word. Title plus 4 core words are overlaid on this shot.

- Shot 3 is the escalation: the problem gets worse or the first attempt fails. Within 15 seconds the viewer knows the problem, the characters, and what to learn.

- The announcement is a child's Chinese voice saying "跟着灰灰学英语：{episode title}", added at assembly with Chinese child TTS, never via Kaggle. Its duration is measured from that episode's title TTS, never fixed. The announcement text is overlaid in gold with a dark outline on the moving picture, sized to fit one line, and it vanishes with the voice. At least 2 seconds of silent reaction follow before any story speech. The announcement sound is 80% of dialogue level. It is a brand sound, not lesson narration, and the no-narration rule still holds.

- Background music is one continuous piece per episode, same style and speed, never changed between shots. Dialogue is 100%, music at normal volume is 25% (12dB below dialogue), and during dialogue it drops to about 3% (18dB below normal, 30dB below dialogue). Volume changes use 0.5-second fades, never hard cuts. The style is light, bright, gentle, piano-led, about 100 to 110 BPM. Music runs at normal volume for the opening, the ending hug, and the quiz card, and is lowered during dialogue.

## Verify every shot yourself

- Never trust the browser's report of resolution, pose, camera, transcription, or download size. Verify every shot yourself.

- Extract frames and check for burned-in text on every frame, including the first frame of a no-dialogue shot, plus two legs, the action, and the characters.

- Run ASR yourself with asr_words.py on a 16kHz mono wav with HF_HUB_OFFLINE=1. Whisper hallucinates on non-speech, so verify pauses with ffmpeg silencedetect (noise=-40dB, d=0.2, -v info).

- Confirm the downloaded file exists in ~/workspace/browser_downloads/ with the expected byte count before you verify it.

- Acceptance: dialogue correctness is the ONLY hard standard. Eyes widening on waking is natural, not a defect. Close-ups and push-ins are not a hard requirement. Still hard: the mouth must genuinely move with the dialogue, there must be no burned-in text (never accept misspelled on-screen text and never hide it by cropping), and the characters and image must stay consistent. A prop slightly off is acceptable, so do not reshoot for a prop alone.

- If blue speckle appears, change the seed, because the speckle was already in the preview and was cured by a seed change, not by changing the upscale.

- Trim only the affected opening frames when the rest is clean, and trim only the minimum the user approved.

- Brightening recipe for settled files: eq=gamma=1.25:brightness=0.03:saturation=1.2, unsharp=5:5:0.8:5:5:0.0, CRF 18.

- The assistant verifies each shot itself and retries automatically with a new seed when a shot fails verification. Only the final whole episode is delivered to the user. Publication needs the user's explicit order.

- Check on a running generation on a schedule and retry it yourself when it fails. Do not wait for the user to ask.

- The user is the final judge of the finished episode. A shot the assistant passes can still be rejected by the user, and that verdict stands.

- Keep generic rules in this skill and keep episode titles, script lines, shot counts and numbers in that episode's script.

## Do not retest what already failed

- Do not retest LTX-2.5 quoted dialogue, a negative prompt, NAG 11, the DEV model, or NAG 15 as a cure for burned-in text. NAG 15 only reduces it and does not cure it, and quoted dialogue burned text in 15 of 15 attempts.

- Do not retest audio driven video (A2V). The user dropped it on 2026-11-27 because its fixed audio could not carry a sleepy voice.

- Do not retest Sulphur-3 as a replacement for LTX-2.5. The W4A8 build failed to load and the INT8 build finished with every frame black.

- Do not retest MultiTalk without a fresh direction from the user, because it was cancelled after repeated session deaths.

- Do not retest lowering Source Strength from 1 to 0.7 as a fix for frozen action, because a shot with that change looked the same as the shot before it.

- Do not retest slowing audio to fake sleepiness, and do not retest feeding clean F5-TTS audio into CosyVoice to add sleepiness, because F5-TTS clones only the emotion already in its reference and CosyVoice instruction mode reads the instruction aloud or fails.

- Do not retest XTTS for child voice cloning. Five versions failed because it is trained on adult voices and clones a child's high pitch with a sandy, distorted sound.

- Do not retest the 2K notebook for reference images. It has no fused and its reference branch is dead code.

- Prove any new mouth method on a single shot first and only then redo earlier shots with it.

- Never use a no-dialogue picture plus separate dubbing as a finished shot, because that route is retired.

## Delivery

- Settled files are padded to 1280x720 and brightened with the recipe above. The next shot's first frame is a high-quality still regenerated from the settled file's last frame, never the last frame itself.

- Assembly splices the settled shots, burns bilingual subtitles, adds the quiz card, and mixes the announcement, dialogue, and music. Subtitles are burned in, centered lower, English on top in white bold with a black outline and a large size, Chinese below, each line 2 to 4 seconds and synced with the dialogue.

- Deliver the finished episode via Google Drive (the episode folder) and the home server video folder.

- A Word document goes with each episode (subtitle script first, then the vocabulary list), named by the episode title in simplified Chinese.

- Publish only on the user's explicit order, only on Monday, Wednesday, or Friday, in episode order.

- Every frame and every line passes the political screen: nothing unfavorable to Chinese politics and nothing Taiwan-related (country names are exempt, Taiwan is not). A hit stops the work and goes to the user.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [Kaggle](https://www.kaggle.com/) for running the notebook and checking session state and quota. Carry the exact model name and the exact prompt into the browser task and verify the model name and the session state there.

- [MiniMax H3 Turbo notebook (working copy)](https://www.kaggle.com/code/tanjian2/minimax-h3-turbo-int8-video-audio) for the fused route. The original is [Unlock Bulk's MiniMax H3 Turbo](https://www.kaggle.com/code/unlockbulk/minimax-h3-turbo-int8-video-audio).

- Do NOT use the 2K notebook https://www.kaggle.com/code/umairahmad341/minimax-h3 for reference images. It has no fused.

## Alternatives for better results

- Use headless Kaggle batch runs only after a generation recipe is settled because browser runs stay the tool while parameters are still being tuned.

- Try another seed for a clean frame only when the picture is otherwise right, because a seed change cured blue speckle but seed changes do not cure a wrong character or a wrong action.

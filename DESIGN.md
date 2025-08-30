
## IFPlayer

Runs interactive fiction intepreters and reads/writes stdout/stdin.

Can contain special knowledge/handling of different interpreters or games.

Exposes all output; mainly text but also graphics (and maybe audio for certain games).

Should have minimal dependencies

### Text parsing

* read() returns all output until prompt or key read.

* No support for "interative" games. We assume text/prompt (REPL) loop.

* Try to identify output text. General rules;

- Paragraphs are separated by empty lines.
- Regex for stripping away cruft; logging, copyright strings, title bars

- Can/should we figure out current room name? Probably not

OUTPUT: text & all_text


## Image Generation

Should be done after "look". Right now all text is used to generate image, but only
first long-enough paragraph is used as cache key.
Problem: Can be inconsistent.

Setting;

- auto: Generate on "look"
- manual: Call '#genimg'

- Never show.
- Show if found

- Split screen or overlay

## Image modernisation

- auto: Modernize and cache all images.
- manual `#modern`


## Cache strategy

Build up data per game.




## AIPlayer

Adds AI functionality to the IFPlayer

- Can listen to voice commands and use VoiceToText to feed to the IFPlayer
- Can playback text output with TextToSpeech

Issue: Handles recording internally, but not playback. Inconsistent.
Issue: Uses pix for PNG handling, dependency should be avoided.


## Talkie

The Talkie application. Depends on pix for all graphics.
Shows images, renders text.

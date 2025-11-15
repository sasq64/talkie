# talkie todo

- os_readchar()

- Rules for what constitues parts of text

All text since last prompt
Text that was written in the same "time slice"
Texts with emtpy lines between; paragraphs

PLAYER PROCESS WILL

- Read stdout and deliver text that is "written at the same time" by waiting until
  at least ~0.25 seconds pass with no output.

- Write stdin with incoming full lines (commands) using write_line()

Intepreter is expected to be polling stdin
LINE VS KEY

- Intepreter can send `#[keymode]` to switch to keymode

Now write_key() should be used instead, for every key press



IF "LOGIC" WILL:

- Try to split incoming text printable/speakable parts

- Title/status bar
- Intepreter techincal output
- Prompt character

## REDUCED SCOPE

Caching vs data files

Consider audio only.


## TODO

### Miletone 1 - "Mostly playable"

- □ Image generation: logic; active, auto etc
- □ Image generation: paragraph selection
- □ Image modernisation: Toggle image
- □ Image gen: Extra prompt info to slash command
- □ Store cached images & voice per game in distributable form

- □ Identify game and add game specific prompts and configuration

### Backlog

- □ Better scan lines
- □ Add timeline profiling



## AI CONVERSATION

Input line -> AI

Functions:
 game_command()
 ai_question()


Question -> AI2

  get_transcript()
  find_game()
  start_game()







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



IF "LOGIC" WILL

- Try to split incoming text printable/speakable parts

- Title/status bar
- Intepreter techincal output
- Prompt character



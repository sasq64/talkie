from typing import Final
from .openaiclient import OpenAIClient


class AdventureGuy:

    def __init__(self, prompt: str):
        self.prompt : str= prompt
        self.texts : list[str] = []
        self.score : int = 0
        self.client : Final = OpenAIClient(model="gpt4")
        self.command : str | None = None
        self.question : str | None = None
        #self.client.add_function(self.set_score)
        #self.client.add_function(self.set_verbal_text)
        self.client.add_function(self.set_command)
        self.client.add_function(self.set_ai_question)

    def update(self):
        r = self.client.update()
        return r
        #if len(self.texts) > 0:
        #    return self.texts.pop(0)

    def get_question(self) -> str | None:
        question = self.question
        self.question = None
        return question

    def get_command(self) -> str | None:
        cmd = self.command
        self.command = None
        return cmd

    def set_command(self, command: str):
        """Call this if you detect an explicit command for the interactive fiction interpreter"""
        self.command = command

    def set_ai_question(self, question: str):
        """Call this if you detect a question for the AI"""
        self.question = question

    def set_input(self, text: str, context: str):
        d = { 'text': text, 'context': context }
        self.client.add_line(self.prompt.format(**d))

    def set_output(self, text: str):
        self.client.clear()
        self.client.add_line(f"Here follows the output of an interpreter of interactive fiction (text adventure). Identify the *descriptive* story parts of the text that can be read to the player as audio. Strip out technical information and information about scores and moves. Call 'set_verbal_text' with the result. The output:\n```\n{text}\n```\n")

    def set_score(self, score: int):
        """Set the current score"""
        self.score = score

    def set_verbal_text(self, text: str):
        print(f"VERBAL: {text}")
        self.texts.append(text)
        """
        Set the part of the text that describes the current location or interaction. Should
        not include technical information, logging, or current score and move counters.
        """

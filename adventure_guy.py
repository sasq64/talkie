from openaiclient import OpenAIClient


class AdventureGuy:

    def __init__(self):
        self.texts : list[str] = []
        self.score = 0
        self.client = OpenAIClient(model="gpt4")
        #self.client.add_function(self.set_score)
        self.client.add_function(self.set_verbal_text)

    def update(self):
        r = self.client.update()
        if r:
            print(r.text)
        if len(self.texts) > 0:
            return self.texts.pop(0)
        

    def add_output(self, text):
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
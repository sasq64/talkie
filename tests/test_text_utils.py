import unittest

from talkie.text_utils import parse_adventure_description, parse_text, unwrap_text, partition_text


class TestTextUtils(unittest.TestCase):
    def test_parse_text_basic(self):
        text = "Hello world! Score: 42 Time: 10:30"
        patterns = {"score": r"Score: \d+", "time": r"Time: \d+:\d+"}
        result = parse_text(text, patterns)

        self.assertEqual(result["score"], "Score: 42")
        self.assertEqual(result["time"], "Time: 10:30")
        self.assertEqual(result["text"], "Hello world!")

    def test_parse_text_no_matches(self):
        text = "Just some plain text"
        patterns = {"score": r"Score: \d+", "level": r"Level: \d+"}
        result = parse_text(text, patterns)

        self.assertEqual(result["score"], "")
        self.assertEqual(result["level"], "")
        self.assertEqual(result["text"], "Just some plain text")

    def test_parse_text_partial_matches(self):
        text = "Player health: 100 Location: forest"
        patterns = {
            "health": r"health: \d+",
            "score": r"Score: \d+",
            "location": r"Location: \w+",
        }
        result = parse_text(text, patterns)

        self.assertEqual(result["health"], "health: 100")
        self.assertEqual(result["score"], "")
        self.assertEqual(result["location"], "Location: forest")
        self.assertEqual(result["text"], "Player")

    def test_parse_adventure_description_with_title(self):
        text = (
            "DEADLINE     An Interactive Fiction by Marc Blank\nCopyright 1982 Infocom"
        )
        result = parse_adventure_description(text)

        self.assertEqual(
            result["title"], "DEADLINE     An Interactive Fiction by Marc Blank"
        )
        self.assertEqual(result["copyright"], "Copyright 1982 Infocom")
        self.assertEqual(result["text"], "")

    def test_parse_adventure_description_copyright_only(self):
        text = "Some game description\nCopyright 1985 Game Company\nMore text here"
        result = parse_adventure_description(text)

        self.assertEqual(result["title"], "")
        self.assertEqual(result["copyright"], "Copyright 1985 Game Company")
        self.assertEqual(result["text"], "Some game description\nMore text here")

    def test_parse_adventure_description_no_matches(self):
        text = "Just a regular game description without special formatting"
        result = parse_adventure_description(text)

        self.assertEqual(result["title"], "")
        self.assertEqual(result["copyright"], "")
        self.assertEqual(
            result["text"], "Just a regular game description without special formatting"
        )

    def test_real_game(self):
        text = "Using normal formatting.\nLoading ./deadline.z3.\n South Lawn                                                 Time:  8:00 am\n\nDEADLINE: An INTERLOGIC Mystery\nCopyright 1982 by Infocom, Inc. All rights reserved.\nDEADLINE and INTERLOGIC are trademarks of Infocom, Inc.\nRelease 27 / Serial number 831005\n\nSouth Lawn\nYou are on a wide lawn just north of the entrance to the Robner estate. Directly\nnorth at the end of a pebbled path is the Robner house, flanked to the northeast\nand northwest by a vast expanse of well-kept lawn. Beyond the house can be seen\nthe lakefront.\n\n>"
        result = parse_adventure_description(text)
        # print(result)

        self.assertIn("Time", result["title"])
        self.assertIn("1982", result["copyright"])

        text = """ Foyer                                                                                                                                                                                                              Time:  8:02 am

You hear footsteps inside the house. Mrs. Robner, dressed in black, opens the door and greets you.
"Hello," she says, "I'm Mrs. Robner. Please come in. I'm afraid I really can't help you much. This is surely a terrible waste of time, not to mention upsetting, having all these police marching around the house. This has been a
trying time, as I suppose you can understand. As I told Mr. Coates and the other detective, you may look around but you must be out by 8 o'clock at the latest. Oh, I almost forgot...Mr. Coates will be reading my husband's will at
noon in the living room. You may attend if you wish."
Mrs. Robner leads you into the house and closes the door behind you.
>"""
        result = parse_adventure_description(text)

        unwrapped = unwrap_text(result["text"])
        self.assertEqual(
            unwrapped,
            """You hear footsteps inside the house. Mrs. Robner, dressed in black, opens the door and greets you.
"Hello," she says, "I'm Mrs. Robner. Please come in. I'm afraid I really can't help you much. This is surely a terrible waste of time, not to mention upsetting, having all these police marching around the house. This has been a trying time, as I suppose you can understand. As I told Mr. Coates and the other detective, you may look around but you must be out by 8 o'clock at the latest. Oh, I almost forgot...Mr. Coates will be reading my husband's will at noon in the living room. You may attend if you wish."
Mrs. Robner leads you into the house and closes the door behind you.""",
        )

    def test_partition_text_short_text(self):
        text = "This is a short text."
        result = partition_text(text, 100)
        self.assertEqual(result, ["This is a short text."])

    def test_partition_text_empty_text(self):
        result = partition_text("", 50)
        self.assertEqual(result, [])

    def test_partition_text_split_paragraphs(self):
        text = "First paragraph here.\n\nSecond paragraph.\n\nThird paragraph."
        result = partition_text(text, 30)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "First paragraph here.")
        self.assertEqual(result[1], "Second paragraph.")
        self.assertEqual(result[2], "Third paragraph.")

    def test_partition_text_split_long_paragraphs(self):
        text = "First paragraph here.\n\nSecond paragraph with more content.\n\nThird paragraph."
        result = partition_text(text, 30)
        self.assertEqual(len(result), 4)  # Second paragraph gets split
        self.assertEqual(result[0], "First paragraph here.")
        self.assertTrue("Second paragraph with more" in result[1])
        self.assertEqual(result[3], "Third paragraph.")

    def test_partition_text_split_sentences_with_newline(self):
        text = "This is the first sentence.\nThis is the second sentence.\nThis is the third sentence."
        result = partition_text(text, 35)
        expected = ["This is the first sentence.", "This is the second sentence.", "This is the third sentence."]
        self.assertEqual(result, expected)

    def test_partition_text_split_sentences_any_ending(self):
        text = "Short! Another sentence? And one more. Final sentence here."
        result = partition_text(text, 25)
        self.assertEqual(len(result), 3)
        self.assertTrue(any("Short!" in chunk for chunk in result))
        self.assertTrue(any("Another sentence?" in chunk for chunk in result))

    def test_partition_text_very_long_sentence(self):
        text = "This is an extremely long sentence that cannot be split on any sentence boundary and must be split arbitrarily."
        result = partition_text(text, 20)
        self.assertTrue(len(result) > 1)
        for chunk in result:
            self.assertLessEqual(len(chunk), 20)

    def test_partition_text_complex_mixed(self):
        text = "First paragraph with multiple sentences. This is another sentence.\n\nSecond paragraph.\n\nThird paragraph that is very long and needs to be split because it exceeds the maximum length limit set for this test case."
        result = partition_text(text, 50)
        self.assertTrue(len(result) >= 3)
        for chunk in result:
            self.assertLessEqual(len(chunk), 50)


if __name__ == "__main__":
    unittest.main()

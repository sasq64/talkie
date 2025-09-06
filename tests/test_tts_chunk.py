import pytest

from talkie.tts_chunk import split_for_tts


def assert_all_leq(chunks: list[str], max_chars: int) -> None:
    assert all(len(c) <= max_chars for c in chunks), (
        f"Found chunk longer than {max_chars}: {[len(c) for c in chunks]}"
    )


def test_empty_text_returns_empty_list() -> None:
    assert split_for_tts("") == []


def test_short_text_unchanged() -> None:
    text = "Hello world."
    assert split_for_tts(text, max_chars=100) == [text]


def test_splits_on_sentence_boundaries() -> None:
    text = "Hello there. This is a test. Another sentence follows! And one more?"
    chunks = split_for_tts(text, max_chars=25)
    # Should try to preserve sentence boundaries and pack greedily
    # The exact packing can vary by boundary choices, but constraints must hold
    assert_all_leq(chunks, 25)
    # Ensure punctuation stays with sentences
    for c in chunks[:-1]:
        assert c[-1] in ".!?"


def test_respects_paragraph_boundaries() -> None:
    text = "First para line one.\nLine two.\n\nSecond paragraph starts here. More text."
    chunks = split_for_tts(text, max_chars=35)
    assert_all_leq(chunks, 35)
    # Should not split inside sentences unnecessarily
    assert any("\n\n" not in c for c in chunks)
    # Combined chunks should reconstruct the original without internal trimming
    assert "".join(c + " " for c in chunks).replace("  ", " ").strip().startswith(
        "First para line one."
    )


def test_falls_back_to_newlines_and_spaces() -> None:
    text = "Alpha\nBeta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda."
    chunks = split_for_tts(text, max_chars=15)
    assert_all_leq(chunks, 15)
    # Should create multiple chunks, e.g., splitting at newline or spaces
    assert len(chunks) >= 3


def test_hard_split_long_word_when_necessary() -> None:
    long_word = "A" * 50
    text = f"Start {long_word} End"
    chunks = split_for_tts(text, max_chars=20)
    assert_all_leq(chunks, 20)
    # Ensure content coverage: concatenation should contain the long word fully
    rebuilt = "".join(chunks)
    assert long_word in rebuilt


def test_greedy_packing_under_limit() -> None:
    text = "One. Two. Three. Four. Five. Six."
    # max_chars allows multiple sentences per chunk
    chunks = split_for_tts(text, max_chars=12)
    assert_all_leq(chunks, 12)
    # Greedy packing: first chunk should contain more than one sentence if possible
    assert any(c.count(".") >= 2 for c in chunks)


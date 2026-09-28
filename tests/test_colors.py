import numpy as np

from scanner.colors import ColorClassifier, bgr_to_lab, ciede2000


def test_identical_lab_is_zero():
    lab = bgr_to_lab((40, 40, 200))
    assert ciede2000(lab, lab) == 0


def test_classifier_separates_default_stickers():
    classifier = ColorClassifier()
    names = ["white", "yellow", "red", "orange", "blue", "green"]
    for name in names:
        guessed, delta = classifier.classify_lab(classifier.references[name])
        assert guessed == name
        assert delta < 1e-6


def test_warm_white_is_white():
    classifier = ColorClassifier()
    name, _ = classifier.classify_lab(bgr_to_lab((210, 225, 235)))
    assert name == "white"


def test_saturated_red_is_not_called_orange():
    # A learned red sample can drift dull while orange stays saturated.
    # Bright sticker red must still come back as red.
    classifier = ColorClassifier({
        "white": np.array([72.0, -1.0, -6.0]),
        "yellow": np.array([75.0, -9.0, 67.0]),
        "red": np.array([51.0, 27.0, 26.0]),
        "orange": np.array([59.0, 58.0, 57.0]),
        "blue": np.array([26.0, 9.0, 7.0]),
        "green": np.array([61.0, -59.0, 45.0]),
    })
    name, _ = classifier.classify_lab(np.array([53.7, 69.0, 54.0]))
    assert name == "red"


def test_nearby_red_still_red():
    classifier = ColorClassifier()
    lab = bgr_to_lab((50, 45, 170))
    name, delta = classifier.classify_lab(lab)
    assert name == "red"
    assert delta < 20

from localditado import postprocess as pp


def test_voice_command_comma_and_period():
    out = pp.process("olá vírgula tudo bem ponto final", voice_commands=True, capitalize=True)
    assert out == "Olá, tudo bem."


def test_voice_command_newline_and_paragraph():
    out = pp.process(
        "linha um nova linha linha dois novo parágrafo fim",
        voice_commands=True,
        capitalize=True,
    )
    assert out == "Linha um\nLinha dois\n\nFim"


def test_dictionary_is_case_insensitive_word_boundary():
    out = pp.process("meu nome é maicon", dictionary={"maicon": "Maycon"}, capitalize=False, voice_commands=False)
    assert out == "meu nome é Maycon"


def test_dictionary_does_not_match_substring():
    out = pp.process("descomplicado", dictionary={"compli": "X"}, capitalize=False, voice_commands=False)
    assert out == "descomplicado"


def test_capitalize_after_sentence():
    out = pp.process("isso é teste. outro caso!", voice_commands=False, capitalize=True)
    assert out == "Isso é teste. Outro caso!"


def test_no_space_before_punctuation():
    out = pp.fix_spacing("palavra ,  outra .")
    assert out == "palavra, outra."


def test_empty_input():
    assert pp.process("", voice_commands=True, capitalize=True) == ""


def test_disabled_voice_commands_keep_words():
    out = pp.process("a vírgula b", voice_commands=False, capitalize=False)
    assert "vírgula" in out

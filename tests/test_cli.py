def test_unknown_command_suggests_similar_command(workdir, run):
    result = run("comit", "-m", "x")
    assert result.code == 1
    assert result.out == ""
    assert result.err == (
        "minigit: 'comit' is not a minigit command. See 'minigit --help'.\n"
        "The most similar command is\n"
        "    commit\n"
    )


def test_unknown_command_no_similar(workdir, run):
    result = run("abxsfvg")
    assert result.code == 1
    assert result.out == ""
    assert result.err == ("minigit: 'abxsfvg' is not a minigit command. See 'minigit --help'.\n")


def test_valid_command(workdir, run):
    result = run("init")
    assert result.code == 0
    assert result.err == ""

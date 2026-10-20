import pytest
from minigit.cli import main

# Added capsys.readouterr() after every main(["init"]) call to flush the initialization message before testing with actual commands

def test_symbolic_ref_read(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    assert main(["symbolic-ref", "HEAD"]) == 0
    out, _ = capsys.readouterr()
    assert out.strip() == "refs/heads/main"

def test_symbolic_ref_short(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    assert main(["symbolic-ref", "--short", "HEAD"]) == 0
    out, _ = capsys.readouterr()
    assert out.strip() == "main"

def test_symbolic_ref_detached(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    (tmp_path / ".minigit" / "HEAD").write_text("1234567890123456789012345678901234567890\n")
    
    assert main(["symbolic-ref", "HEAD"]) == 128
    _, err = capsys.readouterr()
    assert "fatal: ref HEAD is not a symbolic ref" in err

def test_symbolic_ref_update(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    assert main(["symbolic-ref", "HEAD", "refs/heads/dev"]) == 0
    
    assert main(["symbolic-ref", "HEAD"]) == 0
    out, _ = capsys.readouterr()
    assert out.strip() == "refs/heads/dev"

def test_symbolic_ref_update_invalid(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    assert main(["symbolic-ref", "HEAD", "invalid-branch"]) == 128
    _, err = capsys.readouterr()
    assert "fatal: only accepts refs starting with refs/" in err
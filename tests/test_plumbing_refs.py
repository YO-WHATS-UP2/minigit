import pytest
from minigit.cli import main

# Added capsys.readouterr() after every main(["init"]) call to flush the initialization message before testing with actual commands
# I also automated the whole process for setting up a /tmp directory to test it out
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

def test_update_ref_standard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    
    # Create a fake commit so HEAD resolves successfully
    (tmp_path / ".minigit" / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    fake_sha = "1234567890123456789012345678901234567890"
    (tmp_path / ".minigit" / "refs" / "heads" / "main").write_text(f"{fake_sha}\n")
    
    # Test standard update
    assert main(["update-ref", "refs/heads/testbranch", "HEAD"]) == 0
    assert (tmp_path / ".minigit" / "refs" / "heads" / "testbranch").read_text().strip() == fake_sha

def test_update_ref_delete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    
    # Create a ref to delete
    (tmp_path / ".minigit" / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    target = tmp_path / ".minigit" / "refs" / "heads" / "todelete"
    target.write_text("1234567890123456789012345678901234567890\n")
    
    # Test deletion flag
    assert main(["update-ref", "-d", "refs/heads/todelete"]) == 0
    assert not target.exists()

def test_update_ref_safety_check(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    # Create a fake commit so HEAD resolves successfully (Fixes the error)
    (tmp_path / ".minigit" / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    fake_sha = "1234567890123456789012345678901234567890"
    (tmp_path / ".minigit" / "refs" / "heads" / "main").write_text(f"{fake_sha}\n")
    
    # Setup the locked ref
    target = tmp_path / ".minigit" / "refs" / "heads" / "locked"
    target.write_text("1111111111111111111111111111111111111111\n")
    
    # Test that updating fails when the current SHA doesn't match old-value
    assert main(["update-ref", "refs/heads/locked", "HEAD", "2222222222222222222222222222222222222222"]) == 128
    _, err = capsys.readouterr()
    assert "cannot lock ref" in err

def test_update_ref_missing_value(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr() # Flush init output
    
    # Test that running without -d requires a newvalue
    assert main(["update-ref", "refs/heads/testbranch"]) == 128
    _, err = capsys.readouterr()
    assert "fatal: update-ref requires a newvalue unless -d is used" in err    
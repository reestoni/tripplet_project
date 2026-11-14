"""db/user_avatar.py (profile picture, shared with the web app) + the desktop settings dialog / footer."""
import io
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from db import user_avatar  # noqa: E402

UID = 987654321   # no real user


def _png(w, h, colour=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def tmp_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIPPLET_DIR_USER_AVATARS", str(tmp_path / "avatars"))
    yield tmp_path / "avatars"


def test_normalise_square_png():
    out = user_avatar.normalise(_png(800, 400))
    im = Image.open(io.BytesIO(out))
    assert im.format == "PNG" and im.size == (user_avatar.SIZE, user_avatar.SIZE)


def test_rejects():
    with pytest.raises(user_avatar.AvatarError) as e:
        user_avatar.normalise(b"not a picture")
    assert e.value.code == "not_image"
    with pytest.raises(user_avatar.AvatarError) as e:
        user_avatar.normalise(_png(10, 10))
    assert e.value.code == "too_small"
    with pytest.raises(user_avatar.AvatarError) as e:
        user_avatar.normalise(b"x" * (user_avatar.MAX_UPLOAD_BYTES + 1))
    assert e.value.code == "too_big"


def test_save_load_delete(tmp_folder):
    assert not user_avatar.has_avatar(UID) and user_avatar.version(UID) == 0
    path = user_avatar.save(UID, _png(300, 300))
    assert path.startswith(str(tmp_folder)) and user_avatar.has_avatar(UID) and user_avatar.version(UID) > 0
    assert user_avatar.load_bytes(UID)[:8] == b"\x89PNG\r\n\x1a\n"
    assert user_avatar.delete(UID) and not user_avatar.has_avatar(UID)
    assert not user_avatar.delete(UID)


def test_dialog_and_footer(tmp_folder, monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import app_meta
    monkeypatch.setattr(app_meta, "current_user", {"id": UID, "first_name": "Test", "last_name": "User"}, raising=False)
    from ui.widgets.user_settings_dialog import UserSettingsDialog
    from ui.widgets.footer import FooterBar
    dlg = UserSettingsDialog()
    assert dlg.lbl_avatar.text() == "TU" and not dlg.btn_pic_remove.isEnabled()
    dlg._avatar_new = user_avatar.normalise(_png(200, 200))
    dlg._show_avatar()
    assert dlg.lbl_avatar.pixmap() is not None and not dlg.lbl_avatar.pixmap().isNull()
    dlg._save_avatar()
    assert user_avatar.has_avatar(UID)
    foot = FooterBar()
    assert foot.user_icon.width() == 18
    dlg2 = UserSettingsDialog()
    dlg2._remove_avatar()
    dlg2._save_avatar()
    assert not user_avatar.has_avatar(UID)
    dlg.reject()
    dlg2.reject()

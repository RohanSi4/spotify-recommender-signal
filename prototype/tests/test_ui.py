from streamlit.testing.v1 import AppTest


def test_credential_free_demo_ranks_tracks() -> None:
    app = AppTest.from_file("gui_streamlit.py", default_timeout=10).run()
    assert not app.exception
    assert app.radio[0].value == "Demo catalog"
    assert app.metric[0].value == "72"

    app.button[0].click().run()

    assert not app.exception
    result_cards = [item.value for item in app.markdown if "FEATURE SIM" in item.value]
    assert len(result_cards) == 10
    assert "Afterglow Avenue 07" in result_cards[0]

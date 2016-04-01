import pytest
import test
import bluetooth.profiles

test.setup()

def test_Hfp_constructor_works():
  with bluetooth.profiles.HandsFree() as hfp:
    pass

def test_Hfp_starts_and_stops():
  with bluetooth.profiles.HandsFree() as hfp:
    hfp.start()
    hfp.stop()
    # with pytest.raises(Exception):

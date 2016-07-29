import pytest
import test
import handset.bluetooth.profiles

test.setup()

def test_Hfp_constructor_works():
  with handset.bluetooth.profiles.HandsFree() as hfp:
    pass

def test_Hfp_starts_and_stops():
  with handset.bluetooth.profiles.HandsFree() as hfp:
    hfp.start()
    hfp.stop()
    # with pytest.raises(Exception):

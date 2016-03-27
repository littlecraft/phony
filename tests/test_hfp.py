import pytest
import test
from handset.hfp import Hfp

test.setup()

def test_Hfp_constructor_works():
  with Hfp() as hfp:
    pass

def test_Hfp_starts_and_stops():
  with Hfp() as hfp:
    hfp.start()
    hfp.stop()
    # with pytest.raises(Exception):

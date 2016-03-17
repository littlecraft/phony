import pytest
import env
from src.Hfp import Hfp

def test_Hfp_constructor_works():
  hfp = Hfp(env.log)

def test_Hfp_starts_and_stops():
  hfp = Hfp(env.log)
  hfp.start()
  hfp.stop()
  # swith pytest.raises(Exception):

def test_Hfp_listens_to_hfpd():
  pass
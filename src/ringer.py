import threading
import time

from phony.base.log import ClassLogger

class Njm2670HbridgeRinger(ClassLogger):
  RING_FREQUENCY_HZ = 20
  RING_DURATION_SEC = 2.0
  PAUSE_DURATION_SEC = 2.0

  _outputs = None
  _polarity = 0

  _stop = None
  _thread = None

  def __init__(self, io_outputs):
    ClassLogger.__init__(self)

    self._stop = threading.Event()

    self._outputs = io_outputs
    # De-energize hbridge
    self._outputs.ringer_enable(0)
    self._outputs.ringer_1(0)
    self._outputs.ringer_2(0)

  @ClassLogger.TraceAs.event()
  def start_ringing(self):
    if self._thread:
      raise Exception('Ringing already started')

    self._thread = threading.Thread(target = self.run)
    self._thread.start()

  @ClassLogger.TraceAs.call()
  def stop_ringing(self):
    if self._thread:
      self._stop.set()
      self._thread.join()
      self._stop.clear()

      self._thread = None

  def run(self):
    ring_period_sec = 1.0 / self.RING_FREQUENCY_HZ

    self._ringer_enable(1)

    while self._is_running():

      time_to_stop = time.time() + self.RING_DURATION_SEC
      while self._is_running() and time.time() < time_to_stop:
        self._ding()
        time.sleep(ring_period_sec)

      self._sleep_or_exit(self.PAUSE_DURATION_SEC)

    self._ringer_enable(0)

  def _ringer_enable(self, value):
    self._outputs.ringer_enable(value)

  def _ding(self):
    self._outputs.ringer_1(self._polarity)
    self._polarity = not self._polarity
    self._outputs.ringer_2(self._polarity)

  def _sleep_or_exit(self, seconds):
    time_to_stop = time.time() + seconds
    while self._is_running() and time.time() < time_to_stop:
      time.sleep(0.001)

  def _is_running(self):
    return not self._stop.is_set()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop_ringing()
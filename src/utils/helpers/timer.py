import time


class Timer:
    """
    A simple timer class to measure the elapsed time of code execution.
    """

    def __init__(self):
        self.start_time = None

    def start(self):
        """
        Start the timer.
        """
        self.start_time = time.time()

    def stop(self) -> float:
        """
        Stop the timer and return the elapsed time in seconds.
        """
        if self.start_time is None:
            raise ValueError("Timer has not been started.")
        elapsed_time = time.time() - self.start_time
        self.start_time = None
        return elapsed_time

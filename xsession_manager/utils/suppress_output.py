import os
from contextlib import contextmanager


class SuppressOutput:

    suppress_stdout: bool
    suppress_stderr: bool

    def __init__(self, suppress_stdout=False, suppress_stderr=False):
        self.suppress_stdout = suppress_stdout
        self.suppress_stderr = suppress_stderr

    @contextmanager
    def suppress_output(self):
        if self.suppress_stdout is False and self.suppress_stderr is False:
            # Do not suppress any kind of output
            yield
            return

        savefd_stdout = None
        savefd_stderr = None
        fd = os.open('/dev/null', os.O_WRONLY)

        if self.suppress_stderr:
            # Save the original file descriptors
            savefd_stderr = os.dup(2)
            # Suppress stderr
            os.dup2(fd, 2)
        if self.suppress_stdout:
            # Save the original file descriptors
            savefd_stdout = os.dup(1)
            # Suppress stdput
            os.dup2(fd, 1)

        # Close the file descriptor to avoid leaking file descriptors
        os.close(fd)

        yield

        # Restore stdput and stderr
        if savefd_stderr:
            os.dup2(savefd_stderr, 2)
            # Close the saved file descriptor to avoid leaking file descriptors
            os.close(savefd_stderr)
        if savefd_stdout:
            os.dup2(savefd_stdout, 1)
            # Close the saved file descriptor to avoid leaking file descriptors
            os.close(savefd_stdout)





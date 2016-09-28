
class BobTheBuilderException(Exception):
    def __init__(self, message):
        super(BobTheBuilderException, self).__init__(message)
        self.message = message


class BobProcessExecutionError(BobTheBuilderException):
    def __init__(self, message, cmd, returncode, details):
        super(BobProcessExecutionError, self).__init__(message)
        self.message = message
        self.cmd = cmd
        self.returncode = returncode
        self.details = details

    def __repr__(self):
        return '{0}\ncmd:{1}\nreturncode:{2}'.format(self.message, self.cmd, self.returncode)


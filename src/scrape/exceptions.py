""" Exceptions unique to the scraping process. """


class DoneScraping(Exception):
    """ Raised when all scraping is done. """


class NothingToDo(Exception):
    """ Raised upon discovering the output file is already complete. """


class RequestFailed(Exception):
    """ Raised when an HTTP request to the hiscores API fails. """

    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)


class UserNotFound(Exception):
    """ Raised when data for a requested username does not exist. """


class ServerBusy(Exception):
    """ Raised when the CSV API is too busy to process a stats request. """

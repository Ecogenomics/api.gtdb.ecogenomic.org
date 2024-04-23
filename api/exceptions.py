from fastapi import HTTPException


class HttpBaseException(HTTPException):

    def __init__(self, status_code, detail):
        super().__init__(status_code=status_code, detail=detail)


class HttpBadRequest(HttpBaseException):
    status_code = 400

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)


class HttpNotFound(HttpBaseException):
    status_code = 404

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)


class HttpInternalServerError(HttpBaseException):
    status_code = 500

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)

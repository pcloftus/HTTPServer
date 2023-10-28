import os

import parsers

class Handlers():

    def __init__(self):
        self.handlers_dict = {
            "get": self.handle_GET,
            "post": self.handle_POST,
            "size error": self.handle_431,
        }

        self.headers = {
            'Server': 'BasicServer' ,
            'Content-Type': 'text/html',
        }

        self.status_codes = {
            200: 'OK',
            201: 'Created',
            404: 'Not Found',
            431: 'Request Header Fields Too Large',
            501: 'Not Implemented',
        }

    def update_constants(self, headers, status_codes):
        self.headers = headers
        self.status_codes = status_codes

    def router(self, method_name):
        method_name = method_name.lower()

        if method_name not in self.handlers_dict:
            return self.handle_501
        else:
            return self.handlers_dict[method_name]

    def handle_431(self):
        response_line = self.response_line(status_code=431)
        response_headers = self.response_headers()
        blank_line = b"\r\n"
        response_body = b"<h1>431 Request Header Fields Too Large</h1>"

        return b"".join([response_line, response_headers, blank_line, response_body])

    def handle_501(self):
        response_line = self.response_line(status_code=501)
        response_headers = self.response_headers()
        blank_line = b"\r\n"
        response_body = b"<h1>501 Not Implemented</h1>"

        return b"".join([response_line, response_headers, blank_line, response_body])

    def handle_GET(self, request):
        filename = request.uri.strip('/')

        if filename == "":
            filename = "index.html"

        if os.path.exists(filename):
            response_line = self.response_line(status_code=200)

            file_extension = filename.split('.')[1]
            content_type = parsers.parse_filetype(file_extension)
            extra_headers = {"Content-Type": content_type}

            response_headers = self.response_headers(extra_headers)

            with open(filename, 'rb') as f:
                response_body = f.read()
        else:
            response_line = self.response_line(status_code=404)
            response_headers = self.response_headers()
            response_body = b"<h1>404 Not Found</h1>"
        
        blank_line = b"\r\n"

        return b"".join([response_line, response_headers, blank_line, response_body])

    def handle_POST(self, request):
        if b'content-type' not in request.headers:
            raise RuntimeError("Invalid POST request")

        status = 200

        filename = request.uri.strip('/')
        if filename == "":
            raise RuntimeError("Invalid filename for POST")

        if request.headers[b'content-type'] == b'application/x-www-form-urlencoded':
            body = parsers.parse_form_body(request.body)
            if not os.path.exists(filename):
                status = 201
            with open(filename, 'a') as f:
                f.write(str(body))
        elif b'multipart/form-data' in request.headers[b'content-type']:
            multipart_dict = parsers.parse_multipart_body(request.body, request.headers[b'content-type'])
            for key, value in multipart_dict.items():
                multipart_filename = value[b"Headers"][b"Content-Disposition"][b"filename"]
                with open(multipart_filename, 'ab') as f:
                    f.write(value[b"Content"])
        else:
            body = request.body

        response_line = self.response_line(status_code=status)
        response_headers = self.response_headers() 
        blank_line = b"\r\n"

        return b"".join([response_line, response_headers, blank_line, blank_line])

    def response_line(self, status_code):
        reason = self.status_codes[status_code]
        line = "HTTP/1.1 %s %s\r\n" % (status_code, reason)

        return line.encode()

    def response_headers(self, extra_headers=None):
        headers_copy = self.headers.copy()

        if extra_headers:
            headers_copy.update(extra_headers)

        result_headers = ""

        for h in headers_copy:
            result_headers += "%s: %s\r\n" % (h, headers_copy[h])

        return result_headers.encode()
 
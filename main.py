import os
import socket

from ServerSocket import ServerSocket

class ServerBase:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.size_error = False

    def start_server(self):
        self.size_error = False
        serv = ServerSocket()

        serv.start()

        while True:
            (conn, addr) = serv.sock.accept()
            print("Connected by ", addr)

            serv_client = ServerSocket(conn)

            data = serv_client.initial_recv()

            if not serv_client.split_list:
                self.size_error = True
            else:
                if len(serv_client.split_list) < 2:
                    raise RuntimeError("Error parsing headers from bodies received from Socket")

                HTTP_data = HTTPRequest(data)

                if b'content-length' in HTTP_data.headers:
                    print("\nCONTENT LENGTH:\n", HTTP_data.headers[b'content-length'])
                    if int(HTTP_data.headers[b'content-length']) >= len(serv_client.split_list[1]):
                        MSGLEN = int(HTTP_data.headers[b'content-length']) - len(serv_client.split_list[1])
                    else:
                        MSGLEN = serv_client.chunk_size
                else:
                    MSGLEN = serv_client.chunk_size

                print("\nMSGLEN:\n", MSGLEN)

                if MSGLEN > serv_client.chunk_size:
                    data = data + serv_client.chunked_recv(MSGLEN)
                    
            response = self.handle_request(data)

            serv_client.chunked_send(response, len(response))

            serv_client.sock.close()

        def handle_request(self, data):
            return data

class HTTPServer(ServerBase):
    headers = {
        'Server': 'BasicServer' ,
        'Content-Type': 'text/html',
    }

    status_codes = {
        200: 'OK',
        201: 'Created',
        404: 'Not Found',
        431: 'Request Header Fields Too Large',
        501: 'Not Implemented',
    }

    def handle_request(self, data):
        request = HTTPRequest(data)

        if self.size_error:
            handler = self.HTTP_431_handler
        elif request.method == "GET":
            handler = self.handle_GET
        elif request.method == "POST":
            handler = self.handle_POST
        else:
            handler = self.HTTP_501_handler

        response = handler(request)

        return response

    def HTTP_431_handler(self, request):
        response_line = self.response_line(status_code=431)
        response_headers = self.response_headers()
        blank_line = b"\r\n"
        response_body = b"<h1>431 Request Header Fields Too Large</h1>"

        return b"".join([response_line, response_headers, blank_line, response_body])

    def HTTP_501_handler(self, request):
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
            content_type = self.parse_filetype(file_extension)
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
            body = self.parse_form_body(request.body)
            if not os.path.exists(filename):
                status = 201
            with open(filename, 'a') as f:
                f.write(str(body))
        elif b'multipart/form-data' in request.headers[b'content-type']:
            multipart_dict = self.parse_multipart_body(request.body, request.headers[b'content-type'])
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

    def parse_form_body(self, body):
        kv_string = body.split(b"&")
        body_dict = {}
        for pairs in kv_string:
            key_value = pairs.split(b"=", 1)
            body_dict[key_value[0]] = key_value[1]

        return body_dict

    def parse_multipart_body(self, body, content_type):
        result_dict = {}

        content_list = content_type.split(b";")
        if len(content_list) > 1:
            boundary_list = content_list[1].split(b"=")
            if len(boundary_list) > 1:
                boundary_text = b"--" + boundary_list[1].strip()

        split_body = body.split(boundary_text)

        if len(split_body) < 1:
            raise RuntimeError("Error parsing multipart (split_body1)")

        split_body = split_body[1:-1]

        print("\nSPLIT_BODY\n", split_body)

        for i in range(len(split_body)):
            split_part = split_body[i].split(b"\r\n\r\n")

            if len(split_part) < 1:
                raise RuntimeError("Error parsing multipart (split_part1)")

            result_dict[b"Multipart " + bytes(i)] = {}
            result_dict[b"Multipart " + bytes(i)][b"Headers"] = {}

            print("\nSPLIT PART 0\n", split_part[0])
            part_headers = split_part[0].split(b"\r\n")[1:]
            for header in part_headers:
                split_header = header.split(b": ")
                if len(split_header) < 2:
                    print("\nSPLIT HEADER\n", split_header)
                    raise RuntimeError("Error parsing individual part headers")

                if split_header[0].lower() == b'content-disposition':
                    result_dict[b"Multipart " + bytes(i)][b"Headers"][split_header[0]] = {}
                    dispositions = split_header[1].split(b"; ")
                    for disposition in dispositions:
                        disp_pair = disposition.split(b"=", 1)
                        if len(disp_pair) > 1:
                            result_dict[b"Multipart " + bytes(i)][b"Headers"][split_header[0]][disp_pair[0]] = disp_pair[1].strip(b'"')
                        else:
                            result_dict[b"Multipart " + bytes(i)][b"Headers"][split_header[0]][disp_pair[0]] = disp_pair[0]
                else:
                    result_dict[b"Multipart " + bytes(i)][b"Headers"][split_header[0]] = split_header[1]

            result_dict[b"Multipart " + bytes(i)][b"Content"] = split_part[1]

        return result_dict

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

    def parse_filetype(self, extension):
        extension_map = {
            'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'jfif': 'image/jpeg',
            'jfif': 'image/jpeg', 'pjpeg': 'image/jpeg', 'pjp': 'image/jpeg',
            'png': 'image/png',
            'ogg': 'audio/ogg',
            'mpeg': 'audio/mpeg',
            'pdf': 'application/pdf',
            'css': 'text/css',
            'html': 'text/html',
            'js': 'text/javascript',
        }

        return extension_map[extension]

class HTTPRequest:
    def __init__(self, data):
        self.method = None
        self.uri = None
        self.http_version = "1.1"
        self.body = None
        self.headers = None

        self.parse(data)

    def parse(self, data):
        header_body_split = data.split(b"\r\n\r\n", 1)

        if len(header_body_split) < 2:
            raise RuntimeError("Critical error parsing request")
        self.body = header_body_split[1]

        lines = header_body_split[0].split(b"\r\n")
        request_line = lines[0]
        words = request_line.split(b" ")

        self.method = words[0].decode()
        if len(words) > 1:
            self.uri = words[1].decode()
        if len(words) > 2:
            self.http_version = words[2]

        if len(lines) < 1:
            raise RuntimeError("Invalid request received (lines1)")

        headers_list = lines[1:]
        self.headers = self.parse_headers(headers_list)

    def parse_headers(self, headers_list):
        headers_dict = {}
        for i in headers_list:
            header = i.split(b': ', 1)
            headers_dict[header[0].lower()] = header[1]
        return headers_dict

if __name__ == '__main__':
    server = HTTPServer()
    server.start_server()
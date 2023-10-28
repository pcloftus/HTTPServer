from server_socket import ServerSocket
from handlers import Handlers

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
                    if int(HTTP_data.headers[b'content-length']) >= len(serv_client.split_list[1]):
                        MSGLEN = int(HTTP_data.headers[b'content-length']) - len(serv_client.split_list[1])
                    else:
                        MSGLEN = serv_client.chunk_size
                else:
                    MSGLEN = serv_client.chunk_size

                if MSGLEN > serv_client.chunk_size:
                    data = data + serv_client.chunked_recv(MSGLEN)
                    
            response = self.handle_request(data)

            serv_client.chunked_send(response, len(response))

            serv_client.sock.close()

        def handle_request(self, data):
            print("Default handle_request method called")
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

    def __init__(self):
        self.handlers = Handlers()        
        self.handlers.update_constants(self.headers, self.status_codes)

    def handle_request(self, data):
        request = HTTPRequest(data)

        if self.size_error:
            handler = self.handlers.router("size error")
        else:
            handler = self.handlers.router(request.method)

        response = handler(request)

        return response

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
from server_socket import ServerSocket
from handlers import Handlers

class ServerBase:
    """
    Class representing the basic server socket functionality

    Handles the main loop where the socket accepts connections, 
    receives, and sends data. Relies on HTTPRequest class to 
    perform basic parsing to determine if content-length is 
    present in order to chunk socket.recv() - otherwise sends 
    and receives based on a chunk size defined in ServerSocket.

    Attributes
    ----------
    host : str
        Host IP
    port : int
    size_error : bool
        Flag for representing if the headers are too long to receive
        in one socket.recv() call and do not include content-length
    
    Methods
    ----------
    start_server()
        Starts the ServerSocket and loops through accepting connections, 
        receiving data, triggering handling, and sending responses

    handle_request(data)
        Backup method for handling data that simply echos - intended to be 
        overridden by a more specific Server class (HTTPServer)
    """
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.size_error = False

    def start_server(self):
        """
        Set up ServerSocket and main loop for server

        Uses the custom ServerSocket which mostly wraps python socket module. 
        Performs basic parsing via an HTTPRequest object, and thus assumes 
        the data being received is HTTP, in order to get content-length and 
        set the parameters (`chunk_size` or `MSGLEN`) for the socket send() 
        and recv(). Returns nothing and closes the socket when all data is 
        sent.
        """
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
    """
    Subclass of ServerBase that represents HTTP functionality

    Contains basic headers and supported status codes, and functionality 
    for routing requests via the Handlers class.

    Attributes
    ----------
    headers : dict (str : str)
        Contains the basic HTTP headers sent with all responses unless 
        overwritten
    status_codes : dict (int : str)
        Contains mappings of currently support status codes and the 
        messages that accompany them

    Methods 
    ----------
    handle_request(data)
        Creates a new HTTPRequest object with passed byte data, and 
        uses the Handlers object set up in __init__() to route the 
        request method to the correct handling function
    """
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
        """
        Initial setup for the HTTP server

        Associates a Handlers object to the HTTP server for handling 
        all requests, and also updates that Handlers object's headers 
        and status codes so that any updates to those fields can be 
        made from this class.
        """
        self.handlers = Handlers()        
        self.handlers.update_constants(self.headers, self.status_codes)

    def handle_request(self, data):
        """
        First stop for handling HTTP requests

        Passes the bytes in `data` to an HTTPRequest object and uses 
        parsed fields from that object to pass to the router() 
        method of the Handlers object set up in __init__()

        Parameters
        ----------
        data : bytes
            Raw request bytes passed straight from the socket in ServerBase

        Returns
        ----------
        response : bytes
            A full HTTP response string represented as bytes
        """
        request = HTTPRequest(data)

        if self.size_error:
            handler = self.handlers.router("size error")
        else:
            handler = self.handlers.router(request.method)

        response = handler(request)

        return response

class HTTPRequest:
    """
    A representation of an individual HTTP request

    Attributes and methods related to parsing and storing 
    HTTP request data

    Attibutes
    ---------
    method : str
        The parsed out HTTP method, default is None
    uri : str
        The path to the server resource, default is None
    http_version : str
        Default is 1.1
    body : bytes
        The entire body of the HTTP request, default is None
    headers : dict (bytes : bytes)
        A dictionary of headers and their values - left as bytes 
        but represented internally as strings

    Methods
    ---------
    parse(data)
        Takes the bytes representing the initial data received by a
        socket and parses out the various HTTP fields
    parse_headers(headers_list)
        Takes the overall bytes of the headers portion (between the 
        first line and the body), and parses them to dict
    """
    def __init__(self, data):
        """
        Setup for an individual HTTP request object

        Declares various fields related to the HTTP request, but also 
        calls the parse() method for each HTTPRequest created
        """
        self.method = None
        self.uri = None
        self.http_version = "1.1"
        self.body = None
        self.headers = None

        self.parse(data)

    def parse(self, data):
        """
        Parses byte data representing an HTTP request into fields

        Relies on the use of CRLF in HTTP requests to parse each 
        individual portion of the request. Assumes the data it 
        is passed is an HTTP request - otherwise raises 
        RuntimeErrors in parsing

        Parameters
        ----------
        data : bytes
            Raw bytes of the request, represented internally as 
            strings that are either decoded/encoded or used with 
            the "b" prefix
        """
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
        """
        Helper function to specifically parse HTTP header fields

        Parameters
        ----------
        headers_list : list (bytes)
            A list of each individual "Header: Content" combination. 
            Parses these into a dictionary of key-values for each 
            combination
        """
        headers_dict = {}
        for i in headers_list:
            header = i.split(b': ', 1)
            headers_dict[header[0].lower()] = header[1]
        return headers_dict

if __name__ == '__main__':
    server = HTTPServer()
    server.start_server()
import socket

class ServerSocket:
    def __init__(self, sock=None):
        self.chunk_size = 4096 
        self.split_list = None
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:
            self.sock = sock

    def start(self, host='127.0.0.1', port=8888):
        self.sock.bind((host, port))
        self.sock.listen(5)

        print("Listening at: ", self.sock.getsockname())

    def initial_recv(self):
        self.split_list = None
        data = self.sock.recv(self.chunk_size)
        
        if b"\r\n\r\n" in data:
            self.split_list = data.split(b"\r\n\r\n", 1)

        return data

    def chunked_recv(self, MSGLEN):
        chunks = []
        bytes_recvd = 0
        while bytes_recvd < MSGLEN:
            chunk = self.sock.recv(min(MSGLEN - bytes_recvd, self.chunk_size))
            if chunk == b"":
                raise RuntimeError("Socket connection broken (receive)")
            chunks.append(chunk)
            bytes_recvd = bytes_recvd + len(chunk)

        return b"".join(chunks)

    def chunked_send(self, msg, MSGLEN):
        totalsent = 0
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken (send)")
            totalsent = totalsent + sent

    def my_accept(self):
        self.sock.accept()
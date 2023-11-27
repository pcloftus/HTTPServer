# HTTPServer
**HTTP server with HTTPS and other standard HTTP security features**

*Patrick Loftus*

## Functionality
- Uses Python sockets library and SSL, otherwise fully manual implementation
  - Uses chunked sending/receiving based on content-length
  - If no content length but content exceeds default chunk size server returns a 431
  - Otherwise uses one default chunk size to send and receive - within network buffer size
- Manual parsing and composition of requests and responses, supporting:
  - GET
  - POST
  - 200
  - 201
  - 404
  - 431
  - 501
- Uses a self-signed certificate (not included in this repo) to enable HTTPS
  - As well as wrapping sockets to facilitate encryption
- Additionally supports CSP and CORS, and forces HTTPS via HSTS

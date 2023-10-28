def parse_form_body(body):
    kv_string = body.split(b"&")
    body_dict = {}
    for pairs in kv_string:
        key_value = pairs.split(b"=", 1)
        body_dict[key_value[0]] = key_value[1]

    return body_dict

def parse_multipart_body(body, content_type):
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

    for i in range(len(split_body)):
        split_part = split_body[i].split(b"\r\n\r\n")

        if len(split_part) < 1:
            raise RuntimeError("Error parsing multipart (split_part1)")

        result_dict[b"Multipart " + bytes(i)] = {}
        result_dict[b"Multipart " + bytes(i)][b"Headers"] = {}

        part_headers = split_part[0].split(b"\r\n")[1:]
        for header in part_headers:
            split_header = header.split(b": ")
            if len(split_header) < 2:
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

def parse_filetype(extension):
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

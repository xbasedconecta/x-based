#!/usr/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import tempfile
import cgi
import os
import sys

class CAHandler(BaseHTTPRequestHandler):

    FORM_HTML = '''\
<!DOCTYPE html>
<html lang="pt-br">
  <head>
    <link rel="shortcut icon" href="favicon/favicon.ico" type="image/x-icon">
    <link rel="shortcut icon" href="./página ca/favicon.ico" type="image/x-icon">
    <title>X-Based | CA</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        background: #fff;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        margin: 0;
      }

      fieldset {
        border: none;
        text-align: center;
      }

      legend {
        font-size: 1.8em;
        font-weight: bold;
        margin-bottom: 20px;
      }

      label {
        font-size: 1.1em;
        font-weight: bold;
        color: #000;
      }

      #csr {
        display: none;
      }

      /* Botão de selecionar arquivo */
      input[type="file"] + label::after {
        content: "Nenhum Arquivo";
        display: block;
        margin-top: 5px;
        font-size: 0.9em;
        color: #888;
      }

      input[type="file"]::file-selector-button {
        background-color: #008000;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 1em;
      }

      /* Botão normal (Sign/Assinar) */
      input[type="submit"] {
        background-color: #008000;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 1em;
        border-radius: 5px;
        cursor: pointer;
        margin-top: 20px;
      }

      input[type="submit"]:hover {
        background-color: #008000;
      }

      /* Radio buttons alinhados */
      div {
        margin: 15px 0;
      }

      input[type="radio"] {
        margin-left: 10px;
      }

      #escolhaArquivo{
        background-color: #008000;
        padding: 25px;
        color: white;
        border-radius: 10rem;
        cursor: pointer;
      }

      #escolhaArquivo:hover{
        background-color: #1f706b;
      }
    </style>
  </head>
  <body>
    <form method="POST" enctype="multipart/form-data" action="sign">
      <fieldset>
        <legend>X-Based | CA</legend>
        <div>
          <label for="csr" id="escolhaArquivo">Escolha Um Arquivo</label>
          <input name="certreq" type="file" id="csr">
        </div>
        <div style="margin-top: 4rem ;">
          <label>Type</label><br>
          <input type="radio" name="type" id="sign" value="sign">
          <label for="sign">Sign</label>
          <br>
          <input type="radio" name="type" id="auth" value="auth">
          <label for="auth">Auth</label>
          <br>
          <input type="radio" name="type" id="auto" value="auto" checked>
          <label for="auto">Autodetect from file name</label>
        </div>
        <div>
          <input type="submit" value="Assinar"/>
        </div>
      </fieldset>
    </form>
  </body>
</html>
'''.encode()

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(410, "Gone")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(self.FORM_HTML)

    def do_POST(self):
        cgi.maxlen = 10000

        expect = self.headers.get('expect', "")
        if expect.lower() == "100-continue":
            self.send_response(100)
            self.end_headers()

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'})

        req_item = form['certreq']
        req_type = form.getfirst('type', 'auto')

        if req_item.filename:
            # The field contains an uploaded file
            if req_type == "auto":
                if "sign" in req_item.filename:
                    sign_type = "sign"
                else:
                    sign_type = "auth"
            else:
                if req_type == "sign":
                    sign_type = "sign"
                else:
                    sign_type = "auth"

            try:
                t = tempfile.NamedTemporaryFile()
                t.write(req_item.file.read())
                t.flush()
                p = subprocess.Popen(["bash", "/home/ca/CA/sign_req.sh", sign_type, t.name],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (out, err) = p.communicate()
                t.close()
                p.wait()
                if p.returncode == 0:
                    crtname = os.path.splitext(req_item.filename)[0].replace("_csr_", "_crt_")
                    self.send_response(200, 'OK')
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition',
                                     'attachment; filename="{}.pem"'.format(crtname))
                    self.send_header('Content-Length', len(out))
                    self.end_headers()
                    self.wfile.write(out)
                else:
                    err = err.decode()
                    print(err, file=sys.stderr)
                    self.send_response(500)
                    self.send_header("Content-Type", 'text/html; charset="utf-8"')
                    self.end_headers()
                    self.wfile.write("<html><body>Error:<pre>{}</pre></body></html>".format(err).encode())
                return
            finally:
                t.close()
                req_item.file.close()

        self.send_error(400)
        return

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 9998), CAHandler)
    print('Starting server...')
    server.serve_forever()

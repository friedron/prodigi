import uuid
import socketio
import tornado
import argparse
import os
from dotenv import load_dotenv
from tornado.log import access_log, app_log, gen_log
import logging
import logging.handlers
from handlers.websocket import AppHandler

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    log_file = os.path.join(log_dir, "server.log")
    print(f"Using log file: {log_file}")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    with open(log_file, "w"):
        pass

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s: %(message)s")
    handler.setFormatter(formatter)

    # Add to Tornado loggers
    for logger in [access_log, app_log, gen_log]:
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

    # Add to root logger
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.WARNING)


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        # Add security headers
        self.set_header("X-Frame-Options", "DENY")  # Prevent clickjacking
        self.set_header("X-XSS-Protection", "1; mode=block")  # Prevent XSS
        self.set_header("X-Content-Type-Options", "nosniff")  # Prevent MIME sniffing
        self.set_header(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )  # Referrer control
        self.set_header(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
        )
        self.set_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self';",
        )

    def get(self):
        session_id = self.get_secure_cookie("session_id")
        if session_id:
            session_id = session_id.decode()
        if not session_id:
            session_id = str(uuid.uuid4())
            self.set_secure_cookie(
                "session_id", session_id, httponly=True, secure=True, samesite="Lax"
            )
        try:
            self.render("index.html")
        except FileNotFoundError:
            self.write("File not found")
class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self, template_path):
        self.template_path = template_path

    def get(self, filename=""):
        # If no filename or at root, list all files with download buttons
        if not filename or filename == "/":
            try:
                if not os.path.exists(self.template_path):
                    self.write("<p><em>No templates folder found.</em></p>")
                    return
                files = [
                    f for f in os.listdir(self.template_path)
                    if os.path.isfile(os.path.join(self.template_path, f))
                ]
                files.sort()
                content = [
                    '<!DOCTYPE html><html><head><meta charset="utf-8">'
                    '<title>Templates</title>'
                    '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />'
                    '</head><body class="container py-5">'
                    '<h1 class="mb-4">All Templates</h1>'
                ]
                if files:
                    content.append('<ul class="list-group mb-3">')
                    for f in files:
                        href = f"/templates/{f}"
                        content.append(
                            f'<li class="list-group-item d-flex justify-content-between align-items-center">'
                            f'<span>{f}</span>'
                            f'<a class="btn btn-sm btn-primary" href="{href}">Download</a>'
                            '</li>'
                        )
                    content.append('</ul>')
                else:
                    content.append('<p><em>No templates found.</em></p>')
                content.append('</body></html>')
                self.write("".join(content))
            except Exception as e:
                self.set_status(500)
                self.write(f"Error reading templates: {e}")
            return

        # If a filename is specified, serve it for download
        file_path = os.path.join(self.template_path, filename)
        if not os.path.isfile(file_path):
            self.set_status(404)
            self.write("Template not found")
            return
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
        with open(file_path, 'rb') as f:
            self.write(f.read())

class DocsHandler(tornado.web.RequestHandler):
    def initialize(self, docs_path):
        self.docs_path = docs_path

    def get(self, path=""):
        # If no path, list all folders and their HTML notebook files
        if not path or path == "/":
            try:
                if not os.path.exists(self.docs_path):
                    self.write("<p><em>No notebooks folder found.</em></p>")
                    return
                folder_names = [
                    d
                    for d in os.listdir(self.docs_path)
                    if os.path.isdir(os.path.join(self.docs_path, d))
                ]
                folder_names.sort()
                content = [
                    '<!DOCTYPE html><html><head><meta charset="utf-8">'
                    "<title>Notebooks</title>"
                    '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />'
                    '</head><body class="container py-5">'
                    '<h1 class="mb-4">All Notebooks</h1>'
                ]
                for folder in folder_names:
                    if folder.startswith("data"):
                        continue
                    folder_path = os.path.join(self.docs_path, folder)
                    files = [f for f in os.listdir(folder_path) if f.endswith(".html")]
                    files.sort()
                    content.append(
                        f'<h2 class="mt-4">{folder.replace("_", " ").title()}</h2>'
                    )
                    if files:
                        content.append('<ul class="list-group mb-3">')
                        for f in files:
                            # URL: /notebooks/folder/file.html
                            href = f"/notebooks/{folder}/{f}"
                            content.append(
                                f'<li class="list-group-item">'
                                f'<a href="{href}">{f}</a></li>'
                            )
                        content.append("</ul>")
                    else:
                        content.append("<p><em>No notebooks found.</em></p>")
                content.append("</body></html>")
                self.write("".join(content))
            except Exception as e:
                self.set_status(500)
                self.write(f"Error reading notebooks: {e}")
            return

        # Otherwise, serve a specific file (folder/file.html)
        segments = path.strip("/").split("/", 1)
        if len(segments) != 2:
            self.set_status(404)
            self.write("Notebook not found")
            return

        folder, filename = segments
        if not filename.endswith(".html"):
            filename += ".html"
        file_path = os.path.join(self.docs_path, folder, filename)
        if not os.path.isfile(file_path):
            self.set_status(404)
            self.write("Notebook not found")
            return
        with open(file_path, "r", encoding="utf-8") as f:
            self.write(f.read())


def main(args):
    setup_logging()
    print("Allowed origins: ", os.environ.get("ALLOWED_ORIGINS", "*").split(","))
    logging.info(
        "Allowed origins: %s", os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    )
    try:
        allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
        async_server = socketio.AsyncServer(
            async_mode="tornado",
            cors_allowed_origins="*",
            ping_interval=30,
            ping_timeout=30,
            logger=False,
            engineio_logger=False,
        )

        application = tornado.web.Application(
            [
                (r"/socket.io/", socketio.get_tornado_handler(async_server)),
                (
                    r"/assets/(.*)",
                    tornado.web.StaticFileHandler,
                    {"path": os.path.join(base_dir, "static/assets")},
                ),
                (
                    r"/notebooks(?:/(.*))?",
                    DocsHandler,
                    {"docs_path": os.path.join(base_dir, "demo")},
                ),
                (
                    r"/templates(?:/(.+))?",
                    TemplateHandler,
                    {"template_path": os.path.join(base_dir, "templates")},

                ),
                (r'/.*', MainHandler),
            ],
            debug=True,
            max_body_size=400 * 1024 * 1024,  # 300 MB
            static_path=os.path.join(base_dir, "static"),
            template_path=os.path.join(base_dir, "static"),
            cookie_secret=os.environ.get(
                "COOKIE_SECRET", "xipDx3eP4j_YkXJhxipDx3eP4j_YkXJh"
            ),
            xheaders=True,
        )
        apphandler = AppHandler(application, args)
        async_server.register_namespace(apphandler)
        application.listen(args.port)
        print(f"Starting server on port {args.port}")
        try:
            tornado.ioloop.IOLoop.current().start()
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            if apphandler.cleanup_callback:
                apphandler.cleanup_callback.stop()
            print("Shutting down complete.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Tornado Socket.IO server.")
    parser.add_argument(
        "--port", type=int, default=5005, help="Port to run the server on."
    )
    args = parser.parse_args()
    main(args)

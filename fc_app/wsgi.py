from fc_app.server import FCServer


# Do not change this file if you do not know what you are doing.
def application(environ, start_response):
    return FCServer().wsgi(environ, start_response)

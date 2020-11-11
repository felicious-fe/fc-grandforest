from fc_app import FCServer


def application(environ, start_response):
    return FCServer().wsgi(environ, start_response)

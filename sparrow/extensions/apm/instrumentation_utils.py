from elasticapm.instrumentation.register import register

# For show customer register instrumentation list
register_list = []


def register_instrumentation(cls):
    register_list.append(cls)
    register(cls)

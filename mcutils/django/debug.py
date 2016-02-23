def reset_queries():
    from django.db import reset_queries, connection
    result = len(connection.queries), sum(
        map(lambda q: float(q['time']), connection.queries))
    reset_queries()
    return result

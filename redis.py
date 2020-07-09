import pickle
import queue as q
import redis

pool = redis.BlockingConnectionPool(host='localhost', port=6379, db=0, queue_class=q.Queue)
r = redis.Redis(connection_pool=pool)


def redis_get(key):
    if key in r:
        return pickle.loads(r.get(key))
    else:
        return None


def redis_set(key, value):
    r.set(key, pickle.dumps(value))

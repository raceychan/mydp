import uuid
import pika

from core.broker import broker
# SERVER:

# 创建socket
connection = broker.connection

# 获取通道
channel = broker.connection.channel()

# 生成队列
channel.queue_declare(queue='rpc_queue')


def fib(n):
    '''用于获取斐波那契数列'''
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


def on_request(ch, method, props, body):
    '''获取数据的回调函数'''
    n = int(body)

    print(" [.] fib(%s)" % n)
    response = fib(n)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(
                         correlation_id=props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


# 设置为空闲的客户端减少压力
channel.basic_qos(prefetch_count=1)
# 预备开始消费
channel.basic_consume(queue='rpc_queue', on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
# 开始消费，从客户端获取
channel.start_consuming()



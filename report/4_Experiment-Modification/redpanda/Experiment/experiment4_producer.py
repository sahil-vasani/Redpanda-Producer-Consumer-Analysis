from confluent_kafka import Producer
import time

conf = {
'bootstrap.servers': 'localhost:9092'
}

producer = Producer(conf)

topic = "retry-topic"

messages = [
"payment_1",
"payment_2",
"payment_1",
"payment_3",
"payment_2",
"payment_4"
]

for msg in messages:

 producer.produce(
    topic,
    key=msg.encode(),
    value=msg.encode()
)

 print(f"Produced: {msg}")

 time.sleep(1)

 producer.flush()

print("DONE")

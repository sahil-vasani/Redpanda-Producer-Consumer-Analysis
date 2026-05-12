from confluent_kafka import Producer
import random
import time

conf = {
'bootstrap.servers': 'localhost:9092'
}

producer = Producer(conf)

topic = "hot-topic"

users = [
"user_1",
"user_2",
"user_3",
"user_4",
"user_5"
]

for i in range(100):


 user = random.choice(users)

 value = f"event-{i}-from-{user}"

 producer.produce(
    topic,
    key=user.encode(),
    value=value.encode()
 )

 print(f"Produced: {value}")

 time.sleep(0.1)


 producer.flush()

print("DONE")


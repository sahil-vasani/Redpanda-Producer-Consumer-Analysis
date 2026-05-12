from confluent_kafka import Consumer

conf = {
'bootstrap.servers': 'localhost:9092',
'group.id': 'retry-group',
'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)

consumer.subscribe(["retry-topic"])

print("Waiting for messages...")

while True:

 msg = consumer.poll(1.0)

 if msg is None:
    continue

 if msg.error():
    print("ERROR:", msg.error())
    continue

 print(
    f"PARTITION={msg.partition()} "
    f"OFFSET={msg.offset()} "
    f"VALUE={msg.value().decode()}"
 )

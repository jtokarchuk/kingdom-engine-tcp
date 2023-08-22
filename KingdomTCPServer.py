import asyncio
import json
import logging
import pathlib
import os
import redis
import sys
from threading import Thread
import time
import uuid

from datetime import datetime
from TCPClient import Client

class Server:
    def __init__(self, ip: str, port: int, loop: asyncio.AbstractEventLoop):
        self.__ip: str = ip
        self.__port: int = port
        self.__loop: asyncio.AbstractEventLoop = loop
        self.__logger: logging.Logger = self.initialize_logger()
        self.__clients: dict[asyncio.Task, Client] = {}
        self.__id: str(uuid.uuid4())

        self.logger.info(f"Server Initialized with {self.ip}:{self.port}")
        self.gs_send = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.running = True
    
    @property
    def ip(self):
        return self.__ip

    @property
    def port(self):
        return self.__port

    @property
    def loop(self):
        return self.__loop

    @property
    def logger(self):
        return self.__logger

    @property
    def clients(self):
        return self.__clients

    def initialize_logger(self):
        '''
        Initializes a logger and generates a log file in ./logs.
        Returns
        '''
        path = pathlib.Path(os.path.join(os.getcwd(), "logs"))
        path.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger('Server')
        logger.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        fh = logging.FileHandler(
            filename=f'logs/{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}_server.log'
        )
        ch.setLevel(logging.INFO)
        fh.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(asctime)s] - %(levelname)s - %(message)s'
        )

        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addHandler(fh)

        return logger

    def start_server(self):
        '''
        Starts the server on IP and PORT.
        '''
        try:
            self.server = asyncio.start_server(
                self.accept_client, self.ip, self.port
            )
            self.loop.run_until_complete(self.server)
            self.loop.run_forever()
        except Exception as e:
            self.logger.error(e)
        except KeyboardInterrupt:
            self.logger.warning("Keyboard Interrupt Detected. Shutting down!")
            self.running = False

        self.shutdown_server()

    def accept_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        '''
        Callback that is used when server accepts clients
        '''

        client = Client(client_reader, client_writer)
        task = asyncio.Task(self.handle_client(client))
        self.clients[task] = client

        client_ip = client_writer.get_extra_info('peername')[0]
        client_port = client_writer.get_extra_info('peername')[1]
        self.logger.info(f"New Connection: {client_ip}:{client_port}")

        # inform the game server of our presence
        self.send_gameserver_message(client, None, "new_connection")

        task.add_done_callback(self.disconnect_client)
    

    async def handle_client(self, client: Client):
        '''
        Handles incoming messages from client
        '''
        while client.active:
            client_message = await client.get_message()
            if client_message:
                self.send_gameserver_message(client, client_message, "game_command")
                self.logger.info(f"Received: {client_message}")

            await client.writer.drain()

        self.logger.info("Client Disconnected!")

    def send_gameserver_message(self, client: Client, message, type):
        gs_message = {
            "time": int(time.time()),
            "client": "telnet",
            "ip_address": client.ip,
            "user_id": client.user_id,
            "content": message,
            "meta": type
        }
        self.gs_send.rpush("gs_inbox", json.dumps(gs_message))
        client.last_command = gs_message["time"]


    def broadcast_message(self, message):
        '''
        Send message to all connected clients
        '''
        for client in self.clients.values():
            client.send_message(message)

    def disconnect_client(self, task: asyncio.Task):
        client = self.clients[task]
        self.send_gameserver_message(client, None, "disconnect")
        client.writer.close()
        del self.clients[task]
        

    def shutdown_server(self):
        '''
        Shuts down server.
        '''
        self.logger.info("Shutting down server!")
        server.running = False
        for client in self.clients.values():
            client.send_message('Server is shutting down')
        self.loop.stop()

def messaging_thread_func(server):
    gs_receive = redis.Redis(host='localhost', port=6379, decode_responses=True)

    while server.running:
        message = gs_receive.blpop("gs_outbox_telnet", 1)

        """
        A message looks like:
        user_id: recipient,
        content: what to send
        meta: server action (message, disconnect)
        """
        if message:
            message = json.loads(message[1])
            for client in server.clients.values():
                if client.user_id in message["user_id"]:
                    if message["content"]:
                        client.send_message(message["content"])
                    if message["meta"] == "disconnect":
                        client.active = False

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    server = Server("0.0.0.0", 23, loop)
    thread = Thread(target = messaging_thread_func, args = (server,))
    thread.start()
    server.start_server()
import asyncio
import sys
import logging
import pathlib
import os
from TCPClient import Client
from datetime import datetime


class Server:
    def __init__(self, ip: str, port: int, loop: asyncio.AbstractEventLoop):
        '''
        Parameters
        ———-
        ip : str
            IP that the server will be using
        port : int
            Port that the server will be using
        ———-
        '''
        self.__ip: str = ip
        self.__port: int = port
        self.__loop: asyncio.AbstractEventLoop = loop
        self.__logger: logging.Logger = self.initialize_logger()
        self.__clients: dict[asyncio.Task, Client] = {}

        self.logger.info(f"Server Initialized with {self.ip}:{self.port}")

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
        ——-
        logging.Logger
            Used for writing logs of varying levels to the console and log file.
        ——-
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
            '[%(asctime)s] – %(levelname)s – %(message)s'
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

        task.add_done_callback(self.disconnect_client)
    

    async def handle_client(self, client: Client):
        '''
        Handles incoming messages from client
        '''
        while True:
            client_message = await client.get_message()
            # TODO: Send message to game server here

            client.send_message(f"You sent: {client_message}")

            self.logger.info(f"{client_message}")

            await client.writer.drain()

        self.logger.info("Client Disconnected!")

    def broadcast_message(self, message):
        '''
        Send message to all connected clients
        '''
        for client in self.clients.values():
            client.send_message(message)

    def disconnect_client(self, task: asyncio.Task):
        client = self.clients[task]
        del self.clients[task]
        client.writer.close()
        self.logger.info("End Connection")

    def shutdown_server(self):
        '''
        Shuts down server.
        '''
        self.logger.info("Shutting down server!")
        for client in self.clients.values():
            client.send_message('Server is shutting down')
        self.loop.stop()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(f"Usage: {sys.argv[0]} HOST_IP PORT")

    loop = asyncio.get_event_loop()
    server = Server(sys.argv[1], sys.argv[2], loop)
    server.start_server()
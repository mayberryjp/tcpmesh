import socket
import threading
import time
import random
import logging
import json
import os
import sys
from typing import Dict, List, Tuple, Optional
import paho.mqtt.client as mqtt
import re

from const import VERSION, ENTITIES, prompt_response_dict

# Configuration from environment variables
class Config:
    MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', 'password')
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', 'username')
    LISTEN_ADDRESS = os.getenv('LISTEN_ADDRESS', '0.0.0.0')
    LISTEN_PORT = int(os.getenv('LISTEN_PORT', '55555'))
    PEERS = os.getenv('PEERS', '192.168.49.80:55555').split(',')
    HELLO_INTERVAL = int(os.getenv('HELLO_INTERVAL', 300))  # Default to 5 minutes if not set

# Helper functions
def replace_periods(sensor_name):
    """Replace non-word characters with underscores for MQTT topic compatibility"""
    return re.sub(r'\W', '_', sensor_name)


class MQTTClient:
    """Handles all MQTT communications"""
    
    def __init__(self, logger):
        self.logger = logger
        self.client = None
        self.connected = self.connect_persistent()
        
    def connect_persistent(self) -> bool:
        """Create and connect a persistent MQTT client"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        
        try:
            self.client.connect(Config.MQTT_HOST, 1883)
            self.client.loop_start()  # Start the loop in the background
            self.logger.info(f"Successfully connected to MQTT broker at {Config.MQTT_HOST}")
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            self.client = None
            return False
            
    def disconnect_persistent(self):
        """Safely disconnect the persistent MQTT client"""
        if not self.client:
            return
            
        try:
            self.client.loop_stop()  # Stop the background thread
            self.client.disconnect()
            self.logger.info("Disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def publish(self, topic: str, payload, retain: bool = False) -> bool:
        """Publish a message to MQTT broker and handle errors"""
        if not self.client or not self.connected:
            self.logger.error(f"No active MQTT connection, attempting to reconnect")
            self.connected = self.connect_persistent()
            if not self.connected:
                return False
            
        success = False
        try:
            ret = self.client.publish(topic, payload=payload, qos=2, retain=retain)
            ret.wait_for_publish(timeout=5.0)  # Add timeout for safety
            
            if ret.rc == mqtt.MQTT_ERR_SUCCESS:
                success = True
                self.logger.info(f"Successfully published to {topic}: {payload}")  # Changed to INFO for visibility
            else:
                self.logger.error(f"Failed to publish to {topic} with error code {ret.rc}")
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            
        return success
    
    def send_connection_status(self, peer_address: Tuple[str, int], is_connected: bool):
        """Send connection status for a peer"""
        peer_ip, peer_port = peer_address
        status = "on" if is_connected else "off"
        
        topic = f"homeassistant/binary_sensor/tcpmesh_{replace_periods(Config.LISTEN_ADDRESS)}_{replace_periods(f'{peer_ip}_{peer_port}')}_connected/state"
        
        if self.publish(topic, status):
            self.logger.info(f"Published connection status '{status}' for {peer_address}")
        
    def send_latency_measurement(self, peer_address: Tuple[str, int], latency_ms: float):
        """Send latency measurement for a peer"""
        peer_ip, peer_port = peer_address
        
        topic = f"homeassistant/sensor/tcpmesh_{replace_periods(Config.LISTEN_ADDRESS)}_{replace_periods(f'{peer_ip}_{peer_port}')}/state"
        
        if self.publish(topic, round(latency_ms, 0)):
            self.logger.debug(f"Published latency {latency_ms:.0f}ms for {peer_address}")


class TCPMeshSensor:
    """Represents a Home Assistant sensor for TCP mesh monitoring"""
    
    def __init__(self, name_constant, type, sensor_type):
        self.device_class = None
        self.unit_of_measurement = None
        self.state_class = None
        self.sensor_type = sensor_type
        
        name_replace = name_constant
        name_object = ENTITIES[type]
        
        self.name = f"tcpmesh_{name_replace}"
        if name_object["device_class"] is not None:
            self.device_class = name_object["device_class"]
        if name_object["unit_of_measurement"] is not None:
            self.unit_of_measurement = name_object["unit_of_measurement"]
        if name_object["state_class"] is not None:
            self.state_class = name_object["state_class"]
            
        self.state_topic = f"homeassistant/{sensor_type}/tcpmesh_{name_replace}/state"
        self.unique_id = f"tcpmesh_{name_replace}"
        self.device = {
            "identifiers": [f"tcpmesh_{name_replace}"],
            "name": f"TCPMesh For {name_replace}",
        }
        
    def to_json(self):
        payload = {
            "name": self.name,
            "state_topic": self.state_topic,
            "unique_id": self.unique_id,
            "device": self.device,
        }
        
        if self.device_class:
            payload["device_class"] = self.device_class
            
        # Only include these if NOT a binary_sensor
        if self.sensor_type != "binary_sensor":
            if self.unit_of_measurement:
                payload["unit_of_measurement"] = self.unit_of_measurement
            if self.state_class:
                payload["state_class"] = self.state_class
        else:
            # binary_sensor: add payload_on/off
            payload["payload_on"] = "on"
            payload["payload_off"] = "off"
            
        return payload


class MessageHandler:
    """Handles TCP message parsing and response generation"""
    
    def __init__(self, logger, mqtt_client):
        self.logger = logger
        self.mqtt_client = mqtt_client
        self.prompt_response_dict = prompt_response_dict
        
    def create_prompt_message(self, prompt: str) -> Dict:
        """Create a prompt message to send to peers"""
        return {
            "type": "prompt",
            "content": prompt,
            "timestamp": time.time()
        }
        
    def create_response_message(self, prompt: str, response: str, original_timestamp: float) -> Dict:
        """Create a response message for a received prompt"""
        return {
            "type": "response",
            "prompt": prompt,
            "content": response,
            "original_timestamp": original_timestamp,
            "response_timestamp": time.time()
        }
        
    def handle_prompt(self, message: Dict, address: Tuple[str, int]) -> Optional[Dict]:
        """Handle a received prompt message"""
        content = message.get("content", "")
        timestamp = message.get("timestamp", 0)
        
        self.logger.info(f"Received prompt from {address}: {content[:30]}...")
        
        if content in self.prompt_response_dict:
            response = self.prompt_response_dict[content]
            return self.create_response_message(content, response, timestamp)
        else:
            self.logger.critical(f"FATAL ERROR: Received unknown prompt from {address}: {content[:30]}...")
            return None
            
    def handle_response(self, message: Dict, address: Tuple[str, int], sent_prompts: Dict) -> Tuple[bool, Optional[str]]:
        """Handle a received response message and update metrics"""
        content = message.get("content", "")
        original_prompt = message.get("prompt", "")
        original_timestamp = message.get("original_timestamp", 0)
        response_timestamp = message.get("response_timestamp", 0)
        current_time = time.time()
        
        # Calculate response time (convert to milliseconds)
        total_time_ms = (current_time - original_timestamp) * 1000
        
        self.logger.info(f"Received response from {address}: {content[:30]}...")
        self.logger.info(f"Response time metrics for {address}:")
        total_time_ms_no_dec = round(total_time_ms, 0)
        self.logger.info(f"  Total time: {total_time_ms_no_dec} ms")
        
        # Send metrics to MQTT
        self.mqtt_client.send_latency_measurement(address, total_time_ms)
        self.mqtt_client.send_connection_status(address, True)
        
        # Verify the response
        key = (address, original_prompt)
        if key in sent_prompts:
            expected_response = sent_prompts[key]['expected_response']
            if content == expected_response:
                self.logger.info(f"Response from {address} is correct")
                return True, original_prompt
            else:
                self.logger.critical(f"FATAL ERROR: Incorrect response from {address}. Expected: {expected_response[:30]}...")
                return False, original_prompt
        else:
            self.logger.critical(f"FATAL ERROR: Received response from {address} for unknown prompt")
            return False, None


class TCPMeshDaemon:
    """Main TCP mesh daemon that manages connections and message exchange"""
    
    def __init__(self, host: str, port: int, peers: List[Tuple[str, int]], mqtt_client=None):
        self.host = host
        self.port = port
        self.peers = peers
        self.connections = {}  # Maps address to socket
        self.sent_prompts = {}  # Maps (address, prompt) to timestamp and expected response
        self.running = True
        self.lock = threading.Lock()
        self.disconnect_counts = {}  # Maps address to disconnect count
        
        # Initialize disconnect counts for all peers
        for peer_host, peer_port in peers:
            self.disconnect_counts[(peer_host, peer_port)] = 0
        
        # Set up logging
        self.logger = logging.getLogger(f"TCPMeshDaemon-{host}:{port}")
        
        # Use provided mqtt_client or create a new one
        self.mqtt_client = mqtt_client or MQTTClient(self.logger)
        self.message_handler = MessageHandler(self.logger, self.mqtt_client)
        
    def start(self):
        """Start the TCP mesh daemon."""
        # Start server thread
        server_thread = threading.Thread(target=self.run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Give the server time to start
        time.sleep(2)
        
        # Connect to peers
        for peer_host, peer_port in self.peers:
            client_thread = threading.Thread(target=self.connect_to_peer, args=(peer_host, peer_port))
            client_thread.daemon = True
            client_thread.start()
            
        # Start the hello message thread
        hello_thread = threading.Thread(target=self.hello_message_loop)
        hello_thread.daemon = True
        hello_thread.start()
        
        # Start the reconnection loop thread
        reconnect_thread = threading.Thread(target=self.reconnection_loop)
        reconnect_thread.daemon = True
        reconnect_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.logger.info("Shutting down...")
    
    def run_server(self):
        """Run the server to accept incoming connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            self.logger.info(f"Server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    self.logger.info(f"Accepted connection from {address}")
                    
                    # Start a new thread to handle this connection
                    handler_thread = threading.Thread(
                        target=self.handle_connection, 
                        args=(client_socket, address)
                    )
                    handler_thread.daemon = True
                    handler_thread.start()
                except Exception as e:
                    self.logger.critical(f"FATAL ERROR accepting connection: {e}")
        except Exception as e:
            self.logger.critical(f"FATAL SERVER ERROR: {e}")
        finally:
            server_socket.close()
    
    def connect_to_peer(self, peer_host: str, peer_port: int):
        """Connect to a peer server."""
        try:
            if (peer_host, peer_port) not in self.connections:
                self.logger.info(f"Connecting to peer {peer_host}:{peer_port}")
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((peer_host, peer_port))
                
                # Add to connections
                with self.lock:
                    self.connections[(peer_host, peer_port)] = client_socket
                
                # Start handler thread
                handler_thread = threading.Thread(
                    target=self.handle_connection, 
                    args=(client_socket, (peer_host, peer_port))
                )
                handler_thread.daemon = True
                handler_thread.start()
        except Exception as e:
            self.logger.critical(f"FATAL ERROR connecting to peer {peer_host}:{peer_port}: {e}")
            address = (peer_host, peer_port)
            # Add this line to send disconnect notification
            self.mqtt_client.send_connection_status(address, False)
            # Increment disconnect count for failed connection attempts
            self.increment_disconnect_count(address)
    
    def handle_connection(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle an individual client connection."""
        try:
            buffer = ""
            while self.running:
                # Receive data
                data = client_socket.recv(4096)
                
                if not data:
                    self.logger.critical(f"FATAL ERROR: Connection closed by {address}")
                    break
                
                # Add to buffer and process complete messages
                buffer += data.decode('utf-8')
                
                # Process complete JSON messages (may be multiple or partial)
                messages = buffer.split('\n')
                buffer = messages.pop()  # Last element might be incomplete
                
                for msg in messages:
                    if msg.strip():  # Skip empty lines
                        self.process_message(msg, client_socket, address)
                
        except Exception as e:
            self.logger.critical(f"FATAL ERROR handling connection from {address}: {e}")
        finally:
            client_socket.close()
            with self.lock:
                if address in self.connections:
                    del self.connections[address]
                    # Increment disconnect count
                    self.increment_disconnect_count(address)
        # Send disconnect notification
        self.mqtt_client.send_connection_status(address, False)
    
    def hello_message_loop(self):
        """Send hello messages to all connected peers at regular intervals."""
        while self.running:
            # Wait for the next interval
            time.sleep(Config.HELLO_INTERVAL)
            
            # Send hello to all peers
            with self.lock:
                for address, conn in list(self.connections.items()):
                    try:
                        # Select a random prompt
                        prompt = random.choice(list(self.message_handler.prompt_response_dict.keys()))
                        expected_response = self.message_handler.prompt_response_dict[prompt]
                        
                        # Record this prompt
                        current_time = time.time()
                        self.sent_prompts[(address, prompt)] = {
                            'timestamp': current_time,
                            'expected_response': expected_response
                        }
                        
                        # Create and send message
                        message = self.message_handler.create_prompt_message(prompt)
                        conn.sendall((json.dumps(message) + '\n').encode('utf-8'))
                        self.logger.info(f"Sent prompt to {address}: {prompt[:30]}...")
                    except Exception as e:
                        self.logger.critical(f"FATAL ERROR sending hello to {address}: {e}")
                        # Mark as disconnected in MQTT
                        self.mqtt_client.send_connection_status(address, False)
                        # Increment disconnect count
                        self.increment_disconnect_count(address)
    
    def reconnection_loop(self):
        """Periodically try to reconnect to disconnected peers."""
        reconnect_interval = 60  # Try reconnecting every 60 seconds
        
        while self.running:
            time.sleep(reconnect_interval)
            
            for peer_host, peer_port in self.peers:
                if (peer_host, peer_port) not in self.connections:
                    self.logger.info(f"Attempting to reconnect to {peer_host}:{peer_port}")
                    client_thread = threading.Thread(
                        target=self.connect_to_peer, 
                        args=(peer_host, peer_port)
                    )
                    client_thread.daemon = True
                    client_thread.start()
    
    def process_message(self, data: str, client_socket: socket.socket, address: Tuple[str, int]):
        """Process an incoming message."""
        try:
            message = json.loads(data)
            message_type = message.get("type", "")
            
            if message_type == "prompt":
                # This is a prompt, we need to respond
                response_message = self.message_handler.handle_prompt(message, address)
                if response_message:
                    # Send response
                    client_socket.sendall((json.dumps(response_message) + '\n').encode('utf-8'))
                    self.logger.info(f"Sent response to {address}: {response_message['content'][:30]}...")
            
            elif message_type == "response":
                # This is a response to our prompt
                success, original_prompt = self.message_handler.handle_response(message, address, self.sent_prompts)
                if success and original_prompt:
                    # Remove the tracked prompt
                    key = (address, original_prompt)
                    if key in self.sent_prompts:
                        del self.sent_prompts[key]
            
            else:
                self.logger.critical(f"FATAL ERROR: Received unknown message type from {address}: {message_type}")
                
        except json.JSONDecodeError:
            self.logger.critical(f"FATAL ERROR: Received invalid JSON from {address}: {data}")
        except Exception as e:
            self.logger.critical(f"FATAL ERROR processing message from {address}: {e}")
    
    def increment_disconnect_count(self, address: Tuple[str, int]):
        """Increment the disconnect count for a peer and publish it"""
        with self.lock:
            if address in self.disconnect_counts:
                self.disconnect_counts[address] += 1
                count = self.disconnect_counts[address]
                self.logger.info(f"Disconnect count for {address} incremented to {count}")
                
                # Publish updated count to MQTT
                self.mqtt_client.send_disconnect_count(address, count)
            else:
                self.disconnect_counts[address] = 1
                self.logger.info(f"Disconnect count for {address} initialized to 1")
                
                # Publish initial count to MQTT
                self.mqtt_client.send_disconnect_count(address, 1)


def initialize_peer_sensor(peer: str, mqtt_client=None):
    """Initialize Home Assistant sensors for a peer"""
    entity = replace_periods(Config.LISTEN_ADDRESS) + "_" + replace_periods(peer)
    
    logger = logging.getLogger(__name__)
    
    # Use provided client or create a new one
    if mqtt_client is None:
        mqtt_client = MQTTClient(logger)
    
    # Create sensor configurations
    tcpmesh_sensor = TCPMeshSensor(entity, "measurement", "sensor")
    sensor_message = json.dumps(tcpmesh_sensor.to_json())
    
    boolean_entity = f"{entity}_connected"
    tcpmesh_boolean = TCPMeshSensor(boolean_entity, "connectivity", "binary_sensor")
    boolean_message = json.dumps(tcpmesh_boolean.to_json())
    
    # Create disconnect count sensor
    disconnect_entity = f"{entity}_disconnects"
    tcpmesh_disconnects = TCPMeshSensor(disconnect_entity, "counter", "sensor")
    disconnect_message = json.dumps(tcpmesh_disconnects.to_json())
    
    # Publish sensor configurations to MQTT
    logger.info(f"Publishing sensor configuration for {peer}")
    mqtt_client.publish(
        f"homeassistant/sensor/tcpmesh_{entity}/config", 
        sensor_message, 
        retain=True
    )
    
    mqtt_client.publish(
        f"homeassistant/binary_sensor/tcpmesh_{boolean_entity}/config", 
        boolean_message, 
        retain=True
    )
    
    mqtt_client.publish(
        f"homeassistant/sensor/tcpmesh_{disconnect_entity}/config", 
        disconnect_message, 
        retain=True
    )
    
    logger.info(f"Sensor initialization complete for {peer}")
    
    # Also send initial "off" status and zero disconnect count
    peer_parts = peer.split(':')
    address = (peer_parts[0], int(peer_parts[1]))
    mqtt_client.send_connection_status(address, False)
    mqtt_client.send_disconnect_count(address, 0)


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("TCPMesh")
    
    logger.info(f"Starting TCP Mesh Daemon v{VERSION}")
    
    # Log configuration values for debugging
    logger.info(f"Configuration:")
    logger.info(f"  MQTT_HOST: {Config.MQTT_HOST}")
    logger.info(f"  MQTT_USERNAME: {Config.MQTT_USERNAME}")
    logger.info(f"  LISTEN_ADDRESS: {Config.LISTEN_ADDRESS}")
    logger.info(f"  LISTEN_PORT: {Config.LISTEN_PORT}")
    logger.info(f"  PEERS: {Config.PEERS}")
    
    # Create global MQTT client
    mqtt_client = MQTTClient(logger)
    if not mqtt_client.connected:
        logger.critical("Failed to connect to MQTT broker. Exiting.")
        return
        
    try:
        # Parse peers and initialize sensors
        peers = []
        for peer in Config.PEERS:
            try:
                host, port = peer.split(':')
                peers.append((host, int(port)))
                initialize_peer_sensor(peer, mqtt_client)  # Pass existing client
            except Exception as e:
                logger.critical(f"ERROR parsing peer address '{peer}': {e}")
        
        # Create and start the daemon - pass the mqtt_client
        daemon = TCPMeshDaemon(Config.LISTEN_ADDRESS, Config.LISTEN_PORT, peers, mqtt_client)
        daemon.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}", exc_info=True)
    finally:
        # Properly disconnect the MQTT client
        mqtt_client.disconnect_persistent()
        logger.info("MQTT client disconnected")

if __name__ == "__main__":
    main()
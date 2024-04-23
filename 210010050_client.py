from socket import *
import threading
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import cv2
import numpy as np

clients = {} # Dictionary to store the client names and their public keys
done = False

def receive(client_socket, rsa_key_pair): # Receive messages from the server
    global clients
    while True:
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                break
            elif data[0] == '[':
                print()
                print(data)      
            elif data[0] == '<':
                rem = data[data.index(' ')+1:data.index('left')-1]
                print(data)
                del clients[rem]
                print(f"[ACTIVE CONNECTIONS]: {len(clients)}\n")
            elif data[0] == '{':
                json_data=data[:data.index('}')+1]
                clients = json.loads(json_data)    
            elif data == "*":
                msg = client_socket.recv(4096)
                decrypt_and_display(rsa_key_pair, msg)
            elif data[0] == "#":
                client_socket.send("#".encode())
                data = client_socket.recv(4096).decode()
                stream(data)   
                print("\nVideo streaming ended\n")              
        except error as e:
            print(f"Error: {e}")

def stream(data): # Stream the video frames received from the server
    global done
    idx = 0
    print("\nAvailable videos:")
    for x in data.split():
        idx += 1
        print(idx,":",x) 
    vid=input("Enter the serial number of the video you want to watch: ")
    client_socket.send(vid.encode())
    data = client_socket.recv(4096).decode()
    print(data)
    
    try:
        while True:
            frame_size_data = client_socket.recv(16)
            if not frame_size_data:
                break
            frame_size = int(frame_size_data.strip())
            if frame_size == 0:
                break
            frame_data = b''
            while len(frame_data) < frame_size:
                remaining_bytes = frame_size - len(frame_data)
                frame_data += client_socket.recv(remaining_bytes)
            frame_np = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (1080, 720))
            cv2.imshow('Video Stream', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                client_socket.sendall(b'00')  # Send signal to stop the video on the server
                break
            else:
                client_socket.sendall(b'10')
        cv2.destroyAllWindows()
        done=True
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

def encrypt_and_send(message, recipient, client_socket): # Encrypt the message and send it to the recipient
    global clients
    try:
        recipient_public_key = RSA.import_key(clients[recipient])
        cipher = PKCS1_OAEP.new(recipient_public_key)
        encrypted_message = cipher.encrypt(message.encode())
        client_socket.send("SIG".encode('utf-8'))
        client_socket.send(encrypted_message)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

def decrypt_and_display(rsa_key_pair, data): # Decrypt the message and display it
    try:
        cipher = PKCS1_OAEP.new(rsa_key_pair)
        decrypted_message = cipher.decrypt(data)
        print(f"[MESSAGE] {decrypted_message.decode()}\n")
    except:
        pass #indicating other clients can't decrypt the message

# Create a socket and connect to the server
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect(('localhost', 12345))

# Send client name and its generated public key to the server
msg = client_socket.recv(4096)  # Receive the prompt to enter the name
client_name = input(msg.decode())
client_socket.send(client_name.encode())
client_socket.recv(4096).decode()  # Receive the prompt to enter the public key
rsa_key_pair = RSA.generate(2048)
public_key = rsa_key_pair.publickey().export_key().decode()
print("Enter your public key", public_key)
client_socket.send(public_key.encode())

receive_thread = threading.Thread(target=receive, args=(client_socket, rsa_key_pair)) # Start a separate thread to receive dictionary updates continuously
receive_thread.start()

while True:
    msg = input("Choose one of the following options:\n[1]-Send Message\n[2]-Stream Video\n[3]-Quit\nEnter your choice:\n")
    try:
        if msg == "1":
            print("\nConnected clients:")
            for item in clients.items():
                if item[0] != client_name:
                    print(item[0])
            print()
            recipient = input("Enter the name of the client: ")
            message = input("Enter the message: ")
            print()
            if recipient not in clients:
                print("Invalid client name. Please try again.")
                continue
            message = f"RECEIVED FROM {client_name} : {message}"
            encrypt_and_send(message, recipient, client_socket)
        elif msg == "2":
            client_socket.send("VIDEO".encode('utf-8'))
            while not done:
                pass
            done = False
        elif msg == "3":
            client_socket.send("QUIT".encode('utf-8'))
            receive_thread.join()
            client_socket.close()
            print("\nQUIT successful\n")
            exit(1)
        else:
            print("Invalid choice. Please try again.")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
from socket import *
import threading
import json
import cv2

clients = {} # Dictionary to store the client names and their public keys
client_sockets = []
videos = ["video_1", "video_2"]

def broadcast(message): # Broadcast the message to all clients
    global client_sockets
    try:
        for client_socket in client_sockets:
            client_socket.send(message.encode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        
def send_video_frames(client_socket, video_list): # Send video frames to the client that requested them
    global videos
    client_socket.send(video_list.encode())
    v_num = int(client_socket.recv(4096).decode())
    client_socket.send(f"Playing Video: video_{v_num}.mp4\nPress 'q' to stop playing".encode())
    try:
        video_files = [f"video_{v_num}_240p.mp4", f"video_{v_num}_720p.mp4", f"video_{v_num}_1080p.mp4"]
        index = 0
        stp = ""
        while index < len(video_files):
            cap = cv2.VideoCapture(video_files[index])
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            start_frame = (total_frames // 3) * index
            end_frame = (total_frames // 3) * (index+1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                frame_data = cv2.imencode('.jpg', frame)[1].tobytes()
                client_socket.sendall((str(len(frame_data))).encode().ljust(16) + frame_data)
                if  current_frame >= end_frame:
                    index += 1
                    if index == 3:
                        client_socket.sendall(b'0')
                    break
                stp = client_socket.recv(1024).decode()
                if stp == '00':
                    break
            cap.release()
            if stp == '00':
                break
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
        
def handle_client(client_socket, addr): # Handle the client connection
    global clients
    global client_sockets
    
    client_socket.send("Enter your name: ".encode())
    name = client_socket.recv(4096).decode()
    client_socket.send("Enter the public key: ".encode())
    public_key = client_socket.recv(2048).decode()
    clients[name] = public_key
    client_sockets.append(client_socket)
    print(f"[ACTIVE CONNECTIONS]: {len(clients)}")
    
    join_msg = f"[NEW CLIENT] {name} joined.\n[ACTIVE CONNECTIONS]: {len(clients)}\n"
    for client_sckt in client_sockets:
        if client_socket != client_sckt:
            client_sckt.send(join_msg.encode('utf-8'))
            
    json_data = json.dumps(clients)
    broadcast(json_data)

    while True:
        try:
            message = client_socket.recv(4096)
            if not message:
                break
            elif message == b'QUIT':
                left_msg = f"<EXIT> {name} left."
                for client_sckt in client_sockets:
                    if client_socket != client_sckt:
                        client_sckt.send(left_msg.encode('utf-8'))
                del clients[name]
                client_sockets.remove(client_socket)
                print(f"Disconnected with {addr}")
                print(f"[ACTIVE CONNECTIONS]: {len(clients)}")
                client_socket.close()
                break    
            elif message == b'VIDEO':
                global videos
                video_list=" ".join(videos)
                client_socket.send("#".encode())
                data = client_socket.recv(4096)
                if data == b'#':
                    send_video_frames(client_socket, video_list)
                
            elif message == b'SIG':
                message = client_socket.recv(4096)
                for client_sckt in client_sockets:
                    if client_socket != client_sckt:
                        client_sckt.send("*".encode())
                        client_sckt.send(message)
        except Exception as e:
            print(f"Error: {e}")
            exit(1)

# Create a server socket
server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.bind(('localhost', 12345))
server_socket.listen(10)
print(f"[Server] -> Listening for Connections on Port: {12345}...")

while True:
    client_socket, client_addr = server_socket.accept()
    print(f"Connection established with {client_addr}")
    # Create a new thread to handle the client
    client_thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
    client_thread.start()
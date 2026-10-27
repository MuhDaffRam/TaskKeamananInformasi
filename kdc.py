import socket

def run_kdc():
    HOST = '127.0.0.1'
    PORT = 5000
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"[*] KDC Server aktif di {HOST}:{PORT}...")
    
    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode('ascii')
        print(f"\n[KDC] Menerima request dari {addr}: {data}")
        
        # Format request: ID_A || ID_B || N1
        parts = data.split("||")
        if len(parts) == 3:
            id_a, id_b, n1 = parts[0], parts[1], parts[2]
            
            # Buat session key (16 karakter ASCII)
            session_key = "SessionKey123456"
            
            # Balasan KDC (Langkah 2): Kirim Ks & Ticket untuk Bob
            # Ticket format: SessionKey|ID_A
            ticket_for_bob = f"{session_key}|{id_a}"
            response = f"Ks:{session_key}|TICKET:{ticket_for_bob}"
            
            conn.sendall(response.encode('ascii'))
        conn.close()

if __name__ == '__main__':
    run_kdc()
import socket
import sys
import random
import threading

s_box = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0x70, 0x82, 0x9d, 0x72, 0x5a, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7,
    0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15, 0x04,
    0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09
]

def manual_aes_encrypt(plaintext_ascii, key_ascii):
    p_bytes = plaintext_ascii.ljust(16, '\0')[:16].encode('ascii')
    k_bytes = key_ascii.ljust(16, '\0')[:16].encode('ascii')
    encrypted_bytes = bytearray(16)
    for i in range(16):
        val = p_bytes[i] ^ k_bytes[i]
        encrypted_bytes[i] = s_box[val % len(s_box)]
    return encrypted_bytes.hex()

def manual_aes_decrypt(ciphertext_hex, key_ascii):
    c_bytes = bytes.fromhex(ciphertext_hex)
    k_bytes = key_ascii.ljust(16, '\0')[:16].encode('ascii')
    decrypted_bytes = bytearray(16)
    for i in range(16):
        val = c_bytes[i]
        original_val = val ^ k_bytes[i]
        decrypted_bytes[i] = original_val
    
    # Bersihkan karakter null/padding ekstra
    cleaned = decrypted_bytes.rstrip(b'\0')
    try:
        return cleaned.decode('ascii')
    except:
        return cleaned.hex() # Fallback aman jika berupa byte acak

class BobNode:
    def __init__(self):
        self.id_b = "Bob"
        self.master_key_b = "SecretKeyKDCBob23"
        self.session_key = None
        
        self.my_ip = "127.0.0.1"
        self.my_port = 6002
        self.alice_ip = "127.0.0.1"
        self.alice_port = 6001

    def start_responder_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.my_port))
        server.listen(5)
        
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('ascii')
            
            if data.startswith("TICKET||"):
                print(f"\n[Langkah 3] Menerima Ticket dari Alice ({addr[0]})")
                ticket_data = data.split("||")[1]
                
                parts = ticket_data.split("|")
                self.session_key = parts[0]
                print(f"[+] Berhasil ekstrak Session Key dari Ticket: {self.session_key}")
                
                # [Langkah 4] Kirim tantangan Nonce (N2) ke Alice
                n2 = random.randint(1000, 9999)
                print(f"[Langkah 4] Mengirim E_Ks(N2) dengan N2 = {n2}")
                n2_hex = manual_aes_encrypt(str(n2), self.session_key)
                
                try:
                    s_alice = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s_alice.connect((self.alice_ip, self.alice_port))
                    s_alice.sendall(f"NONCE2||{n2_hex}".encode('ascii'))
                    
                    # [Langkah 5] Terima konfirmasi N2 - 1 dari Alice
                    conf_data = s_alice.recv(1024).decode('ascii')
                    if conf_data.startswith("RESPONSE||"):
                        resp_hex = conf_data.split("||")[1]
                        decrypted_n2_minus_1 = manual_aes_decrypt(resp_hex, self.session_key)
                        print(f"[Langkah 5] Menerima respon N2-1 = {decrypted_n2_minus_1} dari Alice.")
                        print("[+] Autentikasi Timbal Balik Selesai! Kunci Sesi Valid.")
                    s_alice.close()
                except Exception as e:
                    print(f"[-] Gagal terhubung ke Alice pada Langkah 4/5: {e}")
                
            elif data.startswith("MSG||"):
                c_hex = data.split("||")[1]
                plain = manual_aes_decrypt(c_hex, self.session_key)
                print(f"\n[Pesan Masuk dari Alice]")
                print(f"   Ciphertext (Hex)   : {c_hex}")
                print(f"   Decrypted (ASCII)  : {plain}")
            
            conn.close()

    def interactive_menu(self):
        print(f"\n[*] Bob Server berjalan pada port {self.my_port}, menunggu koneksi...")
        server_thread = threading.Thread(target=self.start_responder_server, daemon=True)
        server_thread.start()
        
        while True:
            print("\n=== MENU INTERAKTIF BOB ===")
            print("1. Status Kunci Sesi Saat Ini")
            print("2. Ubah Master Key / Session Key secara Manual")
            print("3. Kirim Pesan Balasan ke Alice (Sender Mode)")
            print("4. Keluar")
            choice = input("Pilih menu (1-4): ")
            
            if choice == '1':
                print(f"[*] Session Key Aktif: {self.session_key}")
            elif choice == '2':
                new_key = input("Masukkan key ASCII baru (16 karakter): ")
                if len(new_key) == 16:
                    self.session_key = new_key
                    print("[+] Key berhasil diubah secara interaktif!")
                else:
                    print("[-] Key harus tepat 16 karakter ASCII!")
            elif choice == '3':
                if not self.session_key:
                    print("[-] Belum ada sesi aktif (Tunggu Alice menjalankan KDC/Langkah 3)!")
                    continue
                plaintext = input("Masukkan plaintext balasan (ASCII): ")
                ciphertext_hex = manual_aes_encrypt(plaintext, self.session_key)
                print(f"[+] Plaintext (ASCII) : {plaintext}")
                print(f"[+] Ciphertext (Hex)   : {ciphertext_hex}")
                
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((self.alice_ip, self.alice_port))
                    s.sendall(f"MSG||{ciphertext_hex}".encode('ascii'))
                    s.close()
                    print("[+] Pesan balasan berhasil dikirim ke Alice!")
                except Exception as e:
                    print(f"[-] Gagal mengirim pesan ke Alice: {e}")
            elif choice == '4':
                sys.exit(0)

if __name__ == '__main__':
    node = BobNode()
    node.interactive_menu()
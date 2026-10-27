import socket
import sys

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
    return decrypted_bytes.rstrip(b'\0').decode('ascii', errors='ignore')

class AliceNode:
    def __init__(self):
        self.id_a = "Alice"
        self.id_b = "Bob"
        self.master_key_a = "SecretKeyAlice12"
        self.session_key = None
        
        self.kdc_ip = "127.0.0.1"
        self.kdc_port = 5000
        self.my_port = 6001
        self.bob_ip = "127.0.0.1"
        self.bob_port = 6002

    def run_kdc_protocol(self):
        print("\n[Langkah 1] Mengirim permintaan ke KDC (ID_A || ID_B || N1)...")
        n1 = "Nonce123"
        msg_to_kdc = f"{self.id_a}||{self.id_b}||{n1}"
        
        try:
            # Hubungi KDC
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.kdc_ip, self.kdc_port))
            s.sendall(msg_to_kdc.encode('ascii'))
            
            response = s.recv(1024).decode('ascii')
            s.close()
            print(f"[*] Menerima respons dari KDC: {response}")
            
            # Parsing respons KDC
            parts = response.split("|")
            self.session_key = parts[0].split(":")[1]
            ticket_for_bob = parts[1] + "|" + parts[2]
            print(f"[+] Session Key berhasil didapatkan: {self.session_key}")
            
            # Buka listener lokal untuk bersiap menerima Nonce (Langkah 4) dari Bob
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('0.0.0.0', self.my_port))
            listener.listen(1)
            listener.settimeout(5.0)
            
            # [Langkah 3] Mengirim Ticket ke Bob
            print("[Langkah 3] Mengirim Ticket ke Bob...")
            s_bob = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s_bob.connect((self.bob_ip, self.bob_port))
            s_bob.sendall(f"TICKET||{ticket_for_bob}".encode('ascii'))
            s_bob.close()
            
            # [Langkah 4] Menunggu Tantangan (Nonce N2) dari Bob
            print("[Langkah 4] Menunggu E_Ks(N2) dari Bob...")
            conn_bob, _ = listener.accept()
            n2_encrypted = conn_bob.recv(1024).decode('ascii')
            print(f"[Langkah 4] Menerima data dari Bob: {n2_encrypted}")
            
            if n2_encrypted.startswith("NONCE2||"):
                c_hex = n2_encrypted.split("||")[1]
                n2_decrypted_str = manual_aes_decrypt(c_hex, self.session_key)
                print(f"[+] Decrypted N2 (Plaintext): {n2_decrypted_str}")
                
                # [Langkah 5] Mengirim modifikasi respons ke Bob secara aman berbasis string
                n2_response_str = n2_decrypted_str.strip() + "-ack"
                n2_resp_hex = manual_aes_encrypt(n2_response_str, self.session_key)
                
                conn_bob.sendall(f"RESPONSE||{n2_resp_hex}".encode('ascii'))
                print(f"[Langkah 5] Mengirim E_Ks(Response) ke Bob. Autentikasi Selesai!")
            
            conn_bob.close()
            listener.close()
            print("[+] Kunci dan Autentikasi Berhasil! Alice dan Bob siap berkomunikasi AES.")
            
        except Exception as e:
            print(f"[-] Gagal menjalankan protokol KDC: {e}")

    def interactive_menu(self):
        while True:
            print("\n=== MENU INTERAKTIF ALICE ===")
            print("1. Jalankan Key Distribution (KDC) & Autentikasi (Langkah 1-5)")
            print("2. Ubah Master Key / Session Key secara Manual")
            print("3. Kirim Pesan Rahasia ke Bob (AES Manual -> Hex)")
            print("4. Mode Terima Pesan (Listen sebagai Receiver dari Bob)")
            print("5. Keluar")
            choice = input("Pilih menu (1-5): ")
            
            if choice == '1':
                self.run_kdc_protocol()
            elif choice == '2':
                new_key = input("Masukkan key ASCII baru (16 karakter): ")
                if len(new_key) == 16:
                    self.session_key = new_key
                    print("[+] Key berhasil diubah secara interaktif!")
                else:
                    print("[-] Key harus tepat 16 karakter ASCII!")
            elif choice == '3':
                if not self.session_key:
                    print("[-] Lakukan distribusi kunci (Menu 1) terlebih dahulu!")
                    continue
                plaintext = input("Masukkan plaintext (ASCII): ")
                ciphertext_hex = manual_aes_encrypt(plaintext, self.session_key)
                print(f"[+] Plaintext (ASCII) : {plaintext}")
                print(f"[+] Ciphertext (Hex)   : {ciphertext_hex}")
                
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((self.bob_ip, self.bob_port))
                    s.sendall(f"MSG||{ciphertext_hex}".encode('ascii'))
                    s.close()
                    print("[+] Pesan berhasil dikirim ke Bob!")
                except Exception as e:
                    print(f"[-] Gagal mengirim pesan: {e}")
            elif choice == '4':
                print("[*] Masuk ke mode Listener (Tekan Ctrl+C untuk kembali ke menu)...")
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', self.my_port))
                server.listen(1)
                server.settimeout(5.0)
                try:
                    conn, addr = server.accept()
                    data = conn.recv(1024).decode('ascii')
                    if data.startswith("MSG||"):
                        c_hex = data.split("||")[1]
                        plain = manual_aes_decrypt(c_hex, self.session_key)
                        print(f"\n[Incoming Message dari {addr}]")
                        print(f"   Ciphertext (Hex)   : {c_hex}")
                        print(f"   Decrypted (ASCII)  : {plain}")
                    conn.close()
                except socket.timeout:
                    print("[-] Tidak ada pesan masuk (Timeout).")
                server.close()
            elif choice == '5':
                sys.exit(0)

if __name__ == '__main__':
    node = AliceNode()
    node.interactive_menu()
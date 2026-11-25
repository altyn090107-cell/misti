
from datetime import datetime
import os
import random
import threading
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

VISITED_FILE = "/tmp/visited_ips.txt"
TRAPPED_FILE = "/tmp/trapped_ips.txt"
ip_lock = threading.Lock()


def get_real_ip():
    """Возвращает IP клиента, переданный прокси, или адрес прямого подключения."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def load_ip_set(filename):
    """Безопасно загружает сохранённые IP из файла при старте сервера."""
    if not os.path.exists(filename):
        return set()
    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            ip_set = set()
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Поддерживаем оба формата: "timestamp | ip" и просто "ip"
                ip = line.split("|")[-1].strip()
                if ip:
                    ip_set.add(ip)
            return ip_set
    except Exception as e:
        print(f"[WARNING] Не удалось прочитать {filename}: {e}", flush=True)
        return set()


def register_ip(ip, ip_set, filename):
    """Добавляет новый IP в множество и дописывает его в файл."""
    if not ip or ip == "unknown":
        return False, len(ip_set)

    with ip_lock:
        is_new = ip not in ip_set
        if is_new:
            ip_set.add(ip)
            try:
                parent_dir = os.path.dirname(filename)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(filename, "a", encoding="utf-8") as f:
                    timestamp = datetime.utcnow().isoformat(timespec="seconds")
                    f.write(f"{timestamp} | {ip}\n")
            except Exception as e:
                print(f"[WARNING] Не удалось записать в {filename}: {e}", flush=True)
        return is_new, len(ip_set)


visited_ips = load_ip_set(VISITED_FILE)
trapped_ips = load_ip_set(TRAPPED_FILE)

ROOM_DATA = { #хранилище
    "room": {
        "description": "A dark, abandoned Theatre room, filled wuth dust and cobwests. "
        "It was once a very popular place but got abandoned a long time ago."
        "Now it's known as a niche place for those whp likes to examine abandoned places."
        " 'What might have happened here?' you think to yourself as you look around the room. ", 
        "items": {
            "stage": "You look around the stage and see a few old props, costumes, ballet shoes and a... newspaper? ",
            "ballet shoes": "You step closer to the pointe shoes. "
            "They look as though they have just been taken off. A chill radiates from them.",
            "newspaper": (
                "You pick up the newspaper that were lying around next to ballet shoes and see a headline that reads:"
                "'Brutal Murder of a popular male ballet dancer.'"
                "You read the article out of curiosity: 'A famous male ballerina-Xavier Hollowmoore, took the stage for the last time, "
                "before getting brutally assaulted, and getting choked to death while being violated."
                "He was found dead nearby his Ballet practice studio, in a quiet almost abandoned alleyway...'"
                "You read the rest of the article, and find out that he performed his last dance in this theatre. "
                "You feel a chill run down your spine."
            ),
        },"dialogue": "A room filled with the echoes of past performances",
        
    },
    "corridor": {
        "description": "You are in a corridor.",
        "items": {
            "door": "It's locked.",
            "lamp": "An old lamp that don't even work anymore.",
        },
        "dialogue": "The walls of the corridor emit a strange grinding sound.",
    },
    "dancer": {
        "description": (
            "You are at the... dancer? A male ballet dancer standing there in"
            " a chassé position, a ballet movement in which one foot slides or"
            " steps toward the other, appearing to chase it.He is wearing a"
            " pretty casual outfit, for a ballet dancer, and a pair of puants."
            "  You stand there, staring at his back, wondering what is he doing here,"
            " until..."
        ),
    
        "dialogue": "He slowly turns around and looks at you. He with a smile greets you by saying:"
        "? "
        "Didn't expect to see anyone here, did you? In my past life, what was it, number ninety-nine? No-no a hundred, I used to perform here,"
        "Back when these rotting walls were still bathed in golden light and applause. Back when people actually cared."
        "But now its just nothing but abandoned walls and dust. I mean, look at this place."
        "Its nothing now. People are so terribly messy, aren't they? They just can't help themselves; they ruin everything they touch, "
        "leaving ugly little stains all over the world."
        "Just like they left me in last past life. "
        "You probably alreadyknow what they did to me."
        "People just can't stop bothering and harassing everything i see."
        "You're like them, i know that. "
        "I've lived hundreds lives to see that exact same ugly little spark hiding behind your eyes. "
        "That is why I take such wonderful care of my little list."
        "I don't just punish bad behavior... I make sure you never existed in the first place."
        "Isn't that a mercy? Now... shall we take a bow?",
    }, # {}Хранит данные парами «ключ: значение»
    # []Упорядоченный изменяемый набор элементов
}

# ВОТ ЭТОТ МАРШРУТ ОТВЕЧАЕТ ЗА ГЛАВНУЮ СТРАНИЦУ (без него была ошибка 404)
@app.route('/')
def index():
    real_ip = get_real_ip()
    is_new, total_visitors = register_ip(real_ip, visited_ips, VISITED_FILE)

    fake_ip = f"192.0.2.{random.randint(1, 254)}"
    print("\n[+] Someone opened Theatre Corridor!", flush=True)
    print(f"[+] REAL IP: {real_ip} | DEMO IP: {fake_ip} | NEW: {is_new}", flush=True)
    print(f"[+] TOTAL UNIQUE VISITORS: {total_visitors}", flush=True)

    with ip_lock:
        ip_list = sorted(visited_ips)

    return render_template(
        "index.html",
        total_visitors=total_visitors,
        visited_ips=ip_list,
        current_ip=real_ip,
    )

@app.route('/api/action', methods=['POST'])
def room_action(): #2функ
    data = request.json
    room_name = data.get('room')
    action = data.get('action')
    
    if room_name not in ROOM_DATA:
        return jsonify({"text": "Unknown room."})
    
    current_room = ROOM_DATA[room_name]
    response_text = ""
    redirect_url = None # Флаг для перехода на скример/финал

    if action == 'talk':
        response_text = current_room.get('dialogue', '')
        # Если мы в комнате танцора и игрок поговорил с ним — отправляем в финал
        if room_name == 'dancer':
            redirect_url = '/finale' 
            
    elif action.startswith('inspect_'):
        item_name = action.split('_')[1]
        response_text = current_room["items"].get(item_name, "Here is nothing to inspect.")
    else:
        response_text = "Unknown action."

    return jsonify({
        "text": response_text,
        "redirect": redirect_url
    })
@app.route('/corridor')#функция сработает если пользователь перейдет туда
def corridor(): #3
    return render_template('corridor.html')

@app.route('/room')
def room():#4
    return render_template('room.html')

@app.route('/dancer')
def dancer():#5
    return render_template('dancer.html')

@app.route('/finale')
def finale():
    # Получаем реальный IP пользователя через прокси Render (или запасной локальный)
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        client_ip = request.remote_addr

    if client_ip not in trapped_ips:
        trapped_ips.append(client_ip)
        
    return render_template('finale.html', ip=client_ip, total=len(trapped_ips))

if __name__ == "__main__":
    print("=" * 35)
    print("THEATRE CORRIDOR")
    print("[SYSTEM] Game server starting...")
    print("[SYSTEM] Waiting for players...")
    print("=" * 35, flush=True)
    app.run(host="0.0.0.0", port=5000, debug=False) #проверяет ли запущен код и вывод приветствия в терминале

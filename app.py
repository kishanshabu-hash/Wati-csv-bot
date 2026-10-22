import telebot
import csv
import re
import os
from flask import Flask
import threading

# --- ENVIRONMENT VARIABLES ---
TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
# -----------------------------

bot = telebot.TeleBot(TOKEN)
allowed_users = {OWNER_ID}
user_data = {}

# Web Server (Railway / Render ko active rakhne ke liye)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is Running 24/7 on Railway!"

def is_auth(message):
    return message.from_user.id in allowed_users

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    text = (
        "Welcome To Text TO CSV & VCF BOT\n\n"
        "Commands:\n"
        "/start - Start The Bot\n"
        "/Txt_To_CSV - Convert TXT File to CSV & VCF\n"
        "/CSV_To_TXT - Convert CSV File To TXT\n"
        "/reset - Stop Current Process\n\n"
        "Created By @Flame9906"
    )
    bot.send_message(message.chat.id, text)

# --- RESET COMMAND ---
@bot.message_handler(commands=['reset'])
def reset_command(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.chat.id in user_data:
        del user_data[message.chat.id]
    bot.send_message(message.chat.id, "Process stopped immediately. Use commands to start again.")

# --- OWNER ACCESS SYSTEM ---
@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            new_user = int(message.text.split()[1])
            allowed_users.add(new_user)
            bot.reply_to(message, f"Access Granted to User ID: {new_user}")
        except:
            bot.reply_to(message, "Send command like this: /add_user 123456789")

# ==========================================
#             TXT TO CSV & VCF FLOW
# ==========================================
@bot.message_handler(commands=['Txt_To_CSV'])
def txt_to_csv_start(message):
    if not is_auth(message):
        bot.reply_to(message, "You do not have access to this bot.")
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "Send Your TXT Format File")
    bot.register_next_step_handler(msg, process_txt_file)

def process_txt_file(message):
    if message.text == '/reset': return reset_command(message)
    if not message.document:
        msg = bot.send_message(message.chat.id, "Please send a valid TXT file.")
        bot.register_next_step_handler(msg, process_txt_file)
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8', errors='ignore')
        
        # Numbers extract karna
        numbers = [re.sub(r'[^\d]', '', line.strip()) for line in content.split('\n') if re.sub(r'[^\d]', '', line.strip())]
        
        if not numbers:
            bot.send_message(message.chat.id, "No numbers found in the file.")
            return
            
        user_data[message.chat.id] = {'raw_numbers': numbers}
        msg = bot.send_message(message.chat.id, f"{len(numbers)} Contacts Found In Your File.\n\nSend Me Name For Your Contacts (Example: Koria 1)")
        bot.register_next_step_handler(msg, process_contact_name)
    except Exception as e:
        bot.send_message(message.chat.id, f"Error processing file: {e}")

def process_contact_name(message):
    if message.text == '/reset': return reset_command(message)
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Session expired. Please use /Txt_To_CSV again.")
        return

    raw_name = message.text.strip()
    match = re.match(r'^(.*?)(?:\s+(\d+))?$', raw_name)
    if match:
        prefix = match.group(1).strip()
        start_index = int(match.group(2)) if match.group(2) else 1
    else:
        prefix = raw_name
        start_index = 1
        
    user_data[message.chat.id].update({'prefix': prefix, 'index': start_index})
    
    # Ab Country Code puchenge
    msg = bot.send_message(message.chat.id, "Send Country Code (Example: 82 or 91):")
    bot.register_next_step_handler(msg, process_country_code)

def process_country_code(message):
    if message.text == '/reset': return reset_command(message)
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Session expired. Please use /Txt_To_CSV again.")
        return

    c_code = re.sub(r'[^\d]', '', message.text.strip())
    if not c_code:
        msg = bot.send_message(message.chat.id, "Invalid Country Code. Please send numbers only (e.g. 82 or 91):")
        bot.register_next_step_handler(msg, process_country_code)
        return

    user_data[message.chat.id]['country_code'] = c_code
    
    msg = bot.send_message(message.chat.id, "Send Name For Your CSV File (without .csv):")
    bot.register_next_step_handler(msg, ask_csv_filename)

def ask_csv_filename(message):
    if message.text == '/reset': return reset_command(message)
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Session expired. Please use /Txt_To_CSV again.")
        return

    file_name = message.text.strip()
    if file_name.lower().endswith('.csv'):
        file_name = file_name[:-4]
        
    user_data[message.chat.id]['csv_filename'] = file_name
    
    # Ab VCF file name puchenge
    msg = bot.send_message(message.chat.id, "Send Name For Your VCF File (without .vcf):")
    bot.register_next_step_handler(msg, ask_vcf_filename)

def ask_vcf_filename(message):
    if message.text == '/reset': return reset_command(message)
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Session expired. Please use /Txt_To_CSV again.")
        return

    vcf_name = message.text.strip()
    if vcf_name.lower().endswith('.vcf'):
        vcf_name = vcf_name[:-4]
        
    generate_csv_and_vcf(message.chat.id, vcf_name)

def generate_csv_and_vcf(chat_id, vcf_name):
    data = user_data.get(chat_id)
    if not data:
        bot.send_message(chat_id, "Process interrupted. Please start again with /Txt_To_CSV")
        return

    csv_file = f"{data['csv_filename']}.csv"
    vcf_file = f"{vcf_name}.vcf"

    try:
        raw_numbers = data['raw_numbers']
        prefix = data['prefix']
        start_idx = data['index']
        c_code = data['country_code']

        # Process numbers: strip country code from front if present
        processed_contacts = []
        for i, raw_num in enumerate(raw_numbers):
            num = raw_num
            if num.startswith(c_code):
                num = num[len(c_code):]
            
            contact_name = f"{prefix} {start_idx + i}"
            processed_contacts.append((contact_name, c_code, num))

        # 1. Generate CSV File
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'CountryCode', 'Phone'])
            for contact_name, code, num in processed_contacts:
                writer.writerow([contact_name, code, num])

        # 2. Generate VCF File
        with open(vcf_file, 'w', encoding='utf-8') as f:
            for contact_name, code, num in processed_contacts:
                full_num = f"+{code}{num}"
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{contact_name}\n")
                f.write(f"TEL;TYPE=CELL:{full_num}\n")
                f.write("END:VCARD\n")

        # Send CSV
        with open(csv_file, 'rb') as f:
            bot.send_document(chat_id, f, caption="Here is your CSV file.")

        # Send VCF
        with open(vcf_file, 'rb') as f:
            bot.send_document(chat_id, f, caption="Here is your VCF file.\n\nReady! Send /Txt_To_CSV for new file.")

    except Exception as e:
        bot.send_message(chat_id, f"Error generating files: {e}")
    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)
        if os.path.exists(vcf_file):
            os.remove(vcf_file)
        if chat_id in user_data:
            del user_data[chat_id]

# ==========================================
#             CSV TO TXT FLOW
# ==========================================
@bot.message_handler(commands=['CSV_To_TXT'])
def csv_to_txt_start(message):
    if not is_auth(message):
        bot.reply_to(message, "You do not have access to this bot.")
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "Send Me Your CSV File")
    bot.register_next_step_handler(msg, process_csv_file)

def process_csv_file(message):
    if message.text == '/reset': return reset_command(message)
    if not message.document:
        msg = bot.send_message(message.chat.id, "Please send a valid CSV file.")
        bot.register_next_step_handler(msg, process_csv_file)
        return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8', errors='ignore')
        
        reader = csv.reader(content.splitlines())
        header = next(reader, None)
        
        # Check column index for phone number
        phone_idx = 2 if header and len(header) > 2 else 1
        code_idx = 1 if header and len(header) > 2 else None

        numbers = []
        for row in reader:
            if len(row) > phone_idx:
                p_num = re.sub(r'[^\d]', '', row[phone_idx])
                if code_idx is not None and len(row) > code_idx:
                    c_code = re.sub(r'[^\d]', '', row[code_idx])
                    full = f"{c_code}{p_num}"
                else:
                    full = p_num
                if full:
                    numbers.append(full)
                    
        if not numbers:
            bot.send_message(message.chat.id, "No numbers found in the CSV.")
            return
            
        user_data[message.chat.id] = {'extracted_numbers': numbers}
        msg = bot.send_message(message.chat.id, "Send Name For Your Saved File (without .txt):")
        bot.register_next_step_handler(msg, ask_txt_filename)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Error processing CSV: {e}")

def ask_txt_filename(message):
    if message.text == '/reset': return reset_command(message)
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Session expired. Please use /CSV_To_TXT again.")
        return
    
    file_name = message.text.strip()
    if file_name.lower().endswith('.txt'):
        file_name = file_name[:-4]
        
    generate_txt(message.chat.id, file_name)

def generate_txt(chat_id, file_name):
    data = user_data.get(chat_id)
    if not data or 'extracted_numbers' not in data: 
        bot.send_message(chat_id, "Process interrupted. Please start again with /CSV_To_TXT")
        return
    
    filename = f"{file_name}.txt"
    try:
        numbers = data['extracted_numbers']
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(numbers))
            
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, caption="Your TXT File Is Ready")
            
        os.remove(filename)
    except Exception as e:
        bot.send_message(chat_id, f"Failed to generate file: {e}")
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

# ==========================================
#              GLOBAL HANDLERS
# ==========================================
@bot.message_handler(content_types=['document'])
def handle_unhandled_document(message):
    if is_auth(message):
        bot.send_message(message.chat.id, "Please select an option first:\n\n/Txt_To_CSV - Convert TXT to CSV & VCF\n/CSV_To_TXT - Convert CSV to TXT")

@bot.message_handler(func=lambda message: True)
def handle_unhandled_text(message):
    if is_auth(message):
        bot.send_message(message.chat.id, "Please choose a command:\n\n/Txt_To_CSV - TXT to CSV & VCF\n/CSV_To_TXT - CSV to TXT\n/reset - Reset Process")

def run_bot():
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook removal error: {e}")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

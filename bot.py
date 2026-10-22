# === SABSE PEHLE EVENT LOOP FIX (Ye ekdum upar hona zaroori hai) ===
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# ====================================================================

import os
import csv
import threading
from flask import Flask
from pyrogram import Client, filters

# --- DUMMY WEB SERVER (RENDER KI DEPLOYMENT PASS KARNE KE LIYE) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Live on Render!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_server, daemon=True).start()
# ------------------------------------------------------------------

# Environment Variables
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("csv_filter_bot", api_id=int(API_ID), api_hash=API_HASH, bot_token=BOT_TOKEN)

# User ki file aur state save karne ke liye
user_states = {}

@app.on_message(filters.document)
async def handle_csv(client, message):
    if message.document.file_name.endswith('.csv'):
        processing_msg = await message.reply("File check kar raha hu, thoda wait karo...")
        
        file_path = await message.download()
        failed_numbers = []
        
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('StatusDesc', '').strip().upper() == 'FAILED':
                        phone = row.get('Phone', '').strip()
                        if phone:
                            failed_numbers.append(phone)
            
            if failed_numbers:
                user_states[message.chat.id] = {
                    "status": "waiting_for_name",
                    "numbers": failed_numbers
                }
                await processing_msg.edit_text(
                    f"✅ CSV me total **{len(failed_numbers)}** FAILED numbers mile hain.\n\n"
                    "👉 **Ab tum batao is nayi TXT file ka naam kya rakhna hai?**\n"
                    "(Jaise: `campaign_data` ya `failed_list` - bas naam likh kar bhej do)"
                )
            else:
                await processing_msg.edit_text("Is CSV me koi 'FAILED' status wala number nahi mila.")
                
        except Exception as e:
            await processing_msg.edit_text(f"Error aaya: {str(e)}")
            
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        await message.reply("Bhai, sirf CSV format wali file bhejo.")

@app.on_message(filters.text & filters.private)
async def handle_filename(client, message):
    chat_id = message.chat.id
    
    if chat_id in user_states and user_states[chat_id]["status"] == "waiting_for_name":
        file_name_input = message.text.strip()
        
        if file_name_input.lower().endswith(".txt"):
            file_name_input = file_name_input[:-4]
            
        output_txt = f"{file_name_input}.txt"
        failed_numbers = user_states[chat_id]["numbers"]
        
        processing_msg = await message.reply("File bana raha hu...")
        
        try:
            with open(output_txt, 'w', encoding='utf-8') as out_f:
                for num in failed_numbers:
                    out_f.write(num + "\n")
            
            await processing_msg.delete()
            await message.reply_document(
                document=output_txt, 
                caption=f"Ye rahi tumhari file!\n📁 **Naam:** {output_txt}\n🔢 **Total Numbers:** {len(failed_numbers)}"
            )
        except Exception as e:
            await message.reply(f"File banane me error aaya: {str(e)}")
        finally:
            if os.path.exists(output_txt):
                os.remove(output_txt)
            del user_states[chat_id]
            
print("Bot chalu ho gaya hai...")
app.run()

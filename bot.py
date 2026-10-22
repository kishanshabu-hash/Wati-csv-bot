import os
import csv
from pyrogram import Client, filters

# Railway environment variables se credentials fetch karenge
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# API_ID integer format me hona chahiye
app = Client("csv_filter_bot", api_id=int(API_ID), api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.document)
async def handle_csv(client, message):
    if message.document.file_name.endswith('.csv'):
        processing_msg = await message.reply("File process kar raha hu, thoda wait karo...")
        
        file_path = await message.download()
        output_txt = f"failed_numbers_{message.chat.id}.txt"
        
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
                with open(output_txt, 'w', encoding='utf-8') as out_f:
                    for num in failed_numbers:
                        out_f.write(num + "\n")
                
                await processing_msg.delete()
                await message.reply_document(
                    document=output_txt, 
                    caption=f"Lo bhai! Total **{len(failed_numbers)}** FAILED numbers filter ho gaye hain."
                )
            else:
                await processing_msg.edit_text("Is CSV me koi 'FAILED' status wala number nahi mila.")
                
        except Exception as e:
            await processing_msg.edit_text(f"Error aaya: {str(e)}")
            
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(output_txt):
                os.remove(output_txt)
                
    else:
        await message.reply("Bhai, sirf CSV format wali file bhejo.")

print("Bot chalu ho gaya hai...")
app.run()

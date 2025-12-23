import os
import asyncio
import time
import shutil
import re
import html
from concurrent.futures import ThreadPoolExecutor

# Pyrogram & PDF Libs
from pyrogram import Client, filters, errors, enums
from pyrogram.types import Message, ForceReply, ReplyKeyboardRemove
from PyPDF2 import PdfMerger, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# Premium Logs (Rich)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN2", "YOUR_BOT_TOKEN")

# --- PATH CONFIGURATION (Termux Safe) ---
BASE_DIR = os.getcwd()
TEMP_DIR = os.path.join(BASE_DIR, "downloads_mt")

if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
os.makedirs(TEMP_DIR)

# --- BALANCED HIGH SPEED CONFIGURATION ---
app = Client(
    "devu_merger_pro",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8,                        # 8 is the Sweet Spot for Speed vs Stability
    max_concurrent_transmissions=3,   # 3 Chunks gives high speed without breaking connection
    ipv6=False                        # Keeps connection stable
)

# ================= PREMIUM LOGGER =================
console = Console()

class Logger:
    @staticmethod
    def banner():
        console.print(Panel("[bold cyan]🤖 DEVU MERGER BOT STARTED[/bold cyan]\n[dim]System is ready...[/dim]", title="[bold green]SYSTEM ACTIVE[/]", border_style="cyan", expand=False))

    @staticmethod
    def new_user(uid, name):
        console.print(f"[bold magenta] ➤ NEW USER:[/bold magenta] [yellow]{name}[/yellow] (ID: {uid})")

    @staticmethod
    def file_received(uid, filename, filesize):
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_row("User ID", str(uid))
        table.add_row("File", filename)
        table.add_row("Size", f"{filesize} MB")
        console.print(Panel(table, title="[bold blue]📥 FILE RECEIVED[/]", border_style="blue", expand=False))

    @staticmethod
    def merge_start(uid, filename, file_count):
        console.print(f"[bold yellow]⚡ MERGING STARTED[/bold yellow] | User: [cyan]{uid}[/cyan] | Files: [green]{file_count}[/green] | Output: [u]{filename}[/u]")

    @staticmethod
    def success(uid, filename):
        console.print(f"[bold green]✅ UPLOAD COMPLETE[/bold green] ➤ Sent {filename} to {uid}")

    @staticmethod
    def error(uid, error_msg):
        console.print(Panel(f"[bold red]{error_msg}[/]", title=f"❌ ERROR (User: {uid})", border_style="red"))

# ================= STATE MANAGEMENT =================
user_queue = {}
user_status = {}
last_update_time = {}

process_executor = ThreadPoolExecutor(max_workers=4)

# ================= HELPER FUNCTIONS =================

def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip() or "Merged_Document"

# --- PROFESSIONAL "CERTIFICATE STYLE" DESIGN ---
def create_promo_page_sync(path, p_width, p_height):
    try:
        c = canvas.Canvas(path, pagesize=(p_width, p_height))
        w, h = p_width, p_height

        # Dynamic Font Sizing
        big_font_size = min(w, h) * 0.22
        med_font_size = min(w, h) * 0.05
        small_font_size = min(w, h) * 0.03

        # 1. Background (Cream/Off-White)
        c.setFillColorRGB(0.99, 0.98, 0.95)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # 2. Borders
        pad = 20
        # Outer Border (Navy Blue)
        c.setStrokeColorRGB(0.1, 0.2, 0.4) 
        c.setLineWidth(10)
        c.rect(pad, pad, w - pad*2, h - pad*2)

        # Inner Border (Gold)
        pad2 = 35
        c.setStrokeColorRGB(0.7, 0.5, 0.2)
        c.setLineWidth(3)
        c.rect(pad2, pad2, w - pad2*2, h - pad2*2)

        # 3. Text Positioning
        y_top = h * 0.78
        y_mid = h * 0.5
        y_sub = h * 0.35
        y_foot = h * 0.1

        # TOP TEXT
        c.setFont("Helvetica", med_font_size)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawCentredString(w/2, y_top, "PROFESSIONALLY")
        c.drawCentredString(w/2, y_top - med_font_size*1.2, "MERGED DOCUMENT")

        # CENTER TEXT "DEVU"
        c.setFont("Helvetica-Bold", big_font_size)
        # Shadow Effect
        c.setFillColorRGB(0.1, 0.2, 0.4) 
        c.drawCentredString(w/2 + 4, y_mid - 4, "DEVU")
        # Main Color
        c.setFillColorRGB(0.1, 0.2, 0.4)
        c.drawCentredString(w/2, y_mid, "DEVU")

        # SUB TEXT
        c.setFont("Helvetica-Bold", med_font_size)
        c.setFillColorRGB(0.0, 0.4, 0.7) 
        c.drawCentredString(w/2, y_sub, "PRO MERGER SYSTEM")

        # FOOTER
        c.setFont("Helvetica", small_font_size)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(w/2, y_foot, "Generated by DevuBot | Secure & Verified")

        # Decorative Line
        c.setStrokeColorRGB(0.7, 0.5, 0.2)
        c.setLineWidth(2)
        c.line(w * 0.3, y_mid - big_font_size*0.2, w * 0.7, y_mid - big_font_size*0.2)

        c.save()
    except Exception as e:
        print(f"Promo Error: {e}")

def merge_pdfs_sync(file_list, output_path, promo_path):
    merger = PdfMerger()
    try:
        # Check files before merging
        valid_files = []
        for f in file_list:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                valid_files.append(f)
        
        if not valid_files:
            raise Exception("No valid PDF files found to merge.")

        first_pdf_reader = PdfReader(valid_files[0])
        first_page = first_pdf_reader.pages[0]
        w = float(first_page.mediabox.width)
        h = float(first_page.mediabox.height)

        for f in valid_files:
            merger.append(f)
        
        create_promo_page_sync(promo_path, w, h)
        
        if os.path.exists(promo_path): merger.append(promo_path)
        merger.write(output_path)
    finally: merger.close()

# ================= PROGRESS BAR =================
async def progress(current, total, message, action_type):
    uid = message.chat.id
    now = time.time()
    if uid in last_update_time and (now - last_update_time[uid]) < 3: return

    try:
        if total == 0: return
        percentage = (current * 100) / total
        completed = int(percentage / 10)
        bar = "▰" * completed + "▱" * (10 - completed)
        text = f"⚡ **{action_type}...**\n━━━━━━━━━━━━━━\n📊 `{bar}` **{percentage:.1f}%**\n💾 **Size:** `{current//1024//1024}MB / {total//1024//1024}MB`"
        if message.text != text:
            await message.edit(text)
            last_update_time[uid] = now
    except: pass

# ================= COMMANDS =================

@app.on_message(filters.command("cancel") & filters.private)
async def cancel(client, message):
    uid = message.from_user.id
    
    # Check if merging to lock cancel
    if user_status.get(uid) == "MERGING":
        await message.reply_text("⚠️ **Locked!** Cannot cancel during merging process.")
        return
    
    user_status[uid] = "IDLE"
    
    if uid in user_queue:
        for f in user_queue[uid]:
            if os.path.exists(f): os.remove(f)
        del user_queue[uid]
        # Force remove keyboard here too
        await message.reply_text("🗑 **Queue Cleared!** You can start fresh.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.reply_text("🤷‍♂️ **Nothing to cancel!** Your queue is empty.", reply_markup=ReplyKeyboardRemove())

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    try:
        uid = message.from_user.id
        
        user_status[uid] = "IDLE" 
        if uid in user_queue: del user_queue[uid]
        
        raw_name = message.from_user.first_name or "User"
        safe_name = re.sub(r"[\[\]*_`]", "", raw_name)
        
        try: Logger.new_user(uid, safe_name)
        except: pass

        text = (
            f"⚡ **DEVU MERGER PRO**\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 **Hello, {safe_name}!**\n\n"
            f"I am a Powerful PDF Merger Bot.\n\n"
            f"🛠 **HOW TO USE:**\n"
            f"1️⃣ Send PDF files one by one.\n"
            f"2️⃣ Type /merge when done.\n"
            f"3️⃣ Reply with a filename.\n\n"
            f"🚀 *Send a file to start!*"
        )
        
        # FIX: Ensure keyboard is removed on start
        await message.reply_text(text, quote=True, reply_markup=ReplyKeyboardRemove())
        
    except Exception as e:
        Logger.error(message.chat.id, f"Start Error: {e}")
        await message.reply_text("👋 **Hello!**\nBot is Ready. Send files to merge.", reply_markup=ReplyKeyboardRemove())

@app.on_message(filters.document & filters.private)
async def handle_pdfs(client, message: Message):
    uid = message.from_user.id
    if user_status.get(uid) in ["MERGING", "WAITING_NAME"]:
        await message.reply_text("⚠️ **Process Busy!** Please finish current task first or /cancel.")
        return

    if not message.document.file_name.lower().endswith(".pdf"):
        await message.reply_text("❌ **Invalid File!** Please send only PDF files.")
        return

    # FIX: Add ReplyKeyboardRemove here to clear any stuck 'Name File' input from previous runs
    status = await message.reply_text("📥 **Initializing Download...**", quote=True, reply_markup=ReplyKeyboardRemove())
    
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)

        # Unique path generation
        unique_name = f"{uid}_{message.id}_{int(time.time())}.pdf"
        final_path = os.path.join(TEMP_DIR, unique_name)
        
        # Download
        await message.download(
            file_name=final_path,
            progress=progress,
            progress_args=(status, "Downloading")
        )
        
        # --- SAFETY WAIT (Fixes Corrupt Error) ---
        await asyncio.sleep(1) 
        
        # --- EMPTY FILE CHECK ---
        if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
            if uid not in user_queue: user_queue[uid] = []
            user_queue[uid].append(final_path)
            
            size_mb = round(message.document.file_size / (1024 * 1024), 2)
            Logger.file_received(uid, message.document.file_name, size_mb)
            
            # --- CRASH FIX: SAFE EDIT ---
            msg_text = (
                f"📂 **FILE ADDED TO QUEUE**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📄 **Name:** `{message.document.file_name}`\n"
                f"💾 **Size:** `{size_mb} MB`\n"
                f"📚 **Total Files:** `{len(user_queue[uid])}`\n\n"
                f"🔵 *Send more files or type* /merge"
            )
            try:
                await status.edit(msg_text)
            except errors.MessageIdInvalid:
                await message.reply_text(msg_text)
            except Exception:
                pass

        else:
            if os.path.exists(final_path): os.remove(final_path)
            # --- CRASH FIX: SAFE EDIT ---
            err_text = "❌ **Download Failed!** File appears to be empty or corrupted (Network Issue). Please try again."
            try:
                await status.edit(err_text)
            except:
                await message.reply_text(err_text)

    except Exception as e:
        Logger.error(uid, str(e))
        # --- CRASH FIX: SAFE EDIT ---
        try:
            await status.edit(f"❌ **Error:** {e}")
        except:
            await message.reply_text(f"❌ **Error:** {e}")

@app.on_message(filters.command("merge") & filters.private)
async def ask_for_name(client, message):
    uid = message.from_user.id
    if uid not in user_queue or len(user_queue[uid]) < 2:
        await message.reply_text("⚠️ **Oops!** You need at least **2 PDF files** to merge.")
        return

    user_status[uid] = "WAITING_NAME"
    await message.reply_text(
        "📝 **NAME YOUR FILE**\n\n"
        "Please reply with the name you want for your merged PDF.\n"
        "*(Example: Physics Notes)* 👇",
        reply_markup=ForceReply(selective=True, placeholder="Name your file here...")
    )

@app.on_message(filters.text & filters.private)
async def perform_merge(client, message: Message):
    uid = message.from_user.id
    if user_status.get(uid) != "WAITING_NAME": return

    user_filename = clean_filename(message.text)
    if not user_filename.lower().endswith(".pdf"): user_filename += ".pdf"

    user_status[uid] = "MERGING"
    Logger.merge_start(uid, user_filename, len(user_queue[uid]))
    
    status_msg = await message.reply_text(f"⚙️ **Processing: {user_filename}**\n`Please wait...`")
    
    output_pdf = os.path.join(TEMP_DIR, f"OUT_{uid}_{int(time.time())}.pdf")
    promo_pdf = os.path.join(TEMP_DIR, f"PROMO_{uid}.pdf")

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(process_executor, merge_pdfs_sync, user_queue[uid], output_pdf, promo_pdf)

        await status_msg.edit("🚀 **Finalizing & Uploading...**")
        
        # --- FIXED CAPTION ---
        user_name = message.from_user.first_name # Plain text
        
        caption_text = (
            f"🔥 **𝐌𝐄𝐑𝐆𝐄 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃** 🔥\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f" 📂 **𝐅𝐢𝐥𝐞** : `{user_filename}`\n"
            f" 📚 **𝐐𝐭𝐲** : `{len(user_queue[uid])} Files`\n"
            f" 👤 **𝐁𝐲** : {user_name}\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"      ⚡ 𝗗𝗘𝗩𝗨 𝗠𝗘𝗥𝗚𝗘𝗥 𝗣𝗥𝗢" 
        )

        await message.reply_document(
            document=output_pdf,
            file_name=user_filename,
            caption=caption_text,
            progress=progress,
            progress_args=(status_msg, "Uploading")
        )
        
        Logger.success(uid, user_filename)

        if uid in user_queue:
            for f in user_queue[uid]:
                if os.path.exists(f): os.remove(f)
            del user_queue[uid]

    except Exception as e:
        Logger.error(uid, str(e))
        await status_msg.edit(f"❌ **Failed:** {e}")
    
    finally:
        user_status[uid] = "IDLE"
        try: await status_msg.delete()
        except: pass
        
        if os.path.exists(output_pdf): os.remove(output_pdf)
        if os.path.exists(promo_pdf): os.remove(promo_pdf)

if __name__ == "__main__":
    Logger.banner()
    app.run()

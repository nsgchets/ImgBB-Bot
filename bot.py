import os
import logging
import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("8738265724:AAFIK5hsqmTZg0uX8EG7oYbA4tBsPIOGT2g")
IMGBB_API_KEY = os.getenv("a33277f5aede646aedead635c26670c1")
IMGBB_API_URL = "https://api.imgbb.com/1/upload"

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when /start is issued."""
    welcome_text = (
        "🎉 Welcome to ImgBB Upload Bot!\n\n"
        "Send me any image, and I'll upload it to ImgBB and give you a direct link.\n\n"
        "Supported formats: JPEG, PNG, GIF, BMP, WEBP, etc."
    )
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when /help is issued."""
    help_text = (
        "📖 How to use this bot:\n\n"
        "1️⃣ Send any image (photo or document)\n"
        "2️⃣ Wait a moment while I upload it\n"
        "3️⃣ Get a direct sharing link!\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)


async def upload_to_imgbb(image_data: bytes, filename: str = "image") -> dict | None:
    """
    Upload image to ImgBB and return the response.
    
    Args:
        image_data: Raw image bytes
        filename: Name of the image file
    
    Returns:
        JSON response from ImgBB or None if failed
    """
    async with aiohttp.ClientSession() as session:
        # Prepare form data for ImgBB API
        form_data = aiohttp.FormData()
        form_data.add_field(
            "key", 
            IMGBB_API_KEY,
        )
        form_data.add_field(
            "image", 
            image_data,
            filename=filename,
            content_type="application/octet-stream"
        )
        
        try:
            async with session.post(IMGBB_API_URL, data=form_data) as response:
                result = await response.json()
                
                if result.get("success"):
                    return result
                else:
                    logger.error(f"ImgBB upload failed: {result}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error while uploading to ImgBB: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages from users."""
    if not IMGBB_API_KEY:
        await update.message.reply_text(
            "❌ Bot not configured properly. Please set IMGBB_API_KEY in .env file."
        )
        return
    
    # Send initial processing message
    processing_msg = await update.message.reply_text("⏳ Uploading your image to ImgBB...")
    
    try:
        # Get the largest photo available
        photo = update.message.photo[-1]
        
        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
        
        # Upload to ImgBB
        result = await upload_to_imgbb(bytes(image_data), f"telegram_photo_{photo.file_unique_id}.jpg")
        
        if result and result.get("data"):
            image_url = result["data"]["url"]
            delete_url = result["data"].get("delete_url", "Not available")
            size = result["data"].get("size", "Unknown")
            
            response_text = (
                f"✅ **Upload Successful!**\n\n"
                f"🔗 **Direct Link:** {image_url}\n"
                f"🗑 **Delete URL:** {delete_url}\n"
                f"📦 **Size:** {size} bytes\n\n"
                f"⚠️ The image will be stored permanently on ImgBB."
            )
            
            await processing_msg.edit_text(response_text, parse_mode="Markdown")
        else:
            await processing_msg.edit_text(
                "❌ Failed to upload image to ImgBB. Please try again later."
            )
            
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred while processing your image. Please try again."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document messages that contain images."""
    if not IMGBB_API_KEY:
        await update.message.reply_text(
            "❌ Bot not configured properly. Please set IMGBB_API_KEY in .env file."
        )
        return
    
    document = update.message.document
    
    # Check if the document is an image
    mime_type = document.mime_type or ""
    if not mime_type.startswith("image/"):
        await update.message.reply_text(
            "ℹ️ Please send an image file (JPEG, PNG, GIF, etc.)"
        )
        return
    
    # Send initial processing message
    processing_msg = await update.message.reply_text("⏳ Uploading your image to ImgBB...")
    
    try:
        # Download the document
        file = await context.bot.get_file(document.file_id)
        image_data = await file.download_as_bytearray()
        
        # Upload to ImgBB
        result = await upload_to_imgbb(bytes(image_data), document.file_name or "image")
        
        if result and result.get("data"):
            image_url = result["data"]["url"]
            delete_url = result["data"].get("delete_url", "Not available")
            size = result["data"].get("size", document.file_size)
            
            response_text = (
                f"✅ **Upload Successful!**\n\n"
                f"🔗 **Direct Link:** {image_url}\n"
                f"🗑 **Delete URL:** {delete_url}\n"
                f"📦 **Size:** {size} bytes\n"
                f"📄 **File Name:** {document.file_name}\n\n"
                f"⚠️ The image will be stored permanently on ImgBB."
            )
            
            await processing_msg.edit_text(response_text, parse_mode="Markdown")
        else:
            await processing_msg.edit_text(
                "❌ Failed to upload image to ImgBB. Please try again later."
            )
            
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred while processing your document. Please try again."
        )


def main() -> None:
    """Start the bot."""
    # Validate configuration
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables!")
        return
    
    if not IMGBB_API_KEY:
        logger.warning("IMGBB_API_KEY not set! The bot will not be able to upload images.")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handlers for photos and documents
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()